"""
Tests für den Stammdaten-Fetch von Proton Drive (data_imports.fetch_masterdata).

Die proton-drive CLI wird nicht wirklich aufgerufen -- der Runner ist
injizierbar und wird hier durch Fakes ersetzt.
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from data_imports.fetch_masterdata import (
    FetchError,
    RemoteFile,
    fetch_masterdata_core,
    fetch_timesheets_core,
    is_up_to_date,
    parse_listing,
    select_candidate,
)

REMOTE_DIR = "/my-files/Shared/Beatus/Wegpiraten Unterlagen"
PATTERN = "wegpiraten_datenbank*.xlsx"
PREFERRED = "wegpiraten_datenbank.xlsx"

CONTENT = b"fake excel content"
CONTENT_SHA1 = hashlib.sha1(CONTENT).hexdigest()


def _entry(name: str, modified: str, sha1: str | None = None) -> dict:
    """Baut einen List-Eintrag im Format der proton-drive CLI."""
    entry = {
        "name": {"ok": True, "value": name},
        "type": "file",
        "modificationTime": modified,
        "totalStorageSize": len(CONTENT),
    }
    if sha1:
        entry["activeRevision"] = {"ok": True, "value": {"claimedDigests": {"sha1": sha1}}}
    return entry


def _listing(*entries: dict) -> str:
    return json.dumps(list(entries))


# --- parse_listing ---


def test_parse_listing_array():
    """JSON-Array wird geparst, Ordner und unlesbare Namen werden übersprungen."""
    payload = _listing(
        _entry("a.xlsx", "2026-07-22T11:11:35.000Z", CONTENT_SHA1),
        {"name": {"ok": True, "value": "Ordner"}, "type": "folder", "modificationTime": "2026-01-01T00:00:00Z"},
        {"name": {"ok": False}, "type": "file", "modificationTime": "2026-01-01T00:00:00Z"},
    )
    files = parse_listing(payload)
    assert len(files) == 1
    assert files[0].name == "a.xlsx"
    assert files[0].sha1 == CONTENT_SHA1
    assert files[0].modified == datetime(2026, 7, 22, 11, 11, 35, tzinfo=timezone.utc)


def test_parse_listing_ndjson():
    """NDJSON (ein Objekt pro Zeile) wird als Fallback akzeptiert."""
    payload = "\n".join(
        [
            json.dumps(_entry("a.xlsx", "2026-07-01T00:00:00.000Z")),
            json.dumps(_entry("b.xlsx", "2026-07-02T00:00:00.000Z")),
        ]
    )
    assert [f.name for f in parse_listing(payload)] == ["a.xlsx", "b.xlsx"]


# --- select_candidate ---


def test_select_exact_preferred_wins_over_newer_variant():
    """Der exakte Dateiname hat Vorrang, auch wenn eine Variante neuer ist."""
    files = [
        RemoteFile("wegpiraten_datenbank_orig.xlsx", datetime(2026, 7, 25, tzinfo=timezone.utc), None, None),
        RemoteFile(PREFERRED, datetime(2026, 7, 22, tzinfo=timezone.utc), None, None),
    ]
    assert select_candidate(files, PATTERN, PREFERRED).name == PREFERRED


def test_select_newest_when_no_exact_match():
    """Ohne exakte Datei gewinnt die neueste passende Datei."""
    files = [
        RemoteFile("wegpiraten_datenbank_orig.xlsx", datetime(2026, 7, 20, tzinfo=timezone.utc), None, None),
        RemoteFile("wegpiraten_datenbank-dali.xlsx", datetime(2026, 7, 25, tzinfo=timezone.utc), None, None),
    ]
    assert select_candidate(files, PATTERN, PREFERRED).name == "wegpiraten_datenbank-dali.xlsx"


def test_select_raises_without_candidates():
    """Keine passende Datei -> klarer Fehler."""
    files = [RemoteFile("sonstwas.xlsx", datetime(2026, 7, 25, tzinfo=timezone.utc), None, None)]
    with pytest.raises(FetchError):
        select_candidate(files, PATTERN, PREFERRED)


# --- is_up_to_date ---


def test_up_to_date_via_sha1(tmp_path: Path):
    """Gleicher SHA1 -> aktuell, abweichender Inhalt -> veraltet."""
    local = tmp_path / PREFERRED
    local.write_bytes(CONTENT)
    remote = RemoteFile(PREFERRED, datetime(2026, 7, 22, tzinfo=timezone.utc), len(CONTENT), CONTENT_SHA1)
    assert is_up_to_date(local, remote)
    local.write_bytes(b"anderer inhalt")
    assert not is_up_to_date(local, remote)


def test_up_to_date_fallback_size_and_mtime(tmp_path: Path):
    """Ohne Remote-SHA1: Grösse und mtime (>= remote) entscheiden."""
    local = tmp_path / PREFERRED
    local.write_bytes(CONTENT)
    remote = RemoteFile(PREFERRED, datetime(2026, 7, 22, tzinfo=timezone.utc), len(CONTENT), None)
    # Frisch geschriebene Datei: mtime liegt nach dem Remote-Zeitpunkt -> aktuell.
    assert is_up_to_date(local, remote)
    # mtime vor den Remote-Zeitpunkt gesetzt -> veraltet.
    old = datetime(2026, 7, 1, tzinfo=timezone.utc).timestamp()
    os.utime(local, (old, old))
    assert not is_up_to_date(local, remote)


def test_up_to_date_missing_local(tmp_path: Path):
    """Fehlende lokale Datei ist nie aktuell."""
    remote = RemoteFile(PREFERRED, datetime(2026, 7, 22, tzinfo=timezone.utc), len(CONTENT), CONTENT_SHA1)
    assert not is_up_to_date(tmp_path / PREFERRED, remote)


# --- fetch_masterdata_core (Ende-zu-Ende mit Fake-Runner) ---


def _fake_runner(payload: str, calls: list) -> object:
    """Simuliert die CLI: list liefert payload, download legt die Datei an."""

    def run(args, timeout: int = 120) -> str:
        calls.append(list(args))
        if args[:2] == ["filesystem", "list"]:
            return payload
        if args[:2] == ["filesystem", "download"]:
            target_dir = Path(args[-1])
            name = args[-2].rsplit("/", 1)[-1]
            (target_dir / name).write_bytes(CONTENT)
            return ""
        raise AssertionError(f"Unerwarteter Aufruf: {args}")

    return run


def test_fetch_downloads_and_skips_when_current(tmp_path: Path):
    """Erster Lauf lädt herunter (mtime = Remote-Zeitpunkt), zweiter Lauf lädt nicht erneut."""
    payload = _listing(_entry(PREFERRED, "2026-07-22T11:11:35.000Z", CONTENT_SHA1))
    calls: list = []

    target = fetch_masterdata_core(
        remote_dir=REMOTE_DIR, pattern=PATTERN, preferred=PREFERRED, target_dir=tmp_path, runner=_fake_runner(payload, calls)
    )
    assert target == tmp_path / PREFERRED
    assert target.read_bytes() == CONTENT
    assert target.stat().st_mtime == datetime(2026, 7, 22, 11, 11, 35, tzinfo=timezone.utc).timestamp()

    calls.clear()
    again = fetch_masterdata_core(
        remote_dir=REMOTE_DIR, pattern=PATTERN, preferred=PREFERRED, target_dir=tmp_path, runner=_fake_runner(payload, calls)
    )
    assert again == target
    assert not any(c[:2] == ["filesystem", "download"] for c in calls)


def test_fetch_downloads_newer_remote(tmp_path: Path):
    """Abweichende Remote-Version (anderer SHA1) wird erneut geholt."""
    (tmp_path / PREFERRED).write_bytes(b"alte version")
    payload = _listing(_entry(PREFERRED, "2026-07-22T11:11:35.000Z", CONTENT_SHA1))
    calls: list = []

    fetch_masterdata_core(
        remote_dir=REMOTE_DIR, pattern=PATTERN, preferred=PREFERRED, target_dir=tmp_path, runner=_fake_runner(payload, calls)
    )
    assert (tmp_path / PREFERRED).read_bytes() == CONTENT
    assert any(c[:2] == ["filesystem", "download"] for c in calls)


# --- fetch_timesheets_core ---


def test_fetch_timesheets_downloads_all_matching(tmp_path: Path):
    """Alle passenden xlsx-Dateien werden geholt; ~$-Sperrdateien, andere
    Endungen und Ordner werden übersprungen."""
    payload = _listing(
        _entry("E1_C1017 (X)_2026-06.xlsx", "2026-07-10T08:00:00.000Z", CONTENT_SHA1),
        _entry("E2_C1038 (Y)_2026-06.xlsx", "2026-07-11T08:00:00.000Z", CONTENT_SHA1),
        _entry("~$E1_C1017 (X)_2026-06.xlsx", "2026-07-12T08:00:00.000Z", CONTENT_SHA1),
        _entry("notizen.pdf", "2026-07-12T08:00:00.000Z"),
        {"name": {"ok": True, "value": "Unterordner"}, "type": "folder", "modificationTime": "2026-07-01T00:00:00Z"},
    )
    calls: list = []

    paths = fetch_timesheets_core(remote_dir=REMOTE_DIR, target_dir=tmp_path, runner=_fake_runner(payload, calls))

    assert [p.name for p in paths] == ["E1_C1017 (X)_2026-06.xlsx", "E2_C1038 (Y)_2026-06.xlsx"]
    downloads = [c for c in calls if c[:2] == ["filesystem", "download"]]
    assert len(downloads) == 2
    for p in paths:
        assert p.read_bytes() == CONTENT


def test_fetch_timesheets_skips_up_to_date(tmp_path: Path):
    """Bereits aktuelle lokale Kopien werden nicht erneut geladen."""
    payload = _listing(_entry("sheet.xlsx", "2026-07-10T08:00:00.000Z", CONTENT_SHA1))
    calls: list = []
    runner = _fake_runner(payload, calls)

    first = fetch_timesheets_core(remote_dir=REMOTE_DIR, target_dir=tmp_path, runner=runner)
    assert len([c for c in calls if c[:2] == ["filesystem", "download"]]) == 1

    calls.clear()
    second = fetch_timesheets_core(remote_dir=REMOTE_DIR, target_dir=tmp_path, runner=runner)
    assert second == first
    assert not [c for c in calls if c[:2] == ["filesystem", "download"]]


def test_fetch_timesheets_raises_without_candidates(tmp_path: Path):
    """Leeres Remote-Verzeichnis -> klarer Fehler."""
    payload = _listing(_entry("notizen.pdf", "2026-07-12T08:00:00.000Z"))
    with pytest.raises(FetchError):
        fetch_timesheets_core(remote_dir=REMOTE_DIR, target_dir=tmp_path, runner=_fake_runner(payload, []))
