
from dataclasses import dataclass, field
from typing import Any, Dict

@dataclass
class InvoiceContext:
    """Kontext für die Rechnung. Enthält nur rohe Werte, keine formatierte Strings."""
    data: Dict[str, Any] = field(default_factory=dict)

    def __getitem__(self, key):
        return self.data.get(key)

    def __setitem__(self, key, value):
        self.data[key] = value

    def as_dict(self):
        return self.data.copy()