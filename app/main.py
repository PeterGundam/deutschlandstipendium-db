from pathlib import Path
import base64
import hashlib
import hmac
import os

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
import streamlit as st


PROJEKTORDNER = Path(__file__).resolve().parent.parent
load_dotenv(PROJEKTORDNER / ".env")

st.set_page_config(
    page_title="Deutschlandstipendium",
    page_icon="🎓",
    layout="wide",
)


def verbindung_oeffnen():
    passwort = os.getenv("DB_PASSWORD")
    if not passwort:
        raise RuntimeError("DB_PASSWORD fehlt in der lokalen .env-Datei.")

    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "stipendium_db"),
        user=os.getenv("DB_USER", "stipendium_user"),
        password=passwort,
        connect_timeout=5,
    )


def abfragen(sql: str, parameter: tuple = ()) -> list[dict]:
    with verbindung_oeffnen() as verbindung:
        with verbindung.cursor(row_factory=dict_row) as cursor:
            cursor.execute(sql, parameter)
            return cursor.fetchall()


def passwort_pruefen(passwort: str, gespeicherter_hash: str) -> bool:
    """Prüft das Format aus app/demo_konto_anlegen.py."""
    try:
        verfahren, n, r, p, salt_text, hash_text = gespeicherter_hash.split("$")
        if verfahren != "scrypt":
            return False

        salt = base64.b64decode(salt_text, validate=True)
        erwarteter_hash = base64.b64decode(hash_text, validate=True)

        berechneter_hash = hashlib.scrypt(
            passwort.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(erwarteter_hash),
            maxmem=64 * 1024 * 1024,
        )
        return hmac.compare_digest(berechneter_hash, erwarteter_hash)
    except (ValueError, TypeError, OverflowError):
        return False


SQL_LOGIN = """
SELECT
    l.personen_id,
    l.passwort_hash,
    p.vorname,
    p.nachname,
    (s.personen_id IS NOT NULL) AS ist_bewerber,
    (k.personen_id IS NOT NULL) AS ist_kommission
FROM login_konto l
JOIN person p ON p.personen_id = l.personen_id
LEFT JOIN studierender s ON s.personen_id = l.personen_id
LEFT JOIN kommissionsmitglied k ON k.personen_id = l.personen_id
WHERE lower(l.email) = lower(%s)
  AND l.aktiv = TRUE
"""

# Bewerber: Jede personenbezogene Abfrage ist auf die angemeldete
# personen_id begrenzt. Keine frei eingebbare fremde Matrikelnummer.
SQL_MEINE_BEWERBUNGEN = """
SELECT
    b.bewerbungs_nr,
    st.bezeichnung AS stipendium,
    bz.beginn,
    bz.ende,
    b.status,
    b.eingangsdatum
FROM bewerbung b
JOIN bewerbungszeitraum bz ON bz.zeitraum_id = b.zeitraum_id
JOIN stipendium st ON st.stipendium_id = bz.stipendium_id
WHERE b.studierenden_id = %s
ORDER BY b.bewerbungs_nr DESC
"""

SQL_MEINE_DOKUMENTE = """
SELECT
    d.dokument_id,
    d.dateiname,
    d.dokumenttyp,
    b.bewerbungs_nr
FROM dokument d
JOIN bewerbung b ON b.bewerbungs_nr = d.bewerbungs_nr
WHERE b.studierenden_id = %s
ORDER BY b.bewerbungs_nr, d.dokument_id
"""

SQL_MEINE_ENTSCHEIDUNGEN = """
SELECT
    b.bewerbungs_nr,
    st.bezeichnung AS stipendium,
    a.foerderstatus,
    a.entscheidungsdatum,
    a.begruendung
FROM auswahlentscheidung a
JOIN bewerbung b ON b.bewerbungs_nr = a.bewerbungs_nr
JOIN bewerbungszeitraum bz ON bz.zeitraum_id = b.zeitraum_id
JOIN stipendium st ON st.stipendium_id = bz.stipendium_id
WHERE b.studierenden_id = %s
ORDER BY a.entscheidungsdatum DESC
"""

SQL_MEINE_NACHRICHTEN = """
SELECT
    b.bewerbungs_nr,
    n.datum,
    n.typ,
    n.sendestatus
FROM benachrichtigung n
JOIN bewerbung b ON b.bewerbungs_nr = n.bewerbungs_nr
WHERE b.studierenden_id = %s
ORDER BY n.datum DESC
"""

# Kommission: Leseansichten für den bisherigen Demo-Arbeitsstand.
SQL_ALLE_BEWERBUNGEN = """
SELECT
    b.bewerbungs_nr,
    s.matrikel_nr,
    p.vorname,
    p.nachname,
    st.bezeichnung AS stipendium,
    b.status
FROM bewerbung b
JOIN studierender s ON s.personen_id = b.studierenden_id
JOIN person p ON p.personen_id = s.personen_id
JOIN bewerbungszeitraum bz ON bz.zeitraum_id = b.zeitraum_id
JOIN stipendium st ON st.stipendium_id = bz.stipendium_id
ORDER BY b.bewerbungs_nr
"""

SQL_EINZELBEWERTUNGEN = """
SELECT
    bw.bewertung_id,
    bw.status AS bewertungsstatus,
    p.vorname || ' ' || p.nachname AS kommissionsmitglied,
    CASE
        WHEN bw.dokument_id IS NOT NULL THEN 'Dokument'
        WHEN bw.engagement_id IS NOT NULL THEN 'Engagement'
        WHEN bw.umstand_id IS NOT NULL THEN 'Lebensumstand'
        WHEN bw.auszeichnung_id IS NOT NULL THEN 'Auszeichnung'
    END AS gegenstandsart,
    k.name AS kriterium,
    bp.punkte,
    zk.gewichtung,
    bp.punkte * zk.gewichtung AS gewichtete_punkte
FROM bewertung bw
JOIN person p ON p.personen_id = bw.mitglied_id
JOIN bewerbung b ON b.bewerbungs_nr = bw.bewerbungs_nr
LEFT JOIN bewertungspunkt bp ON bp.bewertung_id = bw.bewertung_id
LEFT JOIN bewertungskriterium k ON k.kriterium_id = bp.kriterium_id
LEFT JOIN zeitraum_kriterium zk
    ON zk.zeitraum_id = b.zeitraum_id
   AND zk.kriterium_id = bp.kriterium_id
WHERE bw.bewerbungs_nr = %s
ORDER BY bw.bewertung_id, k.name
"""

SQL_DOKUMENTE_KOMMISSION = """
SELECT
    d.dokument_id,
    d.dateiname,
    d.dokumenttyp,
    ln.durchschnittsnote
FROM dokument d
LEFT JOIN leistungsnachweis ln ON ln.dokument_id = d.dokument_id
WHERE d.bewerbungs_nr = %s
ORDER BY d.dokument_id
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

SQL_ENTSCHEIDUNGEN_KOMMISSION = """
SELECT
    a.entscheidungs_id,
    a.bewerbungs_nr,
    a.foerderstatus,
    a.entscheidungsdatum,
    a.begruendung,
    COUNT(eb.mitglied_id) AS anzahl_beteiligte
FROM auswahlentscheidung a
LEFT JOIN entscheidungsbeteiligung eb
    ON eb.entscheidungs_id = a.entscheidungs_id
GROUP BY a.entscheidungs_id
ORDER BY a.entscheidungsdatum DESC, a.entscheidungs_id
"""


def tabelle_anzeigen(daten: list[dict], leertext: str) -> None:
    if daten:
        st.dataframe(daten, hide_index=True, width="stretch")
    else:
        st.info(leertext)


def login_anzeigen() -> None:
    st.title("🎓 Deutschlandstipendium")
    st.subheader("Anmelden")

    with st.form("login_formular"):
        email = st.text_input("E-Mail-Adresse").strip().lower()
        passwort = st.text_input("Passwort", type="password")
        abgeschickt = st.form_submit_button("Anmelden")

    if not abgeschickt:
        return

    try:
        konten = abfragen(SQL_LOGIN, (email,))
        konto = konten[0] if len(konten) == 1 else None

        if konto is None or not passwort_pruefen(
            passwort, konto["passwort_hash"]
        ):
            st.error("E-Mail oder Passwort ist falsch.")
            return

        # Genau eine Rolle muss vorliegen.
        if konto["ist_bewerber"] == konto["ist_kommission"]:
            st.error("Für dieses Konto ist keine eindeutige Rolle hinterlegt.")
            return

        rolle = (
            "bewerber" if konto["ist_bewerber"] else "kommission"
        )

        st.session_state["angemeldet"] = {
            "personen_id": konto["personen_id"],
            "vorname": konto["vorname"],
            "nachname": konto["nachname"],
            "rolle": rolle,
        }
        st.rerun()

    except (psycopg.Error, RuntimeError):
        st.error("Anmeldung derzeit nicht möglich. Prüfe PostgreSQL und .env.")


def bewerber_dashboard(personen_id: int) -> None:
    st.header("Mein Bewerber-Dashboard")
    bereich = st.sidebar.radio(
        "Bereich",
        [
            "Meine Bewerbungen",
            "Meine Dokumente",
            "Meine Benachrichtigungen",
            "Meine Entscheidung",
        ],
    )

    parameter = (personen_id,)

    if bereich == "Meine Bewerbungen":
        st.subheader("Meine Bewerbungen")
        tabelle_anzeigen(
            abfragen(SQL_MEINE_BEWERBUNGEN, parameter),
            "Du hast noch keine Bewerbung.",
        )

    elif bereich == "Meine Dokumente":
        st.subheader("Meine Dokumente")
        st.caption("Demodateipfade sind keine echten hochgeladenen Dateien.")
        tabelle_anzeigen(
            abfragen(SQL_MEINE_DOKUMENTE, parameter),
            "Für deine Bewerbungen sind noch keine Dokumente erfasst.",
        )

    elif bereich == "Meine Benachrichtigungen":
        st.subheader("Meine Benachrichtigungen")
        tabelle_anzeigen(
            abfragen(SQL_MEINE_NACHRICHTEN, parameter),
            "Noch keine Benachrichtigungen vorhanden.",
        )

    else:
        st.subheader("Meine Entscheidung")
        tabelle_anzeigen(
            abfragen(SQL_MEINE_ENTSCHEIDUNGEN, parameter),
            "Für deine Bewerbungen liegt noch keine Entscheidung vor.",
        )


def kommissions_dashboard() -> None:
    st.header("Kommissions-Dashboard")
    bereich = st.sidebar.radio(
        "Bereich",
        [
            "Bewerbungsübersicht",
            "Einzelbewertungen",
            "Dokumente",
            "Rangliste",
            "Auswahlentscheidungen",
        ],
    )

    if bereich == "Bewerbungsübersicht":
        st.subheader("Bewerbungsübersicht")
        tabelle_anzeigen(
            abfragen(SQL_ALLE_BEWERBUNGEN),
            "Noch keine Bewerbungen vorhanden.",
        )
        return

    if bereich == "Rangliste":
        st.subheader("Rangliste")
        st.caption("Nur abgeschlossene Bewerbungen erscheinen hier.")
        tabelle_anzeigen(
            abfragen(SQL_RANGLISTE),
            "Noch keine abgeschlossene Bewerbung in der Rangliste.",
        )
        return

    if bereich == "Auswahlentscheidungen":
        st.subheader("Auswahlentscheidungen")
        tabelle_anzeigen(
            abfragen(SQL_ENTSCHEIDUNGEN_KOMMISSION),
            "Noch keine Entscheidungen vorhanden.",
        )
        return

    bewerbungen = abfragen(SQL_ALLE_BEWERBUNGEN)
    if not bewerbungen:
        st.info("Noch keine Bewerbungen vorhanden.")
        return

    beschriftungen = {
        b["bewerbungs_nr"]: (
            f"Nr. {b['bewerbungs_nr']} – "
            f"{b['vorname']} {b['nachname']} ({b['matrikel_nr']})"
        )
        for b in bewerbungen
    }
    nummer = st.selectbox(
        "Bewerbung auswählen",
        list(beschriftungen),
        format_func=lambda nr: beschriftungen[nr],
    )

    if bereich == "Einzelbewertungen":
        st.subheader("Einzelbewertungen")
        daten = abfragen(SQL_EINZELBEWERTUNGEN, (nummer,))
        tabelle_anzeigen(daten, "Noch keine Bewertungen vorhanden.")

        if daten:
            score = sum(
                zeile["gewichtete_punkte"] or 0
                for zeile in daten
                if zeile["bewertungsstatus"] == "abgeschlossen"
            )
            st.metric("Score aus abgeschlossenen Bewertungen", f"{score:.2f}")

    else:
        st.subheader("Dokumente")
        tabelle_anzeigen(
            abfragen(SQL_DOKUMENTE_KOMMISSION, (nummer,)),
            "Für diese Bewerbung sind keine Dokumente erfasst.",
        )


if "angemeldet" not in st.session_state:
    login_anzeigen()
    st.stop()

benutzer = st.session_state["angemeldet"]

st.sidebar.write(
    f"Angemeldet: {benutzer['vorname']} {benutzer['nachname']}"
)
if st.sidebar.button("Abmelden"):
    del st.session_state["angemeldet"]
    st.rerun()

try:
    if benutzer["rolle"] == "bewerber":
        bewerber_dashboard(benutzer["personen_id"])
    elif benutzer["rolle"] == "kommission":
        kommissions_dashboard()
    else:
        st.error("Unbekannte Rolle. Bitte erneut anmelden.")
except (psycopg.Error, RuntimeError):
    st.error("Die Datenbankabfrage konnte nicht ausgeführt werden.")
    st.caption("Prüfe die lokale .env-Datei und PostgreSQL.")