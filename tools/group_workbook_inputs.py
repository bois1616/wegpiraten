"""Gruppiert Eingabespalten in einer separaten Kundenkopie."""

import argparse
from pathlib import Path

from loguru import logger

from data_imports.workbook_layout import describe_sheets, finish_input_presentation, group_input_columns
from data_imports.workbook_package import WorkbookPackage
from data_imports.workbook_upgrade import _findings, _inputs
from shared_modules.config import Config


def main() -> None:
    """Erhält Eingaben anhand von Tabellenname, Feld und Zeile statt Zelladresse."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    if args.source.resolve() == args.destination.resolve():
        raise ValueError("Zuerst eine separate Ausgabekopie vorbereiten.")
    config = Config()
    package = WorkbookPackage(args.source)
    inputs = _inputs(package, config)
    mappings = group_input_columns(package)
    describe_sheets(package)
    _findings(package)
    finish_input_presentation(package)
    assert _inputs(package, config) == inputs
    package.write(args.destination)
    logger.info("Eingaben erhalten: {}; neu geordnete Blätter: {}", len(inputs), list(mappings))


if __name__ == "__main__":
    main()
