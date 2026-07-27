"""
Holt Dateien von Proton Drive: die Stammdaten-Datei (wegpiraten_datenbank.xlsx)
und ausgefüllte Zeiterfassungsbögen (Timesheets) eines Monatsverzeichnisses.

Proton Drive ist Ende-zu-Ende-verschlüsselt und nur über die proton-drive CLI
erreichbar (kein Mount). Alle CLI-Aufrufe laufen unter dem zentralen flock
(``masterdata_source.lockfile``), damit sie sich nicht mit den Sync-Timern um
den lokalen CLI-Cache streiten (SQLITE_BUSY) -- vgl. ~/proton-drive/Makefile
und ~/proton-drive/bin/download.sh.

Ablauf Stammdaten: Remote-Verzeichnis per ``filesystem list -j`` nach
Kandidaten durchsuchen (exakter Dateiname hat Vorrang, sonst neueste Datei),
gegen die lokale Kopie im Import-Verzeichnis vergleichen (SHA1, sonst
Grösse+mtime) und nur bei Bedarf herunterladen.

Ablauf Timesheets: alle zum Muster passenden Dateien eines relativen
Remote-Unterverzeichnisses (unterhalb von ``masterdata_source.remote_dir``)
nach derselben Vergleichslogik holen. Remote-Dateien werden nie verändert.
"""

import fnmatch
import hashlib
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, Sequence

from loguru import logger

from shared_modules.config import Config


class FetchError(RuntimeError):
    """Fehler beim Holen der Stammdaten von Proton Drive."""


@dataclass
class RemoteFile:
    """Metadaten einer Datei auf Proton Drive (aus ``filesystem list -j``)."""

    name: str
    modified: datetime
    size: Optional[int]
    sha1: Optional[str]


# Runner kapselt den CLI-Aufruf (injizierbar für Tests).
Runner = Callable[..., str]


def _locked_runner(proton_cli: Path, lockfile: Path, lock_timeout: int) -> Runner:
    """
    Baut einen Runner, der die proton-drive CLI unter dem zentralen flock
    aufruft (wie die Targets in ~/proton-drive/Makefile).
    """

    def run(args: Sequence[str], timeout: int = 120) -> str:
        cmd = ["flock", "-w", str(lock_timeout), str(lockfile), str(proton_cli), *args]
        logger.debug(f"CLI-Aufruf: {' '.join(cmd)}")
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except FileNotFoundError as exc:
            raise FetchError(f"proton-drive CLI oder flock nicht gefunden: {exc}") from exc
        except subprocess.TimeoutExpired as exc:
            raise FetchError(f"CLI-Aufruf nach {timeout}s abgebrochen: {' '.join(cmd)}") from exc
        if proc.returncode != 0:
            raise FetchError(
                f"proton-drive fehlgeschlagen (Exit {proc.returncode}): {proc.stderr.strip() or proc.stdout.strip()}"
            )
        return proc.stdout

    return run


def parse_listing(payload: str) -> list[RemoteFile]:
    """
    Parst die Ausgabe von ``filesystem list -j`` (JSON-Array, je nach
    CLI-Version auch NDJSON) und liefert die enthaltenen Dateien.
    """
    try:
        entries = json.loads(payload)
    except json.JSONDecodeError:
        entries = []
        for line in payload.splitlines():
            line = line.strip().rstrip(",")
            if not line or line in ("[", "]"):
                continue
            entries.append(json.loads(line))

    files: list[RemoteFile] = []
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("type") != "file":
            continue
        name_info = entry.get("name") or {}
        if not name_info.get("ok"):
            logger.warning("Dateiname remote nicht entschlüsselbar -- Eintrag übersprungen.")
            continue
        modified_raw = entry.get("modificationTime")
        if not modified_raw:
            logger.warning(f"Keine modificationTime für '{name_info.get('value')}' -- Eintrag übersprungen.")
            continue
        revision = (entry.get("activeRevision") or {}).get("value") or {}
        digests = revision.get("claimedDigests") or {}
        files.append(
            RemoteFile(
                name=name_info["value"],
                modified=datetime.fromisoformat(modified_raw),
                size=entry.get("totalStorageSize"),
                sha1=digests.get("sha1"),
            )
        )
    return files


def select_candidate(files: list[RemoteFile], pattern: str, preferred: str) -> RemoteFile:
    """
    Wählt die Stammdaten-Datei aus den Remote-Dateien: der exakte bevorzugte
    Dateiname hat Vorrang, sonst gewinnt die neueste Datei passend zum Muster.
    """
    matches = [f for f in files if fnmatch.fnmatch(f.name, pattern)]
    if not matches:
        raise FetchError(f"Keine Datei passend zu '{pattern}' im Remote-Verzeichnis gefunden.")
    for candidate in matches:
        logger.debug(f"Kandidat: {candidate.name} (remote geändert: {candidate.modified.isoformat()})")
    exact = [f for f in matches if f.name == preferred]
    chosen = exact[0] if exact else max(matches, key=lambda f: f.modified)
    logger.info(f"Gewählte Remote-Datei: {chosen.name} (remote geändert: {chosen.modified.isoformat()})")
    return chosen


def is_up_to_date(local: Path, remote: RemoteFile) -> bool:
    """
    Prüft, ob die lokale Kopie der Remote-Datei entspricht: bevorzugt per
    SHA1 (vom Remote-Digest), sonst per Grösse und Änderungszeitpunkt.
    """
    if not local.exists():
        return False
    if remote.sha1:
        local_sha1 = hashlib.sha1(local.read_bytes()).hexdigest()
        if local_sha1 == remote.sha1:
            return True
        logger.debug(f"SHA1 weicht ab (lokal {local_sha1}, remote {remote.sha1}).")
        return False
    if remote.size is not None and local.stat().st_size != remote.size:
        return False
    return local.stat().st_mtime >= remote.modified.timestamp()


def _download_one(*, remote_dir: str, remote_file: RemoteFile, target_dir: Path, runner: Runner, target_name: str) -> Path:
    """
    Lädt eine Remote-Datei in das Zielverzeichnis und setzt die mtime auf den
    Remote-Zeitpunkt, damit der Aktualitätsvergleich beim nächsten Lauf
    zuverlässig greift.
    """
    target = target_dir / target_name
    # Hinweis: Dateinamen mit "/" oder "\" müssten für die CLI escaped werden
    # (vgl. ~/proton-drive/bin/download.sh) -- hier per Muster ausgeschlossen.
    remote_path = f"{remote_dir.rstrip('/')}/{remote_file.name}"
    logger.info(f"Lade '{remote_path}' herunter...")
    with tempfile.TemporaryDirectory(dir=target_dir) as tmp:
        runner(["filesystem", "download", "-c", "replace", "--", remote_path, tmp], timeout=600)
        downloaded = Path(tmp) / remote_file.name
        if not downloaded.exists():
            raise FetchError(f"Download ohne Ergebnisdatei: {downloaded}")
        os.replace(downloaded, target)
    ts = remote_file.modified.timestamp()
    os.utime(target, (ts, ts))
    logger.info(f"Datei aktualisiert: {target} (remote geändert: {remote_file.modified.isoformat()})")
    return target


def fetch_masterdata_core(
    *,
    remote_dir: str,
    pattern: str,
    preferred: str,
    target_dir: Path,
    runner: Runner,
    target_name: Optional[str] = None,
) -> Path:
    """
    Holt die Stammdaten-Datei von Proton Drive in das Zielverzeichnis.

    Args:
        remote_dir: Remote-Verzeichnis auf Proton Drive.
        pattern: Glob-Muster für Kandidaten-Dateien.
        preferred: Bevorzugter (exakter) Dateiname.
        target_dir: Lokales Zielverzeichnis (Import-Ordner).
        runner: Funktion für CLI-Aufrufe (injizierbar für Tests).
        target_name: Lokaler Zieldateiname (Standard: preferred).

    Returns:
        Pfad zur lokalen Datei im Zielverzeichnis.
    """
    target_name = target_name or preferred
    logger.info(f"Suche Stammdaten remote in '{remote_dir}' (Muster '{pattern}')...")

    payload = runner(["filesystem", "list", "-j", "--", remote_dir])
    files = parse_listing(payload)
    logger.info(f"{len(files)} Datei(en) remote gefunden.")
    chosen = select_candidate(files, pattern, preferred)

    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / target_name
    if is_up_to_date(target, chosen):
        logger.info(f"Lokale Datei ist bereits aktuell: {target}")
        return target

    return _download_one(remote_dir=remote_dir, remote_file=chosen, target_dir=target_dir, runner=runner, target_name=target_name)


def fetch_masterdata(config: Config) -> Path:
    """
    Holt die Stammdaten-Datei gemäss Konfiguration von Proton Drive in den
    Import-Ordner (structure.imports_path).
    """
    source = config.masterdata_source
    prj_root = Path(config.structure.prj_root)
    imports_rel = Path(config.structure.imports_path or "import")
    target_dir = imports_rel if imports_rel.is_absolute() else prj_root / imports_rel

    runner = _locked_runner(
        proton_cli=Path(source.proton_cli).expanduser(),
        lockfile=Path(source.lockfile).expanduser(),
        lock_timeout=source.lock_timeout_seconds,
    )
    return fetch_masterdata_core(
        remote_dir=source.remote_dir,
        pattern=source.file_pattern,
        preferred=source.preferred_filename,
        target_dir=target_dir,
        runner=runner,
        target_name=config.database.db_name or source.preferred_filename,
    )


def fetch_timesheets_core(
    *,
    remote_dir: str,
    target_dir: Path,
    runner: Runner,
    pattern: str = "*.xlsx",
) -> list[Path]:
    """
    Holt alle zum Muster passenden Dateien eines Remote-Verzeichnisses in das
    Zielverzeichnis (z.B. ausgefüllte Zeiterfassungsbögen eines Monats).
    Temporäre Excel-Sperrdateien (``~$*``) werden übersprungen, bereits
    aktuelle lokale Kopien nicht erneut geladen.

    Args:
        remote_dir: Remote-Verzeichnis auf Proton Drive.
        target_dir: Lokales Zielverzeichnis (Import-Ordner).
        runner: Funktion für CLI-Aufrufe (injizierbar für Tests).
        pattern: Glob-Muster für die zu holenden Dateien.

    Returns:
        Liste der lokalen Dateipfade (geholt oder bereits aktuell).
    """
    logger.info(f"Suche Dateien remote in '{remote_dir}' (Muster '{pattern}')...")

    payload = runner(["filesystem", "list", "-j", "--", remote_dir])
    files = parse_listing(payload)
    candidates = [f for f in files if fnmatch.fnmatch(f.name, pattern) and not f.name.startswith("~$")]
    if not candidates:
        raise FetchError(f"Keine Dateien passend zu '{pattern}' im Remote-Verzeichnis '{remote_dir}' gefunden.")
    logger.info(f"{len(candidates)} Datei(en) remote gefunden.")

    target_dir.mkdir(parents=True, exist_ok=True)
    results: list[Path] = []
    downloaded = 0
    for remote_file in sorted(candidates, key=lambda f: f.name):
        target = target_dir / remote_file.name
        if is_up_to_date(target, remote_file):
            logger.info(f"Bereits aktuell: {target.name}")
        else:
            _download_one(
                remote_dir=remote_dir, remote_file=remote_file, target_dir=target_dir, runner=runner, target_name=remote_file.name
            )
            downloaded += 1
        results.append(target)
    logger.info(f"{downloaded} Datei(en) geholt, {len(results) - downloaded} bereits aktuell.")
    return results


def fetch_timesheets(config: Config, remote_subdir: str) -> list[Path]:
    """
    Holt die ausgefüllten Zeiterfassungsbögen aus einem Unterverzeichnis von
    ``masterdata_source.remote_dir`` (z.B. "Timesheets - .../2026-06 Juni/...")
    in den Import-Ordner (structure.imports_path).
    """
    source = config.masterdata_source
    prj_root = Path(config.structure.prj_root)
    imports_rel = Path(config.structure.imports_path or "import")
    target_dir = imports_rel if imports_rel.is_absolute() else prj_root / imports_rel

    remote_dir = f"{source.remote_dir.rstrip('/')}/{remote_subdir.strip('/')}"
    runner = _locked_runner(
        proton_cli=Path(source.proton_cli).expanduser(),
        lockfile=Path(source.lockfile).expanduser(),
        lock_timeout=source.lock_timeout_seconds,
    )
    return fetch_timesheets_core(remote_dir=remote_dir, target_dir=target_dir, runner=runner)
