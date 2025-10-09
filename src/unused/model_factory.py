from __future__ import annotations

from datetime import date
from typing import Any, Dict, Iterable, Optional, Tuple, Type

from pydantic import BaseModel, create_model
from shared_modules.config import Config

# YAML-Typ → Python-Typ
_PY_TYPE_MAP: Dict[str, Type[Any]] = {
    "str": str,
    "float": float,
    "int": int,
    "bool": bool,
    "currency": float,  # optional: Decimal
}

def build_entity_model(
    *,
    name: str,
    config: Config,
    entity: str,
    include_fields: Optional[Iterable[str]] = None,
    use_is_position: Optional[bool] = None,  # None = ignorieren (Import/Export), True/False = filtern (Invoice-Table)
    type_overrides: Optional[Dict[str, Type[Any]]] = None,
    extras: Optional[Dict[str, Tuple[Type[Any], Any]]] = None,
    base: Type[BaseModel] = BaseModel,
) -> Type[BaseModel]:
    """
    Erzeugt zur Laufzeit ein Pydantic-Modell aus config.models[entity].
    - include_fields: explizite Feldmenge (Whitelist) oder None = alle
    - use_is_position: None = Flag ignorieren, True/False = entsprechend filtern
    - type_overrides: erzwungene Python-Typen für Felder (z.B. service_date -> date)
    - extras: zusätzliche Felder (Name -> (Typ, Default))
    """
    entity_cfg = config.models.get(entity)
    assert entity_cfg is not None, f"Unbekannte Entity '{entity}' in Config."
    wanted = set(include_fields) if include_fields else None
    overrides = type_overrides or {}

    fields_spec: Dict[str, Tuple[Any, Any]] = {}

    for f in entity_cfg.fields:
        # optionaler Filter auf is_position (nur für Tabellenspalten in Invoice-Factory gedacht)
        if use_is_position is not None:
            if bool(getattr(f, "is_position", False)) is not use_is_position:
                continue
        if wanted is not None and f.name not in wanted:
            continue

        py_type = overrides.get(f.name)
        if py_type is None:
            mapped = _PY_TYPE_MAP.get(f.type)
            assert mapped is not None, f"Nicht unterstützter Typ '{f.type}' für Feld '{f.name}'."
            py_type = mapped

        default = None if getattr(f, "optional", False) else ...
        fields_spec[f.name] = (py_type, default)

    if extras:
        for key, (tp, default) in extras.items():
            fields_spec[key] = (tp, default)

    return create_model(name, __base__=base, **fields_spec)


# Convenience-Builder für häufige Fälle

def make_invoice_row_model(config: Config) -> Type[BaseModel]:
    """
    Positions-/Faktenzeile für invoice_data (Import/Export).
    is_position wird IGNORIERT (use_is_position=None), damit alle benötigten Felder verfügbar sind.
    """
    return build_entity_model(
        name="InvoiceRowModel",
        config=config,
        entity="invoice_data",
        include_fields={
            "client_id", "service_date", "service_type",
            "travel_time", "direct_time", "indirect_time",
            "billable_hours", "hourly_rate", "total_hours", "total_costs",
        },
        use_is_position=None,
        type_overrides={"service_date": date},
        extras={"employee_id": (str, None)},  # kommt aus clients-Header
    )


def make_client_header_model(config: Config) -> Type[BaseModel]:
    """
    Kopf-/Headerdaten aus client für das Reporting-Sheet.
    """
    return build_entity_model(
        name="ReportingHeaderModel",
        config=config,
        entity="client",
        include_fields={"client_id", "employee_id", "allowed_hours_per_month", "service_type", "short_code"},
        use_is_position=None,
    )