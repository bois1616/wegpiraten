"""Erzeugt eine technische Kundenkopie, ohne Stammdaten oder SQLite zu verändern."""

import argparse
from pathlib import Path

from loguru import logger

from data_imports.workbook_upgrade import prepare_workbook
from shared_modules.config import Config


def main() -> None:
    """Die bewusste Quelldatei und ein separater Zielpfad sind Pflicht."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    result = prepare_workbook(Config(args.config), args.source, args.destination)
    logger.info("Umstellung abgeschlossen: {}", result.model_dump_json())


if __name__ == "__main__":
    main()
