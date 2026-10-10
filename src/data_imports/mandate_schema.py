"""Abgeleitete Auftragsdaten für Bögen und Rechnungen."""

import sqlite3

# Die Herkunftszeile entscheidet wie INDEX/MATCH bei gleichem Geburtsdatum.
_VIEW_SQL = """
CREATE VIEW v_mandate AS
WITH chosen AS (
    SELECT m.mandate_id,
        (SELECT b.person_id FROM mandate_person b
         WHERE b.mandate_id=m.mandate_id ORDER BY b.source_row LIMIT 1) AS care_person_id
    FROM mandate m
), index_children AS (
    SELECT c.mandate_id,
        CASE WHEN COALESCE(p.family_key,'')='' THEN p.person_id
        ELSE (SELECT sibling.person_id FROM person sibling
              WHERE sibling.family_key=p.family_key
                AND sibling.date_of_birth IS NOT NULL
              ORDER BY sibling.date_of_birth DESC, sibling.source_row LIMIT 1)
        END AS index_person_id
    FROM chosen c LEFT JOIN person p ON p.person_id=c.care_person_id
)
SELECT m.*, m.mandate_id AS client_id, m.service_type_id AS service_type,
    i.index_person_id, p.family_id, p.short_code,
    p.first_name, p.last_name, p.social_security_number,
    ap.gender AS sr_ap_gender, ap.first_name AS sr_ap_first_name,
    ap.last_name AS sr_ap_last_name,
    COALESCE(m.allowed_travel_time,0)+COALESCE(m.allowed_direct_effort,0)
        +COALESCE(m.allowed_indirect_effort,0) AS allowed_hours_per_month
FROM mandate m
LEFT JOIN index_children i ON i.mandate_id=m.mandate_id
LEFT JOIN person p ON p.person_id=i.index_person_id
LEFT JOIN masterdata_contact_person ap ON ap.contact_person_id=m.contact_person_id
"""


def create_mandate_view(conn: sqlite3.Connection) -> None:
    """Erstellt genau eine Ausgabezeile je Auftrag, auch ohne gültiges Indexkind."""
    conn.execute("DROP VIEW IF EXISTS v_mandate")
    conn.execute(_VIEW_SQL)
