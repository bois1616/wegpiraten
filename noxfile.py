"""
Nox-Konfiguration für Wegpiraten.

Verwendung:
    nox              # Führt alle Standard-Sessions aus (lint, typecheck)
    nox -s lint      # Nur Linting mit ruff
    nox -s typecheck # Nur Type-Checking mit pyright
    nox -s typecheck_fast # Schneller Type-Check mit ty
    nox -s typecheck_all  # Type-Check mit ty und pyright
    nox -s test      # Unit-Tests mit pytest
    nox -s format    # Code formatieren mit ruff
    nox -l           # Verfügbare Sessions auflisten
"""

import nox

# Standard-Sessions, die bei `nox` ohne Argumente ausgeführt werden
nox.options.sessions = ["lint", "typecheck"]
nox.options.reuse_existing_virtualenvs = True

# Python-Version für alle Sessions
PYTHON_VERSION = "3.13"

# Source-Verzeichnis (ohne unused)
SRC_DIRS = [
    "src/cli.py",
    "src/shared_modules",
    "src/pydantic_models",
    "src/invoices",
    "src/time_sheets",
    "src/data_imports",
]

TYPECHECK_DEPS = [
    "pydantic>=2.11",
    "pandas>=2.3",
    "pandas-stubs>=2.3",
    "openpyxl>=3.1",
    "types-openpyxl>=3.1",
    "loguru>=0.7",
    "pyyaml>=6.0",
    "types-pyyaml>=6.0",
    "cryptography>=46.0",
    "typer>=0.21",
    "rich>=14.1",
    "docxtpl>=0.20",
    "sqlalchemy>=2.0",
    "babel>=2.17",
    "pillow>=11.0",
    "pypdf2>=3.0",
    "qrcode>=8.2",
    "types-qrcode>=8.2",
    "reportlab>=4.4",
    "types-reportlab>=4.4",
]


@nox.session(python=PYTHON_VERSION)
def lint(session: nox.Session) -> None:
    """Führt Linting mit ruff durch."""
    session.install("ruff>=0.15.0")
    session.run("ruff", "check", *SRC_DIRS)


@nox.session(python=PYTHON_VERSION)
def typecheck(session: nox.Session) -> None:
    """Führt Type-Checking mit pyright durch."""
    session.install("pyright>=1.1.408")
    # Installiere Projekt-Dependencies für Type-Checking
    session.install(*TYPECHECK_DEPS)
    session.run("pyright", *SRC_DIRS)


@nox.session(python=PYTHON_VERSION)
def typecheck_fast(session: nox.Session) -> None:
    """Führt schnellen Type-Checking mit ty durch."""
    session.install("ty>=0.0.34")
    session.install(*TYPECHECK_DEPS)
    session.run("ty", "check", *SRC_DIRS)


@nox.session(python=PYTHON_VERSION)
def test(session: nox.Session) -> None:
    """Führt Unit-Tests mit pytest durch."""
    session.install("pytest>=8.0", ".")
    session.run("pytest", "tests/", "--tb=short", env={"PYTHONPATH": "src"})


@nox.session(python=PYTHON_VERSION)
def format(session: nox.Session) -> None:
    """Formatiert Code mit ruff."""
    session.install("ruff>=0.15.0")
    session.run("ruff", "format", *SRC_DIRS)
    session.run("ruff", "check", "--fix", *SRC_DIRS)


@nox.session(python=PYTHON_VERSION)
def lint_fix(session: nox.Session) -> None:
    """Führt Linting mit automatischer Korrektur durch."""
    session.install("ruff>=0.15.0")
    session.run("ruff", "check", "--fix", *SRC_DIRS)


@nox.session(python=PYTHON_VERSION)
def check_all(session: nox.Session) -> None:
    """Führt alle Checks durch (lint + typecheck)."""
    session.notify("lint")
    session.notify("typecheck")


@nox.session
def typecheck_all(session: nox.Session) -> None:
    """Führt beide Type-Checker aus: zuerst ty, dann pyright."""
    session.notify("typecheck_fast")
    session.notify("typecheck")


@nox.session(python=PYTHON_VERSION)
def dev(session: nox.Session) -> None:
    """Installiert das Projekt im Entwicklungsmodus."""
    session.install("-e", ".[dev]")
    session.run("wegpiraten", "--help")
