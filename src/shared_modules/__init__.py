from .config import Config
import sys
from pathlib import Path

# Add the 'src' directory to the PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))