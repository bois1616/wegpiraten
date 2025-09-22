from pathlib import Path
from module.config import Config
from module.reporting_factory import ReportingFactory
from module.reporting_processor import ReportingProcessor

def main():
    config_path = Path(__file__).parent.parent.parent / ".config" / "wegpiraten_config.yaml"
    config = Config()
    config.load(config_path)

    prj_root = Path(config.data["structure"]["prj_root"])
    output_path = prj_root / config.data["structure"]["output_path"]
    template_path = prj_root / config.data["structure"]["template_path"]

    reporting_month = "2025-09"  # Beispiel: September 2025

    factory = ReportingFactory(config)
    processor = ReportingProcessor(config, factory)
    processor.run(reporting_month, output_path, template_path)

if __name__ == "__main__":
    main()