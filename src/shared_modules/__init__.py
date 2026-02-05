import sys
from pathlib import Path

from .config import Config as Config  # Expliziter Re-Export

# Add the 'src' directory to the PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

__all__ = ["Config"]
