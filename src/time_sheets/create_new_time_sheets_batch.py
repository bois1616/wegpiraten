from pathlib import Path
from loguru import logger

from shared_modules.config import Config
from shared_modules.utils import ensure_dir
from time_sheets.modules.time_sheet_factory import TimeSheetFactory
from time_sheets.modules.time_sheet_batch_processor import TimeSheetBatchProcessor


def main() -> None:
    """
    Einstiegspunkt für das Anlegen eines neuen Berichtsmonats.
    Vertraut auf die (bereits beim Laden geprüfte) Config, leitet Pfade ab
    und erstellt anschließend mit Factory + Processor alle Zeiterfassungs-Sheets.
    """
    config_path: Path = Path(__file__).parents[2] / ".config" / "wegpiraten_config.yaml"
    config = Config(config_path)

    structure = config.structure
    prj_root = Path(structure.prj_root)

    # Aus den (validierten) Config-Pfaden die Ziel-/Template-Verzeichnisse ableiten.
    output_path = ensure_dir(prj_root / (structure.output_path or "output"))
    template_path = prj_root / (structure.template_path or "templates")

    factory = TimeSheetFactory(config)
    processor = TimeSheetBatchProcessor(config, factory)

    reporting_month = "2025-10"
    logger.info(f"Starte Batch-Erstellung für {reporting_month}.")
    processor.run(reporting_month, output_path, template_path)


if __name__ == "__main__":
    main()

