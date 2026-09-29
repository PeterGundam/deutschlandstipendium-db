from pathlib import Path
import os

import psycopg
from psycopg.rows import dict_row
import streamlit as st
from dotenv import load_dotenv


# .env liegt im Projektordner, eine Ebene über app/
PROJEKTORDNER = Path(__file__).resolve().parent.parent
load_dotenv(PROJEKTORDNER / ".env")

st.set_page_config(
    page_title="Deutschlandstipendium",
    page_icon="🎓",
    layout="wide",
)


@st.cache_data(ttl=30)
def abfragen(sql: str, parameter: tuple = ()) -> list[dict]:
    """SQL ausführen und das Ergebnis für 30 Sekunden zwischenspeichern."""
    verbindungsdaten = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432"),
        "dbname": os.getenv("DB_NAME", "stipendium_db"),
        "user": os.getenv("DB_USER", "stipendium_user"),
        "password": os.getenv("DB_PASSWORD"),
        "connect_timeout": 5,
    }

    if not verbindungsdaten["password"]:
        raise RuntimeError("DB_PASSWORD fehlt in der lokalen .env-Datei.")

    with psycopg.connect(**verbindungsdaten) as verbindung:
        with verbindung.cursor(row_factory=dict_row) as cursor:
            cursor.execute(sql, parameter)
            return cursor.fetchall()


SQL_BEWERBUNGEN = """
SELECT
    b.bewerbungs_nr,
    s.matrikel_nr,
    p.vorname,
    p.nachname,
    st.bezeichnung AS stipendium,
    b.status,
    b.eingangsdatum
FROM bewerbung b
JOIN studierender s ON s.personen_id = b.studierenden_id
JOIN person p ON p.personen_id = s.personen_id
JOIN bewerbungszeitraum bz ON bz.zeitraum_id = b.zeitraum_id
JOIN stipendium st ON st.stipendium_id = bz.stipendium_id
ORDER BY b.bewerbungs_nr
"""

SQL_SUCHE = """
SELECT
    b.bewerbungs_nr,
    s.matrikel_nr,
    p.vorname,
    p.nachname,
    st.bezeichnung AS stipendium,
    b.status,
    b.eingangsdatum
FROM bewerbung b
JOIN studierender s ON s.personen_id = b.studierenden_id
JOIN person p ON p.personen_id = s.personen_id
JOIN bewerbungszeitraum bz ON bz.zeitraum_id = b.zeitraum_id
JOIN stipendium st ON st.stipendium_id = bz.stipendium_id
WHERE s.matrikel_nr = %s
ORDER BY b.bewerbungs_nr
"""

SQL_RANGLISTE = """
SELECT
    zeitraum_id,
    position,
    matrikel_nr,
    vorname,
    nachname,
    gesamt_score
FROM rangliste
ORDER BY zeitraum_id, position, bewerbungs_nr
"""


st.title("🎓 Deutschlandstipendium")
st.caption("Lokales Demo-Dashboard – Daten aus PostgreSQL")

bereich = st.sidebar.radio(
    "Bereich",
    ["Bewerbungsübersicht", "Bewerbung suchen", "Rangliste"],
)

try:
    if bereich == "Bewerbungsübersicht":
        st.header("Bewerbungsübersicht")
        daten = abfragen(SQL_BEWERBUNGEN)
        st.write(f"{len(daten)} Bewerbungen gefunden")
        if daten:
            st.dataframe(daten, hide_index=True, width="stretch")
        else:
            st.info("Noch keine Bewerbungen vorhanden.")

    elif bereich == "Bewerbung suchen":
        st.header("Bewerbung nach Matrikelnummer suchen")
        matrikel_nr = st.text_input("Matrikelnummer", placeholder="DEMO-1001")

        if matrikel_nr.strip():
            # Der Wert wird als Parameter übergeben, nicht in SQL hineinkopiert.
            daten = abfragen(SQL_SUCHE, (matrikel_nr.strip(),))
            if daten:
                st.dataframe(daten, hide_index=True, width="stretch")
            else:
                st.info("Keine Bewerbung zu dieser Matrikelnummer gefunden.")

    else:
        st.header("Rangliste")
        st.caption("Nur abgeschlossene Bewerbungen erscheinen in dieser View.")
        daten = abfragen(SQL_RANGLISTE)
        if daten:
            st.dataframe(daten, hide_index=True, width="stretch")
        else:
            st.info("Noch keine abgeschlossene Bewerbung in der Rangliste.")

except (psycopg.Error, RuntimeError) as fehler:
    # Keine Zugangsdaten oder ausführlichen Verbindungsdetails im Browser zeigen.
    st.error("Die Datenbankabfrage konnte nicht ausgeführt werden.")
    st.caption(f"Fehlertyp: {type(fehler).__name__}. Prüfe .env und PostgreSQL.")