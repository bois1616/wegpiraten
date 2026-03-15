"""
Tests für generate_scor (ISO 11649 Structured Creditor Reference / RF-Referenz).
"""

import pytest

from invoices.modules.invoice_factory import generate_scor


def _is_valid_scor(rfnb: str) -> bool:
    """Prüft eine RF-Referenz: rotierende Ziffernfolge MOD 97 == 1."""
    if not rfnb.startswith("RF") or len(rfnb) < 5:
        return False
    rotated = rfnb[4:] + rfnb[:4]
    numeric = "".join(str(ord(c) - ord("A") + 10) if c.isalpha() else c for c in rotated)
    return int(numeric) % 97 == 1


# --- Bekannte Referenzwerte (ISO-11649-Beispiel) ---


def test_known_reference():
    """Bekannter ISO-11649-Beispielwert: '539007547034' → RF18539007547034."""
    assert generate_scor("539007547034") == "RF18539007547034"


# --- Typische Rechnungsnummern aus dem Projekt ---


def test_typical_invoice_number():
    """Typische Rechnungsnummer 2026-03-C1010: Sonderzeichen werden entfernt."""
    rfnb = generate_scor("2026-03-C1010")
    assert rfnb.startswith("RF")
    assert _is_valid_scor(rfnb)


def test_typical_invoice_number_private():
    """Weitere typische Rechnungsnummer 2026-02-C1038."""
    rfnb = generate_scor("2026-02-C1038")
    assert rfnb.startswith("RF")
    assert _is_valid_scor(rfnb)


# --- Randfälle ---


def test_long_invoice_truncated_to_21():
    """Referenz wird auf 21 alphanumerische Zeichen gekürzt; Ergebnis max. 25 Zeichen."""
    rfnb = generate_scor("2026-02-C1038-EXTRA-LONG-NUMBER-EXCEEDING-LIMIT")
    assert rfnb.startswith("RF")
    assert len(rfnb) <= 25  # 2 (RF) + 2 (check) + 21 (ref)
    assert _is_valid_scor(rfnb)


def test_empty_invoice_falls_back_to_zero():
    """Leere / rein sonderzeichenhaltige Eingabe → Fallback-Referenz '0'."""
    rfnb = generate_scor("---")
    assert rfnb.startswith("RF")
    assert _is_valid_scor(rfnb)


@pytest.mark.parametrize(
    "invoice_id",
    [
        "2026-01-C1000",
        "2025-12-C9999",
        "01-2026-C1010",
        "RE2026C1010",
    ],
)
def test_various_formats_produce_valid_scor(invoice_id: str):
    """Verschiedene Rechnungsformate → immer gültige SCOR-Referenz."""
    rfnb = generate_scor(invoice_id)
    assert _is_valid_scor(rfnb), f"Ungültige SCOR-Referenz für '{invoice_id}': {rfnb}"
