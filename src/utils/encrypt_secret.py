"""
Hilfsskript zum Verschlüsseln von Passwörtern für .env.
"""

from __future__ import annotations

import getpass
import os
from pathlib import Path
from typing import Optional

import typer
from cryptography.fernet import Fernet  # type: ignore[import]
from rich.console import Console

app = typer.Typer(add_completion=False)
console = Console()


def _prompt_secret() -> str:
    """
    Fragt ein Secret interaktiv ab.
    """
    console.print("Kein Passwort als Argument übergeben.")
    secret = getpass.getpass("Bitte Passwort eingeben (wird nicht angezeigt): ")
    if not secret:
        raise ValueError("Kein Passwort eingegeben.")
    return secret


def _read_env_file(env_path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not env_path.exists():
        return data
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip("'").strip('"')
        data[key.strip()] = value
    return data


def _load_fernet_key(fernet_key: Optional[str]) -> str:
    """
    Lädt den Fernet-Key aus Option oder Umgebung.
    """
    if fernet_key:
        return fernet_key
    secret = os.getenv("FERNET_KEY")
    if not secret:
        env_data = _read_env_file(Path(".env"))
        secret = env_data.get("FERNET_KEY")
    if not secret:
        new_key = Fernet.generate_key().decode()
        console.print("\nKein FERNET_KEY in Umgebung oder .env gefunden.")
        console.print("Ein neuer Schlüssel wurde generiert:")
        console.print(f"FERNET_KEY={new_key}")
        console.print("Bitte diesen Schlüssel in deiner .env eintragen und erneut ausführen.\n")
        raise ValueError("FERNET_KEY fehlt.")
    return secret


@app.command()
def main(
    secret: Optional[str] = typer.Argument(
        None,
        help="Klartext-Secret (optional; wird sonst interaktiv abgefragt).",
    ),
    fernet_key: Optional[str] = typer.Option(
        None,
        "--fernet-key",
        "-k",
        help="Fernet-Key (überschreibt FERNET_KEY aus der .env).",
    ),
    decode_key: Optional[str] = typer.Option(
        None,
        "--decode-key",
        help="Fernet-Token entschlüsseln (benötigt FERNET_KEY oder --fernet-key).",
    ),
) -> None:
    """
    Verschlüsselt ein Secret oder entschlüsselt einen Fernet-Token.
    """
    if decode_key:
        try:
            key = _load_fernet_key(fernet_key)
        except ValueError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(1)
        try:
            f = Fernet(key.encode())
            decrypted = f.decrypt(decode_key.encode())
        except Exception as exc:
            raise typer.BadParameter(f"Ungültiger Fernet-Token: {exc}") from exc
        try:
            console.print(f"Entschlüsseltes Secret: {decrypted.decode()}")
        except UnicodeDecodeError:
            console.print(f"Entschlüsseltes Secret (hex): {decrypted.hex()}")
        return

    try:
        plaintext = secret or _prompt_secret()
        key = _load_fernet_key(fernet_key)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

    f = Fernet(key.encode())
    encrypted = f.encrypt(plaintext.encode())
    console.print(f"Verschlüsseltes Passwort für .env: {encrypted.decode()}")


if __name__ == "__main__":
    app()
