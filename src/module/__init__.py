from .config import Config
from .invoice_processor import InvoiceProcessor
from .invoice_filter import InvoiceFilter
import sys
from pathlib import Path

# Add the 'src' directory to the PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))