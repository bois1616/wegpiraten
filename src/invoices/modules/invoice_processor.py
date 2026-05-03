import math
import sqlite3
from pathlib import Path
from typing import List, Optional
from zipfile import ZipFile

import pandas as pd
from jinja2 import Environment
from loguru import logger
from pandas._typing import Scalar

from shared_modules.config import Config
from shared_modules.entity import LegalPerson, PrivatePerson
from shared_modules.month_period import MonthPeriod, get_month_period
from shared_modules.utils import (
    clear_path,
    log_exceptions,
    safe_str,
    to_float,
    zip_invoices,
)

from .document_utils import DocumentUtils
from .filters import FilterConfig, register_filters
from .invoice_context import InvoiceContext
from .invoice_factory import InvoiceFactory
from .invoice_filter import InvoiceFilter

# Privatleistungs-Code: im Startmonat werden 15 min kostenfrei als Einführungsgespräch ausgewiesen
_PRIVATE_SERVICE_TYPE_CODE = "ST99"
_INTRO_FREE_MINUTES = 15


class InvoiceProcessor:
    """
    Koordiniert den Gesamtprozess der Rechnungserstellung:
    - Daten laden und prüfen
    - Rechnungen und PDFs erzeugen
    - Zusammenfassungen und ZIP-Archiv erstellen
    Nutzt konsequent Pydantic-Modelle für Konfiguration und Filter.
    """

    def __init__(self, config: Config, filter: InvoiceFilter):
        """
        Initialisiert den InvoiceProcessor mit Pydantic-basierter Konfiguration und Filter.
        Args:
            config (Config): Singleton-Konfiguration mit Pydantic-Modell.
            filter (InvoiceFilter): Pydantic-Modell mit den Filterkriterien.
        """
        self.config: Config = config
        self.filter: InvoiceFilter = filter
        self.invoice_factory: InvoiceFactory = InvoiceFactory(config)

    @staticmethod
    def _normalize_rounding(value: Optional[float]) -> float:
        """
        Normalisiert Rundung auf Minutenbasis.
        - Wenn rundung < 1, wird von Stunden ausgegangen und in Minuten umgerechnet.
        - Fallback auf 1 Minute bei ungültigen Werten.
        """
        step = to_float(value) or 0.0
        if step <= 0:
            return 1.0
        if step < 1:
            step = step * 60.0
        return step

    @classmethod
    def _round_minutes(cls, minutes_value: Optional[float], rounding: Optional[float]) -> int:
        # Werte sind bereits als Integer-Minuten gespeichert.
        minutes_raw = round(to_float(minutes_value) or 0.0, 6)
        step = cls._normalize_rounding(rounding)
        if step <= 0:
            return int(round(minutes_raw))
        step = round(step, 6)
        epsilon = 1e-6
        rounded = math.ceil((minutes_raw / step) - epsilon) * step
        return int(round(rounded))

    def _load_service_data(self, period: MonthPeriod) -> pd.DataFrame:
        """
        Lädt service_data aus der SQLite-DB und reichert sie mit Stammdaten an.
        Filtert nach dem Abrechnungsmonat und optionalen Filterkriterien.
        """
        db_path = self.config.get_db_path()
        start_date = period.start.date().isoformat()
        end_date = period.end.date().isoformat()

        tenant_select_sql = """
            NULL AS tenant_id,
            NULL AS tenant_name,
            NULL AS tenant_street,
            NULL AS tenant_zip,
            NULL AS tenant_city,
            NULL AS tenant_iban,
        """
        tenant_join_sql = ""
        tenant_source_expr = "NULL"

        with sqlite3.connect(db_path) as conn:
            service_data_columns = {row[1] for row in conn.execute("PRAGMA table_info(service_data)").fetchall()}
            client_columns = {row[1] for row in conn.execute("PRAGMA table_info(clients)").fetchall()}
            has_service_data_tenant = "tenant_id" in service_data_columns
            has_client_tenant = "tenant_id" in client_columns

            if has_service_data_tenant and has_client_tenant:
                tenant_source_expr = "COALESCE(sd.tenant_id, c.tenant_id)"
            elif has_service_data_tenant:
                tenant_source_expr = "sd.tenant_id"
            elif has_client_tenant:
                tenant_source_expr = "c.tenant_id"

            if has_service_data_tenant or has_client_tenant:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS masterdata_tenant (
                        tenant_id TEXT PRIMARY KEY,
                        name TEXT,
                        tenant_street TEXT,
                        tenant_zip TEXT,
                        tenant_city TEXT,
                        tenant_iban TEXT,
                        is_active INTEGER NOT NULL DEFAULT 1
                    )
                    """
                )
                tenant_select_sql = f"""
                    {tenant_source_expr} AS tenant_id,
                    t.name AS tenant_name,
                    t.tenant_street AS tenant_street,
                    t.tenant_zip AS tenant_zip,
                    t.tenant_city AS tenant_city,
                    t.tenant_iban AS tenant_iban,
                """
                tenant_join_sql = f"LEFT JOIN masterdata_tenant t ON {tenant_source_expr} = t.tenant_id"
                tenant_columns = {row[1] for row in conn.execute("PRAGMA table_info(masterdata_tenant)").fetchall()}
                if "name" not in tenant_columns:
                    conn.execute("ALTER TABLE masterdata_tenant ADD COLUMN name TEXT")
                    logger.info("Tabelle masterdata_tenant um Spalte name erweitert.")
            else:
                logger.warning(
                    "Spalte tenant_id fehlt in service_data und clients. Tenant-Daten bleiben für die Faktura leer."
                )

            sql = f"""
        SELECT
            sd.client_id,
            sd.service_date,
            sd.travel_time,
            sd.direct_time,
            sd.indirect_time,
            sd.notes,
            sd.service_type AS service_type_raw,
            c.first_name AS client_first_name,
            c.last_name AS client_last_name,
            c.social_security_number AS client_social_security_number,
            {tenant_select_sql}
            c.start_date AS client_start_date,
            c.sr_ap_first_name AS sr_ap_first_name,
            c.sr_ap_last_name AS sr_ap_last_name,
            c.sr_ap_gender AS sr_ap_gender,
            COALESCE(c.allowed_travel_time, 0) AS allowed_travel_time,
            COALESCE(c.allowed_direct_effort, 0) AS allowed_direct_effort,
            COALESCE(c.allowed_indirect_effort, 0) AS allowed_indirect_effort,
            c.payer_id AS payer_id,
            c.service_requester_id AS service_requester_id,
            c.service_type AS service_type_id,
            p.name AS payer_name,
            p.name2 AS payer_name2,
            p.street AS payer_street,
            p.zip_code AS payer_zip,
            p.city AS payer_city,
            sr.name AS service_requester_name,
            COALESCE(st_id.code, st_code.code) AS service_type_code,
            COALESCE(st_id.description, st_code.description) AS service_type_description,
            COALESCE(st_id.hourly_rate, st_code.hourly_rate) AS hourly_rate,
            COALESCE(st_id.rundung, st_code.rundung) AS rundung
        FROM service_data sd
        JOIN clients c ON sd.client_id = c.client_id
        LEFT JOIN payer p ON c.payer_id = p.payer_id
        {tenant_join_sql}
        LEFT JOIN service_requester sr ON c.service_requester_id = sr.service_requester_id
        LEFT JOIN service_types st_code
            ON st_code.rowid = (
                SELECT stc.rowid
                FROM service_types stc
                WHERE stc.code = sd.service_type
                ORDER BY stc.is_active DESC, COALESCE(stc.from_date, '') DESC, stc.rowid DESC
                LIMIT 1
            )
        LEFT JOIN service_types st_id ON c.service_type = st_id.service_type_id
        WHERE sd.service_date BETWEEN ? AND ?
        """
            params: List[Scalar] = [start_date, end_date]

            if self.filter.payer:
                sql += " AND c.payer_id = ?"
                params.append(self.filter.payer)
            if self.filter.client:
                sql += " AND sd.client_id = ?"
                params.append(self.filter.client)
            if self.filter.service_requester:
                sql += " AND (c.service_requester_id = ? OR sr.name = ?)"
                params.extend([self.filter.service_requester, self.filter.service_requester])
            if self.filter.payer_list:
                placeholders = ", ".join(["?"] * len(self.filter.payer_list))
                sql += f" AND c.payer_id IN ({placeholders})"
                params.extend(self.filter.payer_list)
            if self.filter.client_list:
                placeholders = ", ".join(["?"] * len(self.filter.client_list))
                sql += f" AND sd.client_id IN ({placeholders})"
                params.extend(self.filter.client_list)

            sql += " ORDER BY c.payer_id, sd.client_id, sd.service_date"
            df = pd.read_sql_query(sql, conn, params=params)

        if "service_date" in df.columns:
            df["service_date"] = pd.to_datetime(df["service_date"], errors="coerce").dt.date

        return df

    def run(self) -> None:
        """
        Führt den gesamten Rechnungsprozess aus.
        Nutzt ausschließlich typisierte und validierte Pydantic-Modelle.
        """
        logger.info(f"Starte Rechnungsprozess mit Filter: {self.filter}")

        # Zugriff auf die Struktur-Konfiguration über das Pydantic-Modell
        structure = self.config.get_structure()
        project_root = Path(structure.prj_root)
        tmp_path = project_root / (structure.tmp_path or "")
        output_path = project_root / (structure.output_path or "")

        clear_path(tmp_path)
        logger.debug(f"Temporäres Verzeichnis {tmp_path} geleert.")

        # Zeitraum für den gesamten Rechnungsprozess als MonthPeriod berechnen
        period: MonthPeriod = get_month_period(self.filter.invoice_month)
        start_inv_period: str = period.start.strftime("%d.%m.%Y")
        end_inv_period: str = period.end.strftime("%d.%m.%Y")

        invoice_data = self._load_service_data(period)
        if invoice_data.empty:
            logger.warning("Keine service_data im Abrechnungsmonat gefunden.")
            return
        logger.info(f"{len(invoice_data)} Leistungsdatensätze geladen.")

        service_provider_obj: LegalPerson = self.invoice_factory.provider
        logger.debug(f"Empfänger der Rechnungen: {service_provider_obj}")

        invoice_list: List[InvoiceContext] = []
        all_invoices: List[Path] = []
        all_docx: List[Path] = []

        # Jinja2-Environment mit typisierter Filter-Konfiguration initialisieren
        formatting = self.config.formatting
        filter_config = FilterConfig(
            locale=formatting.locale or "de_CH",
            currency=formatting.currency or "CHF",
            currency_format=formatting.currency_format or "#,##0.00 ¤",
            date_format=formatting.date_format or "dd.MM.yyyy",
            numeric_format=formatting.numeric_format or "#,##0.00",
        )
        jinja_env = Environment()
        register_filters(jinja_env, filter_config)

        # Gruppierung nach Zahlungsdienstleister (ZDNR)
        for payer_id, payer_data in invoice_data.groupby("payer_id"):
            if payer_id is None or (isinstance(payer_id, float) and payer_id != payer_id):
                logger.error("Fehlende payer_id in service_data – überspringe Gruppe.")
                continue
            payer_row = payer_data.iloc[0]

            invoices_for_payer: List[Path] = []

            # LegalPerson wird mit typisierten Feldern aus der DataFrame-Zeile erstellt
            payer_obj = LegalPerson(
                name=safe_str(payer_row.get("payer_name")),
                name_2=safe_str(payer_row.get("payer_name2")),
                street=safe_str(payer_row.get("payer_street")),
                zip=safe_str(payer_row.get("payer_zip")),
                city=safe_str(payer_row.get("payer_city")),
                iban=None,
                key=safe_str(payer_id),
            )

            logger.debug(
                f"Erstelle Rechnungen für Zahlungsdienstleister: {payer_obj.key} (ZDNR: {payer_id}) mit {len(payer_data)} Positionen"
            )

            # Kontext für die Zusammenführung der PDFs pro ZDNR
            payer_context = InvoiceContext(
                data={
                    "payer": payer_obj,
                    "start_inv_period": start_inv_period,
                    "end_inv_period": end_inv_period,
                    "invoice_month": self.filter.invoice_month,
                    "service_date_range": period,  # MonthPeriod für Templates und weitere Verarbeitung
                }
            )

            for client_id, client_details in payer_data.groupby("client_id"):
                if client_id is None or (isinstance(client_id, float) and client_id != client_id):
                    logger.error("Fehlende client_id in service_data – überspringe Datensätze.")
                    continue
                client_row = client_details.iloc[0]

                # PrivatePerson wird mit typisierten Feldern aus der DataFrame-Zeile erstellt
                client_obj = PrivatePerson(
                    first_name=safe_str(client_row.get("client_first_name")),
                    last_name=safe_str(client_row.get("client_last_name")),
                    street="",
                    zip_city="",
                    birth_date="",
                    social_security_number=safe_str(client_row.get("client_social_security_number")),
                    key=safe_str(client_id),
                )
                client_name = ", ".join(
                    part
                    for part in [
                        safe_str(client_obj.last_name),
                        safe_str(client_obj.first_name),
                    ]
                    if part
                )

                logger.debug(
                    f"Erstelle Rechnung für Klient: {client_obj.name} ({client_obj.key}) mit {len(client_details)} Positionen"
                )

                # Leistungsbesteller und Betreuungstyp aus den Daten holen
                service_requester = client_row.get("service_requester_name", "")
                service_type = client_row.get("service_type_code") or client_row.get("service_type_raw") or ""
                service_type_description = client_row.get("service_type_description") or ""

                invoice_id = self.invoice_factory.create_invoice_id(
                    client_id=str(client_id), invoice_month=self.filter.invoice_month
                )

                # Privatleistung im Startmonat: erste 15 min werden kostenfrei ausgewiesen
                is_private_intro_month = False
                if service_type == _PRIVATE_SERVICE_TYPE_CODE:
                    client_start_date_raw = client_row.get("client_start_date")
                    if client_start_date_raw:
                        try:
                            start_dt = pd.to_datetime(str(client_start_date_raw)).date()
                            is_private_intro_month = (
                                start_dt.year == period.start.year and start_dt.month == period.start.month
                            )
                        except Exception:
                            logger.warning(
                                "Startdatum für Klient {} nicht parsbar: {} – Einführungsregelung nicht angewendet.",
                                client_id,
                                client_start_date_raw,
                            )

                positions = []
                sum_fahrtzeit = 0
                sum_direkt = 0
                sum_indirekt = 0
                sum_stunden = 0
                sum_kosten = 0.0
                remaining_intro_minutes = _INTRO_FREE_MINUTES if is_private_intro_month else 0

                # Zeilen aufteilen: «ohne Berechnung»-Einträge (Notiz, case-insensitiv) bleiben
                # als eigene Rechnungsposition erhalten; alle anderen werden je Tag summiert.
                details_sorted = client_details.sort_values("service_date")  # pyright: ignore[reportCallIssue]
                is_intro_mask = details_sorted["notes"].apply(lambda v: "ohne berechnung" in str(v or "").lower())
                intro_rows = details_sorted[is_intro_mask]
                normal_rows = details_sorted[~is_intro_mask]

                date_groups = (
                    normal_rows.groupby("service_date", as_index=False)
                    .agg(
                        travel_time=("travel_time", "sum"),
                        direct_time=("direct_time", "sum"),
                        indirect_time=("indirect_time", "sum"),
                        hourly_rate=("hourly_rate", "first"),
                        rundung=("rundung", "first"),
                    )
                    .sort_values("service_date")  # pyright: ignore[reportCallIssue]
                )

                has_intro_position = False

                def _make_position(
                    service_date: object,
                    fahrtzeit: int,
                    direkt: int,
                    indirekt: int,
                    hourly_rate: float,
                    is_intro: bool,
                ) -> dict:
                    minuten_total = fahrtzeit + direkt + indirekt
                    kosten = 0.0 if is_intro else (minuten_total / 60.0) * hourly_rate
                    return {
                        "Leistungsdatum": service_date,
                        "Bezeichnung": "",
                        "Fahrtzeit": fahrtzeit,
                        "Direkt": direkt,
                        "Indirekt": indirekt,
                        "Stunden": minuten_total,
                        "Kosten": kosten,
                        "is_intro": is_intro,
                    }

                # «ohne Berechnung»-Positionen als separate Zeilen (nicht aggregiert, Kosten=0)
                for _, irow in intro_rows.iterrows():
                    service_date = irow.get("service_date")
                    if service_date is None or pd.isna(service_date):
                        continue
                    rundung = irow.get("rundung")
                    fahrtzeit = self._round_minutes(irow.get("travel_time"), rundung)
                    direkt = self._round_minutes(irow.get("direct_time"), rundung)
                    indirekt = self._round_minutes(irow.get("indirect_time"), rundung)
                    minuten_total = fahrtzeit + direkt + indirekt
                    if minuten_total == 0:
                        continue
                    has_intro_position = True
                    pos = _make_position(service_date, fahrtzeit, direkt, indirekt, 0.0, is_intro=True)
                    positions.append(pos)
                    sum_fahrtzeit += fahrtzeit
                    sum_direkt += direkt
                    sum_indirekt += indirekt
                    sum_stunden += minuten_total
                    # sum_kosten bleibt 0 für diese Zeilen

                # Normale Positionen je Tag aggregiert
                for _, row in date_groups.iterrows():
                    service_date = row.get("service_date")
                    if service_date is None or pd.isna(service_date):
                        logger.error("Fehlendes Leistungsdatum bei Client {} – Zeile ignoriert.", client_id)
                        continue
                    hourly_rate = to_float(row.get("hourly_rate"))
                    if hourly_rate is None:
                        logger.error(
                            "Kein Stundensatz für Client {} ({}) am {} – Zeile ignoriert.",
                            client_obj.name,
                            client_id,
                            service_date,
                        )
                        continue
                    rundung = row.get("rundung")
                    fahrtzeit = self._round_minutes(row.get("travel_time"), rundung)
                    direkt = self._round_minutes(row.get("direct_time"), rundung)
                    indirekt = self._round_minutes(row.get("indirect_time"), rundung)

                    # Einführungsgespräch (Startmonat): kostenfreie Freiminuten von direct_time abziehen
                    if remaining_intro_minutes > 0 and direkt > 0:
                        intro_direct = min(remaining_intro_minutes, direkt)
                        remaining_intro_minutes -= intro_direct
                        has_intro_position = True
                        positions.append(
                            {
                                "Leistungsdatum": service_date,
                                "Bezeichnung": "Einführungsgespräch – ohne Berechnung",
                                "Fahrtzeit": 0,
                                "Direkt": intro_direct,
                                "Indirekt": 0,
                                "Stunden": intro_direct,
                                "Kosten": 0.0,
                                "is_intro": True,
                            }
                        )
                        sum_direkt += intro_direct
                        sum_stunden += intro_direct
                        direkt -= intro_direct

                    minuten_total = fahrtzeit + direkt + indirekt
                    kosten = (minuten_total / 60.0) * hourly_rate

                    if minuten_total > 0:
                        positions.append(
                            _make_position(service_date, fahrtzeit, direkt, indirekt, hourly_rate, is_intro=False)
                        )
                        sum_fahrtzeit += fahrtzeit
                        sum_direkt += direkt
                        sum_indirekt += indirekt
                        sum_stunden += minuten_total
                        sum_kosten += kosten

                if not positions:
                    logger.warning("Keine gültigen Positionen für Client {} – Rechnung übersprungen.", client_id)
                    continue

                totals = {
                    "summe_fahrtzeit": sum_fahrtzeit,
                    "summe_direkt": sum_direkt,
                    "summe_indirekt": sum_indirekt,
                    "summe_stunden": sum_stunden,
                    "summe_kosten": sum_kosten,
                }

                allowed_travel = int(client_row.get("allowed_travel_time") or 0)
                allowed_direct = int(client_row.get("allowed_direct_effort") or 0)
                allowed_indirect = int(client_row.get("allowed_indirect_effort") or 0)
                budget_exceeded = (
                    (allowed_travel > 0 and sum_fahrtzeit > allowed_travel)
                    or (allowed_direct > 0 and sum_direkt > allowed_direct)
                    or (allowed_indirect > 0 and sum_indirekt > allowed_indirect)
                )

                # Rechnungen mit Betrag 0 werden zugelassen wenn Privatleistung im Startmonat
                # oder mindestens eine Position als «ohne Berechnung» markiert ist.
                if sum_stunden == 0 or (sum_kosten == 0 and not is_private_intro_month and not has_intro_position):
                    logger.warning(
                        "Rechnung für Client {} übersprungen: Zeitsumme={} Min, Betrag={} CHF.",
                        client_id,
                        sum_stunden,
                        sum_kosten,
                    )
                    continue

                invoice_context = InvoiceContext(
                    data={
                        "invoice_id": invoice_id,
                        "invoice_date": pd.Timestamp.now(),
                        "invoice_month": self.filter.invoice_month,
                        "start_inv_period": start_inv_period,
                        "end_inv_period": end_inv_period,
                        "service_date_range": period,  # MonthPeriod für Templates und weitere Verarbeitung
                        "service_requester": service_requester,
                        "service_type": service_type,
                        "care_type": service_type,
                        "payer": payer_obj,
                        "service_provider": service_provider_obj,
                        "provider_city": safe_str(service_provider_obj.city),
                        "tenant_id": safe_str(client_row.get("tenant_id")),
                        "tenant_name": safe_str(client_row.get("tenant_name")),
                        "tenant_street": safe_str(client_row.get("tenant_street")),
                        "tenant_zip": safe_str(client_row.get("tenant_zip")),
                        "tenant_city": safe_str(client_row.get("tenant_city")),
                        "tenant_iban": safe_str(client_row.get("tenant_iban")),
                        "client_name": client_name or safe_str(client_obj.name),
                        "service_type_description": service_type_description,
                        "client": client_obj,
                        "has_intro_position": has_intro_position,
                        "allowed_travel_time": allowed_travel,
                        "allowed_direct_effort": allowed_direct,
                        "allowed_indirect_effort": allowed_indirect,
                        "budget_exceeded": budget_exceeded,
                        "sr_ap_first_name": safe_str(client_row.get("sr_ap_first_name")),
                        "sr_ap_last_name": safe_str(client_row.get("sr_ap_last_name")),
                        "sr_ap_gender": safe_str(client_row.get("sr_ap_gender")),
                        "positions": positions,
                        **totals,
                    }
                )

                with log_exceptions(f"Fehler bei PDF-Erstellung für Klient {client_id}"):
                    rendered_invoice = self.invoice_factory.render_invoice(
                        invoice_context=invoice_context,
                        jinja_env=jinja_env,
                    )
                    # docx_name = f"Rechnung_{payer_id}_{client_id}_{self.filter.invoice_month}.docx"
                    docx_name = f"RE {client_obj.key} - {client_obj.first_name} {client_obj.last_name} ({self.filter.invoice_month}).docx"
                    docx_path = output_path / docx_name
                    rendered_invoice.save(docx_path)
                    all_docx.append(docx_path)
                    named_pdf = DocumentUtils.docx_to_pdf(docx_path, docx_path.with_suffix(".pdf"), invoice_context)
                    invoices_for_payer.append(named_pdf)
                    all_invoices.append(named_pdf)
                    invoice_list.append(invoice_context)

            with log_exceptions(f"Fehler beim Zusammenführen der PDFs für Kostenträger {payer_id}"):
                merged_pdf = DocumentUtils.merge_pdfs(invoices_for_payer, payer_context, output_path=output_path)
                logger.info(f"PDFs für Kostenträger {payer_id} zusammengeführt in {merged_pdf.name}")

        with log_exceptions("Fehler beim Erstellen der Rechnungsübersicht"):
            summary_file = DocumentUtils.create_summary(
                config=self.config,
                invoice_list=invoice_list,
            )
            logger.info(f"Rechnungsübersicht als Excel-Datei {summary_file.name} erstellt")

        with log_exceptions("Fehler beim Archivieren der Rechnungsdokumente"):
            zip_invoices(
                all_invoices,
                output_path / f"Rechnungen_{start_inv_period}_bis_{end_inv_period}.zip",
            )
            logger.success("Alle Rechnungsdokumente wurden erfolgreich archiviert.")

        if all_docx:
            docx_zip = output_path / f"Rechnungen_DOCX_{start_inv_period}_bis_{end_inv_period}.zip"
            with ZipFile(docx_zip, "w") as zipf:
                for file in all_docx:
                    if file.exists():
                        zipf.write(file, arcname=file.name)
                    else:
                        logger.warning("DOCX fehlt und wird nicht gezippt: {}", file)
            logger.success(f"DOCX-Archiv erstellt: {docx_zip.name}")


if __name__ == "__main__":
    print("InvoiceProcessor Modul. Nicht direkt ausführbar.")
