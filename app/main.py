from pathlib import Path
import base64
import hashlib
import hmac
import os
import uuid

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
import streamlit as st


PROJEKTORDNER = Path(__file__).resolve().parent.parent
UPLOAD_ORDNER = PROJEKTORDNER / "private_uploads"
MAX_PDF_GROESSE = 10 * 1024 * 1024  # 10 MB

load_dotenv(PROJEKTORDNER / ".env")

st.set_page_config(
    page_title="Deutschlandstipendium",
    page_icon="🎓",
    layout="wide",
)


# ---------------------------------------------------------------------
# Datenbank und Anmeldung
# ---------------------------------------------------------------------

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
    """Führt eine lesende SQL-Abfrage aus."""
    with verbindung_oeffnen() as verbindung:
        with verbindung.cursor(row_factory=dict_row) as cursor:
            cursor.execute(sql, parameter)
            return cursor.fetchall()


def passwort_pruefen(passwort: str, gespeicherter_hash: str) -> bool:
    """Prüft den scrypt-Hash aus demo_konto_anlegen.py."""
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


# ---------------------------------------------------------------------
# SQL für Bewerber
# ---------------------------------------------------------------------

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
    b.bewerbungs_nr,
    d.dateiname,
    d.dokumenttyp
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

SQL_OFFENE_ZEITRAEUME = """
SELECT
    bz.zeitraum_id,
    st.bezeichnung,
    bz.beginn,
    bz.ende
FROM bewerbungszeitraum bz
JOIN stipendium st ON st.stipendium_id = bz.stipendium_id
WHERE CURRENT_DATE BETWEEN bz.beginn AND bz.ende
ORDER BY bz.ende, bz.zeitraum_id
"""

SQL_MEINE_ENTWUERFE = """
SELECT
    b.bewerbungs_nr,
    st.bezeichnung
FROM bewerbung b
JOIN bewerbungszeitraum bz ON bz.zeitraum_id = b.zeitraum_id
JOIN stipendium st ON st.stipendium_id = bz.stipendium_id
WHERE b.studierenden_id = %s
  AND b.status = 'Entwurf'
ORDER BY b.bewerbungs_nr DESC
"""


# ---------------------------------------------------------------------
# Schreibfunktionen für den Bewerber-Use-Case
# ---------------------------------------------------------------------

def entwurf_anlegen(personen_id: int, zeitraum_id: int) -> int | None:
    """
    Legt nur für einen aktuell offenen Zeitraum einen Entwurf an.
    Pro Studierendem und Zeitraum gibt es höchstens eine Bewerbung.
    """
    with verbindung_oeffnen() as verbindung:
        with verbindung.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO bewerbung (studierenden_id, zeitraum_id)
                SELECT %s, bz.zeitraum_id
                FROM bewerbungszeitraum bz
                WHERE bz.zeitraum_id = %s
                  AND CURRENT_DATE BETWEEN bz.beginn AND bz.ende
                  AND EXISTS (
                      SELECT 1
                      FROM studierender s
                      WHERE s.personen_id = %s
                  )
                ON CONFLICT (studierenden_id, zeitraum_id) DO NOTHING
                RETURNING bewerbungs_nr
                """,
                (personen_id, zeitraum_id, personen_id),
            )
            zeile = cursor.fetchone()
            return zeile[0] if zeile else None


def pdf_speichern(
    personen_id: int,
    bewerbungs_nr: int,
    dokumenttyp: str,
    datei,
) -> None:
    """
    Speichert eine echte PDF lokal und verknüpft sie mit dem eigenen Entwurf.
    Datenbankeintrag und Datei werden bei einem Fehler möglichst gemeinsam
    zurückgenommen.
    """
    if dokumenttyp not in ("Motivationsschreiben", "Leistungsnachweis"):
        raise ValueError("Unbekannter Dokumenttyp.")

    if datei is None:
        raise ValueError("Bitte zuerst eine PDF auswählen.")

    # Die Dateiendung im Browser allein beweist noch nicht, dass es ein PDF ist.
    if not datei.name.lower().endswith(".pdf"):
        raise ValueError("Bitte eine Datei mit der Endung .pdf auswählen.")

    inhalt = datei.getvalue()

    if not inhalt.startswith(b"%PDF-"):
        raise ValueError("Die Datei ist keine erkennbare PDF.")

    if len(inhalt) > MAX_PDF_GROESSE:
        raise ValueError("Die PDF darf höchstens 10 MB groß sein.")

    # Den Originalnamen nur für die Anzeige nutzen, nie als Speicherpfad.
    dateiname = datei.name.replace("\\", "/").split("/")[-1][:255]

    UPLOAD_ORDNER.mkdir(mode=0o700, exist_ok=True)
    zielpfad = UPLOAD_ORDNER / f"{uuid.uuid4().hex}.pdf"

    try:
        with verbindung_oeffnen() as verbindung:
            with verbindung.cursor() as cursor:
                # Nur die eigene Bewerbung im Status Entwurf bearbeiten.
                # FOR UPDATE sperrt sie während der Datenbanktransaktion.
                cursor.execute(
                    """
                    SELECT 1
                    FROM bewerbung
                    WHERE bewerbungs_nr = %s
                      AND studierenden_id = %s
                      AND status = 'Entwurf'
                    FOR UPDATE
                    """,
                    (bewerbungs_nr, personen_id),
                )

                if cursor.fetchone() is None:
                    raise ValueError(
                        "Nur eigene Bewerbungen im Status Entwurf "
                        "dürfen geändert werden."
                    )

                # Bei bereits vorhandenem Pflichtdokument nichts überschreiben.
                cursor.execute(
                    """
                    SELECT 1
                    FROM dokument
                    WHERE bewerbungs_nr = %s
                      AND dokumenttyp = %s
                    """,
                    (bewerbungs_nr, dokumenttyp),
                )

                if cursor.fetchone() is not None:
                    raise ValueError(
                        f"Ein {dokumenttyp} ist für diese Bewerbung "
                        "bereits vorhanden."
                    )

                # Zufälliger Dateiname verhindert Pfadmanipulation
                # über vom Bewerber gelieferte Dateinamen.
                with zielpfad.open("xb") as ausgabe:
                    ausgabe.write(inhalt)

                cursor.execute(
                    """
                    INSERT INTO dokument
                        (bewerbungs_nr, dateiname, dokumenttyp, dateipfad)
                    VALUES (%s, %s, %s, %s)
                    RETURNING dokument_id
                    """,
                    (
                        bewerbungs_nr,
                        dateiname,
                        dokumenttyp,
                        str(zielpfad),
                    ),
                )

                dokument_id = cursor.fetchone()[0]

                if dokumenttyp == "Motivationsschreiben":
                    cursor.execute(
                        """
                        INSERT INTO motivationsschreiben (dokument_id)
                        VALUES (%s)
                        """,
                        (dokument_id,),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO leistungsnachweis (dokument_id)
                        VALUES (%s)
                        """,
                        (dokument_id,),
                    )

    except Exception:
        # Bei Datenbankfehlern keine verwaiste neue Datei zurücklassen.
        zielpfad.unlink(missing_ok=True)
        raise


# ---------------------------------------------------------------------
# SQL für Kommissionsmitglieder
# ---------------------------------------------------------------------

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
LEFT JOIN bewertungspunkt bp
    ON bp.bewertung_id = bw.bewertung_id
LEFT JOIN bewertungskriterium k
    ON k.kriterium_id = bp.kriterium_id
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
LEFT JOIN leistungsnachweis ln
    ON ln.dokument_id = d.dokument_id
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


# ---------------------------------------------------------------------
# Streamlit-Oberfläche
# ---------------------------------------------------------------------

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

        # Eine Person soll genau eine der beiden Rollen haben.
        if konto["ist_bewerber"] == konto["ist_kommission"]:
            st.error("Für dieses Konto ist keine eindeutige Rolle hinterlegt.")
            return

        st.session_state["angemeldet"] = {
            "personen_id": konto["personen_id"],
            "vorname": konto["vorname"],
            "nachname": konto["nachname"],
            "rolle": (
                "bewerber"
                if konto["ist_bewerber"]
                else "kommission"
            ),
        }

        st.rerun()

    except (psycopg.Error, RuntimeError):
        st.error("Anmeldung derzeit nicht möglich. Prüfe PostgreSQL und .env.")


def bewerber_dashboard(personen_id: int) -> None:
    st.header("Mein Bewerber-Dashboard")

    bereich = st.sidebar.radio(
        "Bereich",
        [
            "Entwurf & PDF-Upload",
            "Meine Bewerbungen",
            "Meine Dokumente",
            "Meine Benachrichtigungen",
            "Meine Entscheidung",
        ],
    )

    parameter = (personen_id,)

    if bereich == "Entwurf & PDF-Upload":
        st.subheader("Bewerbung vorbereiten")

        st.write("**1. Entwurf anlegen**")
        zeitraeume = abfragen(SQL_OFFENE_ZEITRAEUME)

        if zeitraeume:
            auswahl = st.selectbox(
                "Offener Bewerbungszeitraum",
                zeitraeume,
                format_func=lambda z: (
                    f"{z['bezeichnung']} "
                    f"({z['beginn']} bis {z['ende']})"
                ),
            )

            if st.button("Neuen Entwurf anlegen"):
                nummer = entwurf_anlegen(
                    personen_id,
                    auswahl["zeitraum_id"],
                )

                if nummer is None:
                    st.info(
                        "Für diesen Zeitraum besteht bereits eine "
                        "Bewerbung oder der Zeitraum ist nicht mehr offen."
                    )
                else:
                    st.success(f"Entwurf Nr. {nummer} wurde angelegt.")

        else:
            st.info("Derzeit gibt es keinen offenen Bewerbungszeitraum.")

        st.divider()
        st.write("**2. Pflichtdokumente als PDF hochladen**")

        entwuerfe = abfragen(SQL_MEINE_ENTWUERFE, parameter)

        if not entwuerfe:
            st.info("Du hast derzeit keinen bearbeitbaren Entwurf.")
            return

        entwurf = st.selectbox(
            "Entwurf für den Upload",
            entwuerfe,
            format_func=lambda b: (
                f"Nr. {b['bewerbungs_nr']} – {b['bezeichnung']}"
            ),
        )

        dokumenttyp = st.selectbox(
            "Art des Dokuments",
            ["Motivationsschreiben", "Leistungsnachweis"],
        )

        datei = st.file_uploader(
            "PDF auswählen (höchstens 10 MB)",
            type=["pdf"],
        )

        if st.button("PDF speichern"):
            try:
                pdf_speichern(
                    personen_id,
                    entwurf["bewerbungs_nr"],
                    dokumenttyp,
                    datei,
                )
                st.success("PDF gespeichert.")
                st.rerun()

            except ValueError as fehler:
                st.error(str(fehler))

            except psycopg.errors.UniqueViolation:
                st.error(
                    "Für diese Bewerbung gibt es bereits "
                    "ein Dokument dieses Typs."
                )

            except (psycopg.Error, OSError):
                st.error(
                    "Die PDF konnte nicht gespeichert werden. "
                    "Bitte Datenbank und Upload-Ordner prüfen."
                )

    elif bereich == "Meine Bewerbungen":
        st.subheader("Meine Bewerbungen")
        tabelle_anzeigen(
            abfragen(SQL_MEINE_BEWERBUNGEN, parameter),
            "Du hast noch keine Bewerbung.",
        )

    elif bereich == "Meine Dokumente":
        st.subheader("Meine Dokumente")
        st.caption(
            "Hier werden nur Dokumente deiner eigenen Bewerbungen angezeigt."
        )
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
            f"{b['vorname']} {b['nachname']} "
            f"({b['matrikel_nr']})"
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

            st.metric(
                "Score aus abgeschlossenen Bewertungen",
                f"{score:.2f}",
            )

    else:
        st.subheader("Dokumente")
        tabelle_anzeigen(
            abfragen(SQL_DOKUMENTE_KOMMISSION, (nummer,)),
            "Für diese Bewerbung sind keine Dokumente erfasst.",
        )


# Ohne Login keine Dashboard-Ansichten ausführen.
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