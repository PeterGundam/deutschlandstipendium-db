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
MAX_PDF_GROESSE = 10 * 1024 * 1024

load_dotenv(PROJEKTORDNER / ".env")

st.set_page_config(
    page_title="Deutschlandstipendium",
    page_icon="🎓",
    layout="wide",
)


# ============================================================
# Datenbank und Login
# ============================================================

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


def login_anzeigen() -> None:
    st.title("🎓 Deutschlandstipendium")
    st.subheader("Anmelden")

    with st.form("login_formular"):
        email = st.text_input("E-Mail-Adresse")
        passwort = st.text_input("Passwort", type="password")
        abgeschickt = st.form_submit_button("Anmelden", type="primary")

    if not abgeschickt:
        return

    try:
        konten = abfragen(SQL_LOGIN, (email.strip(),))
        konto = konten[0] if len(konten) == 1 else None

        if konto is None or not passwort_pruefen(
            passwort, konto["passwort_hash"]
        ):
            st.error("E-Mail-Adresse oder Passwort ist falsch.")
            return

        if konto["ist_bewerber"] == konto["ist_kommission"]:
            st.error("Für dieses Konto ist keine eindeutige Rolle hinterlegt.")
            return

        st.session_state["angemeldet"] = {
            "personen_id": konto["personen_id"],
            "vorname": konto["vorname"],
            "nachname": konto["nachname"],
            "rolle": (
                "bewerber" if konto["ist_bewerber"] else "kommission"
            ),
        }
        st.rerun()

    except (psycopg.Error, RuntimeError):
        st.error("Anmeldung derzeit nicht möglich. Prüfe PostgreSQL und .env.")


def tabelle_anzeigen(daten: list[dict], leertext: str) -> None:
    if daten:
        st.dataframe(daten, hide_index=True, use_container_width=True)
    else:
        st.info(leertext)


# ============================================================
# Bewerber: SQL und Schreibfunktionen
# ============================================================

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
SELECT d.dokument_id, b.bewerbungs_nr, d.dateiname, d.dokumenttyp
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
SELECT b.bewerbungs_nr, n.datum, n.typ, n.sendestatus
FROM benachrichtigung n
JOIN bewerbung b ON b.bewerbungs_nr = n.bewerbungs_nr
WHERE b.studierenden_id = %s
ORDER BY n.datum DESC
"""

SQL_OFFENE_ZEITRAEUME = """
SELECT bz.zeitraum_id, st.bezeichnung, bz.beginn, bz.ende
FROM bewerbungszeitraum bz
JOIN stipendium st ON st.stipendium_id = bz.stipendium_id
WHERE CURRENT_DATE BETWEEN bz.beginn AND bz.ende
ORDER BY bz.ende, bz.zeitraum_id
"""

SQL_MEINE_ENTWUERFE = """
SELECT b.bewerbungs_nr, st.bezeichnung
FROM bewerbung b
JOIN bewerbungszeitraum bz ON bz.zeitraum_id = b.zeitraum_id
JOIN stipendium st ON st.stipendium_id = bz.stipendium_id
WHERE b.studierenden_id = %s
  AND b.status = 'Entwurf'
ORDER BY b.bewerbungs_nr DESC
"""


def entwurf_anlegen(personen_id: int, zeitraum_id: int) -> int | None:
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
                      SELECT 1 FROM studierender s
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
    """Speichert eine PDF zu einem eigenen Bewerbungsentwurf."""
    if dokumenttyp not in ("Motivationsschreiben", "Leistungsnachweis"):
        raise ValueError("Unbekannter Dokumenttyp.")

    if datei is None:
        raise ValueError("Bitte zuerst eine PDF auswählen.")

    if not datei.name.lower().endswith(".pdf"):
        raise ValueError("Die Datei muss die Endung .pdf haben.")

    inhalt = datei.getvalue()
    if not inhalt.startswith(b"%PDF-"):
        raise ValueError("Die Datei ist keine erkennbare PDF.")

    if len(inhalt) > MAX_PDF_GROESSE:
        raise ValueError("Die PDF darf höchstens 10 MB groß sein.")

    dateiname = datei.name.replace("\\", "/").split("/")[-1][:255]

    UPLOAD_ORDNER.mkdir(mode=0o700, exist_ok=True)
    zielpfad = UPLOAD_ORDNER / f"{uuid.uuid4().hex}.pdf"

    try:
        with verbindung_oeffnen() as verbindung:
            with verbindung.cursor() as cursor:
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

                cursor.execute(
                    """
                    SELECT 1 FROM dokument
                    WHERE bewerbungs_nr = %s AND dokumenttyp = %s
                    """,
                    (bewerbungs_nr, dokumenttyp),
                )
                if cursor.fetchone() is not None:
                    raise ValueError(
                        f"Ein {dokumenttyp} ist bereits vorhanden."
                    )

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
        zielpfad.unlink(missing_ok=True)
        raise


def bewerber_dashboard(personen_id: int) -> None:
    st.title("Mein Bewerber-Dashboard")

    bereich = st.sidebar.radio(
        "Bereich",
        [
            "Meine Bewerbungen",
            "Bewerbung vorbereiten",
            "Dokumente hochladen",
            "Meine Dokumente",
            "Meine Benachrichtigungen",
            "Meine Entscheidung",
        ],
        key="bewerber_bereich",
    )

    parameter = (personen_id,)

    if bereich == "Meine Bewerbungen":
        st.subheader("Meine Bewerbungen")
        tabelle_anzeigen(
            abfragen(SQL_MEINE_BEWERBUNGEN, parameter),
            "Du hast noch keine Bewerbung.",
        )

    elif bereich == "Bewerbung vorbereiten":
        st.subheader("Neuen Entwurf anlegen")
        zeitraeume = abfragen(SQL_OFFENE_ZEITRAEUME)

        if not zeitraeume:
            st.info("Derzeit gibt es keinen offenen Bewerbungszeitraum.")
            return

        auswahl = st.selectbox(
            "Bewerbungszeitraum",
            zeitraeume,
            format_func=lambda z: (
                f"{z['bezeichnung']} "
                f"({z['beginn']} bis {z['ende']})"
            ),
        )

        if st.button("Entwurf anlegen"):
            nummer = entwurf_anlegen(
                personen_id, auswahl["zeitraum_id"]
            )
            if nummer is None:
                st.info(
                    "Für diesen Zeitraum besteht bereits eine Bewerbung "
                    "oder der Zeitraum ist nicht mehr offen."
                )
            else:
                st.success(f"Entwurf Nr. {nummer} wurde angelegt.")

    elif bereich == "Dokumente hochladen":
        st.subheader("PDF-Dokument hochladen")
        entwuerfe = abfragen(SQL_MEINE_ENTWUERFE, parameter)

        if not entwuerfe:
            st.info(
                "Du hast keinen bearbeitbaren Entwurf. "
                "Bereits eingereichte Bewerbungen sind nicht mehr "
                "für den Upload freigegeben."
            )
            return

        entwurf = st.selectbox(
            "Bewerbung",
            entwuerfe,
            format_func=lambda b: (
                f"Nr. {b['bewerbungs_nr']} – {b['bezeichnung']}"
            ),
        )
        dokumenttyp = st.selectbox(
            "Was für ein Dokument ist diese PDF?",
            ["Motivationsschreiben", "Leistungsnachweis"],
        )
        datei = st.file_uploader(
            "PDF auswählen (maximal 10 MB)",
            type=["pdf"],
        )

        if st.button("PDF speichern", type="primary"):
            try:
                pdf_speichern(
                    personen_id,
                    entwurf["bewerbungs_nr"],
                    dokumenttyp,
                    datei,
                )
                st.success("PDF gespeichert.")
            except ValueError as fehler:
                st.error(str(fehler))
            except psycopg.errors.UniqueViolation:
                st.error(
                    "Ein Dokument dieser Art ist bereits vorhanden."
                )
            except (psycopg.Error, OSError):
                st.error(
                    "Der Upload ist fehlgeschlagen. "
                    "Bitte Datenbank und Upload-Ordner prüfen."
                )

    elif bereich == "Meine Dokumente":
        st.subheader("Meine Dokumente")
        tabelle_anzeigen(
            abfragen(SQL_MEINE_DOKUMENTE, parameter),
            "Für deine Bewerbungen sind keine Dokumente erfasst.",
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


# ============================================================
# Kommission: echte Suche und Bewerbungsdetail
# ============================================================

SQL_KOMMISSION_SUCHE = """
WITH gegenstaende AS (
    SELECT bewerbungs_nr, 'Dokument'::text AS art, dokument_id AS id
    FROM dokument

    UNION ALL

    SELECT bewerbungs_nr, 'Engagement', engagement_id
    FROM engagement

    UNION ALL

    SELECT bewerbungs_nr, 'Lebensumstand', umstand_id
    FROM lebensumstand

    UNION ALL

    SELECT bewerbungs_nr, 'Auszeichnung', auszeichnung_id
    FROM auszeichnung
),
fortschritt AS (
    SELECT
        g.bewerbungs_nr,
        COUNT(*) AS anzahl_gegenstaende,
        COUNT(bw.bewertung_id) FILTER (
            WHERE bw.status = 'abgeschlossen'
        ) AS anzahl_bewertet
    FROM gegenstaende g
    LEFT JOIN bewertung bw
      ON bw.bewerbungs_nr = g.bewerbungs_nr
     AND (
         (g.art = 'Dokument' AND bw.dokument_id = g.id)
         OR (g.art = 'Engagement' AND bw.engagement_id = g.id)
         OR (g.art = 'Lebensumstand' AND bw.umstand_id = g.id)
         OR (g.art = 'Auszeichnung' AND bw.auszeichnung_id = g.id)
     )
    GROUP BY g.bewerbungs_nr
)
SELECT
    b.bewerbungs_nr,
    s.matrikel_nr,
    p.vorname,
    p.nachname,
    b.status AS bewerbungsstatus,
    COALESCE(f.anzahl_gegenstaende, 0) AS anzahl_gegenstaende,
    COALESCE(f.anzahl_bewertet, 0) AS anzahl_bewertet,
    COALESCE(a.foerderstatus, 'Noch offen') AS entscheidung,
    EXISTS (
        SELECT 1 FROM dokument d
        WHERE d.bewerbungs_nr = b.bewerbungs_nr
          AND d.dokumenttyp = 'Motivationsschreiben'
    ) AS hat_motivationsschreiben,
    EXISTS (
        SELECT 1 FROM dokument d
        WHERE d.bewerbungs_nr = b.bewerbungs_nr
          AND d.dokumenttyp = 'Leistungsnachweis'
    ) AS hat_leistungsnachweis
FROM bewerbung b
JOIN studierender s ON s.personen_id = b.studierenden_id
JOIN person p ON p.personen_id = s.personen_id
LEFT JOIN fortschritt f ON f.bewerbungs_nr = b.bewerbungs_nr
LEFT JOIN auswahlentscheidung a
    ON a.bewerbungs_nr = b.bewerbungs_nr
ORDER BY p.nachname, p.vorname, b.bewerbungs_nr
"""

SQL_KOMMISSION_GEGENSTAENDE = """
WITH gegenstaende AS (
    SELECT
        d.bewerbungs_nr,
        'Dokument'::text AS art,
        d.dokument_id AS gegenstand_id,
        d.dateiname::text AS titel,
        d.dokumenttyp::text AS inhalt,
        d.dokument_id,
        NULL::integer AS engagement_id,
        NULL::integer AS umstand_id,
        NULL::integer AS auszeichnung_id
    FROM dokument d

    UNION ALL

    SELECT
        e.bewerbungs_nr, 'Engagement', e.engagement_id,
        e.art::text, e.beschreibung::text,
        NULL, e.engagement_id, NULL, NULL
    FROM engagement e

    UNION ALL

    SELECT
        l.bewerbungs_nr, 'Lebensumstand', l.umstand_id,
        'Lebensumstand', l.beschreibung::text,
        NULL, NULL, l.umstand_id, NULL
    FROM lebensumstand l

    UNION ALL

    SELECT
        a.bewerbungs_nr, 'Auszeichnung', a.auszeichnung_id,
        a.titel::text, a.beschreibung::text,
        NULL, NULL, NULL, a.auszeichnung_id
    FROM auszeichnung a
)
SELECT
    g.art,
    g.gegenstand_id,
    g.titel,
    g.inhalt,
    bw.bewertung_id,
    bw.status AS bewertungsstatus,
    p.vorname || ' ' || p.nachname AS bewertet_von
FROM gegenstaende g
LEFT JOIN bewertung bw
  ON bw.bewerbungs_nr = g.bewerbungs_nr
 AND (
     (g.art = 'Dokument' AND bw.dokument_id = g.dokument_id)
     OR (g.art = 'Engagement' AND bw.engagement_id = g.engagement_id)
     OR (g.art = 'Lebensumstand' AND bw.umstand_id = g.umstand_id)
     OR (g.art = 'Auszeichnung' AND bw.auszeichnung_id = g.auszeichnung_id)
 )
LEFT JOIN person p ON p.personen_id = bw.mitglied_id
WHERE g.bewerbungs_nr = %s
ORDER BY g.art, g.titel, g.gegenstand_id
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

SQL_ENTSCHEIDUNGEN = """
SELECT
    a.entscheidungs_id,
    a.bewerbungs_nr,
    s.matrikel_nr,
    a.foerderstatus,
    a.entscheidungsdatum,
    a.begruendung,
    COUNT(eb.mitglied_id) AS anzahl_beteiligte
FROM auswahlentscheidung a
JOIN bewerbung b ON b.bewerbungs_nr = a.bewerbungs_nr
JOIN studierender s ON s.personen_id = b.studierenden_id
LEFT JOIN entscheidungsbeteiligung eb
    ON eb.entscheidungs_id = a.entscheidungs_id
GROUP BY a.entscheidungs_id, s.matrikel_nr
ORDER BY a.entscheidungsdatum DESC, a.entscheidungs_id
"""


def kommissions_detail_zurueck() -> None:
    st.session_state.pop("kom_detail_id", None)


def bewertungsstand(bewerbung: dict) -> str:
    gesamt = bewerbung["anzahl_gegenstaende"]
    fertig = bewerbung["anzahl_bewertet"]

    if gesamt == 0:
        return "Keine Gegenstände"
    if fertig == 0:
        return "Offen"
    if fertig == gesamt:
        return "Alle erfassten bewertet"
    return "Teilweise bewertet"


def fortschritt_anzeigen(bewerbung: dict) -> None:
    gesamt = bewerbung["anzahl_gegenstaende"]
    fertig = bewerbung["anzahl_bewertet"]

    if not gesamt:
        st.caption("Noch keine Gegenstände erfasst.")
    elif fertig == gesamt:
        st.markdown(
            """
            <div style="background:#26313d;border-radius:10px;
                        height:12px;overflow:hidden;">
              <div style="background:#22c55e;width:100%;
                          height:12px;"></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(f"✅ {fertig} von {gesamt} erfassten Gegenständen bewertet")
    else:
        st.progress(
            fertig / gesamt,
            text=f"{fertig} von {gesamt} erfassten Gegenständen bewertet",
        )


def kommissions_detail_anzeigen(bewerbung: dict) -> None:
    st.button(
        "← Zur Trefferliste",
        on_click=kommissions_detail_zurueck,
    )

    st.title(f"{bewerbung['vorname']} {bewerbung['nachname']}")
    st.caption(
        f"{bewerbung['matrikel_nr']} · "
        f"Bewerbung Nr. {bewerbung['bewerbungs_nr']}"
    )

    a, b, c = st.columns(3)
    a.metric("Bewerbungsstatus", bewerbung["bewerbungsstatus"])
    b.metric("Bewertungsstand", bewertungsstand(bewerbung))
    c.metric("Entscheidung", bewerbung["entscheidung"])

    fortschritt_anzeigen(bewerbung)

    if not (
        bewerbung["hat_motivationsschreiben"]
        and bewerbung["hat_leistungsnachweis"]
    ):
        st.warning(
            "Mindestens eines der vorgesehenen Pflichtdokumente fehlt. "
            "Die grüne Leiste bedeutet nur: Alle bislang erfassten "
            "Gegenstände sind bewertet – nicht, dass die Bewerbung "
            "fachlich vollständig ist."
        )

    gegenstaende = abfragen(
        SQL_KOMMISSION_GEGENSTAENDE,
        (bewerbung["bewerbungs_nr"],),
    )

    tab_gegenstaende, tab_punkte, tab_entscheidung = st.tabs(
        ["Unterlagen & Angaben", "Punkte", "Entscheidung"]
    )

    with tab_gegenstaende:
        if not gegenstaende:
            st.info("Noch keine Gegenstände erfasst.")
        else:
            index = st.selectbox(
                "Gegenstand auswählen",
                list(range(len(gegenstaende))),
                format_func=lambda i: (
                    "✓ " if gegenstaende[i]["bewertungsstatus"]
                    == "abgeschlossen" else "○ "
                )
                + f"{gegenstaende[i]['art']}: "
                  f"{gegenstaende[i]['titel']}",
                key=f"kom_gegenstand_{bewerbung['bewerbungs_nr']}",
            )
            gegenstand = gegenstaende[index]

            links, rechts = st.columns([1.2, 1], gap="large")

            with links:
                st.subheader("Unterlage / Angabe")
                st.write(
                    f"**{gegenstand['art']}:** "
                    f"{gegenstand['titel']}"
                )

                if gegenstand["art"] == "Dokument":
                    st.info(
                        "Der Dokumenteintrag ist sichtbar. "
                        "Eine Vorschau echter PDFs ergänzen wir später; "
                        "einige Demodateipfade sind nur Platzhalter."
                    )
                    st.write(
                        f"**Dokumenttyp:** {gegenstand['inhalt']}"
                    )
                else:
                    st.text_area(
                        "Erfasster Inhalt",
                        value=gegenstand["inhalt"] or "",
                        height=230,
                        disabled=True,
                        key=(
                            f"kom_inhalt_{bewerbung['bewerbungs_nr']}_"
                            f"{gegenstand['art']}_"
                            f"{gegenstand['gegenstand_id']}"
                        ),
                    )

            with rechts:
                st.subheader("Bearbeitungsstand")
                if gegenstand["bewertungsstatus"] == "abgeschlossen":
                    st.success("Bewertet")
                elif gegenstand["bewertung_id"] is not None:
                    st.warning("Bewertung als Entwurf vorhanden")
                else:
                    st.info("Noch nicht bewertet")

                if gegenstand["bewertet_von"]:
                    st.write(
                        f"**Bewertet von:** "
                        f"{gegenstand['bewertet_von']}"
                    )

                st.caption(
                    "Punkte erfassen und bearbeiten folgt im "
                    "nächsten Implementierungsschritt."
                )

            st.subheader("Alle Gegenstände dieser Bewerbung")
            tabelle_anzeigen(
                [
                    {
                        "Art": g["art"],
                        "Gegenstand": g["titel"],
                        "Bewertungsstand": (
                            "Bewertet"
                            if g["bewertungsstatus"] == "abgeschlossen"
                            else "Offen"
                        ),
                    }
                    for g in gegenstaende
                ],
                "Noch keine Gegenstände vorhanden.",
            )

    with tab_punkte:
        tabelle_anzeigen(
            abfragen(
                SQL_EINZELBEWERTUNGEN,
                (bewerbung["bewerbungs_nr"],),
            ),
            "Noch keine Punkte vorhanden.",
        )

    with tab_entscheidung:
        st.write(
            f"**Förderentscheidung:** {bewerbung['entscheidung']}"
        )
        st.caption(
            "Bewertung und Förderentscheidung sind getrennte Schritte. "
            "Diese Ansicht verändert noch keine Entscheidung."
        )


def kommissions_dashboard() -> None:
    st.sidebar.radio(
        "Bereich",
        [
            "Bewerbungen",
            "Bewertungsaufgaben",
            "Rangliste",
            "Auswahlentscheidungen",
        ],
        key="kommissions_bereich",
        on_change=kommissions_detail_zurueck,
    )

    bereich = st.session_state["kommissions_bereich"]

    if bereich == "Rangliste":
        st.title("Interne Rangliste")
        tabelle_anzeigen(
            abfragen(SQL_RANGLISTE),
            "Noch keine abgeschlossenen Bewerbungen in der Rangliste.",
        )
        return

    if bereich == "Auswahlentscheidungen":
        st.title("Auswahlentscheidungen")
        tabelle_anzeigen(
            abfragen(SQL_ENTSCHEIDUNGEN),
            "Noch keine Auswahlentscheidungen vorhanden.",
        )
        return

    bewerbungen = abfragen(SQL_KOMMISSION_SUCHE)

    detail_id = st.session_state.get("kom_detail_id")
    if detail_id is not None:
        bewerbung = next(
            (
                b for b in bewerbungen
                if b["bewerbungs_nr"] == detail_id
            ),
            None,
        )
        if bewerbung is None:
            kommissions_detail_zurueck()
            st.warning("Diese Bewerbung ist nicht mehr verfügbar.")
        else:
            kommissions_detail_anzeigen(bewerbung)
        return

    st.title(
        "Bewertungsaufgaben"
        if bereich == "Bewertungsaufgaben"
        else "Bewerbungen"
    )
    st.caption(
        "Suche, Filter, Fortschritt und Entscheidungen stammen "
        "aus PostgreSQL."
    )

    suchtext = st.text_input(
        "Nach Name oder Matrikelnummer suchen",
        key="kom_suchtext",
    ).strip().casefold()

    a, b, c, d = st.columns(4)

    with a:
        status_filter = st.selectbox(
            "Bewerbungsstatus",
            [
                "Alle",
                "Entwurf",
                "Eingereicht",
                "In_Pruefung",
                "Abgeschlossen",
            ],
            key="kom_status_filter",
        )

    with b:
        stand_filter = st.selectbox(
            "Bewertungsstand",
            [
                "Alle",
                "Keine Gegenstände",
                "Offen",
                "Teilweise bewertet",
                "Alle erfassten bewertet",
            ],
            key="kom_bewertungs_filter",
        )

    with c:
        entscheidung_filter = st.selectbox(
            "Entscheidung",
            [
                "Alle",
                "Noch offen",
                "Bewilligt",
                "Warteliste",
                "Abgelehnt",
            ],
            key="kom_entscheidungs_filter",
        )

    with d:
        sortierung = st.selectbox(
            "Sortieren",
            [
                "Name A–Z",
                "Name Z–A",
                "Matrikelnummer",
                "Bewerbungsstatus",
                "Bearbeitungsfortschritt",
            ],
            key="kom_sortierung",
        )

    treffer = []

    for bewerbung in bewerbungen:
        durchsuchbar = (
            f"{bewerbung['vorname']} "
            f"{bewerbung['nachname']} "
            f"{bewerbung['matrikel_nr']}"
        ).casefold()
        stand = bewertungsstand(bewerbung)

        if suchtext and suchtext not in durchsuchbar:
            continue
        if (
            status_filter != "Alle"
            and bewerbung["bewerbungsstatus"] != status_filter
        ):
            continue
        if stand_filter != "Alle" and stand != stand_filter:
            continue
        if (
            entscheidung_filter != "Alle"
            and bewerbung["entscheidung"] != entscheidung_filter
        ):
            continue

        # Arbeitsliste: nur noch nicht fertig bewertete Gegenstände
        # eingereichter bzw. bereits geprüfter Bewerbungen.
        if bereich == "Bewertungsaufgaben":
            if bewerbung["bewerbungsstatus"] not in (
                "Eingereicht",
                "In_Pruefung",
            ):
                continue
            if stand in ("Alle erfassten bewertet", "Keine Gegenstände"):
                continue
            if bewerbung["entscheidung"] != "Noch offen":
                continue

        treffer.append(bewerbung)

    if sortierung in ("Name A–Z", "Name Z–A"):
        treffer.sort(
            key=lambda x: (
                x["nachname"].casefold(),
                x["vorname"].casefold(),
            ),
            reverse=(sortierung == "Name Z–A"),
        )
    elif sortierung == "Matrikelnummer":
        treffer.sort(key=lambda x: x["matrikel_nr"])
    elif sortierung == "Bewerbungsstatus":
        treffer.sort(
            key=lambda x: (
                x["bewerbungsstatus"],
                x["nachname"].casefold(),
            )
        )
    else:
        treffer.sort(
            key=lambda x: (
                x["anzahl_bewertet"] / x["anzahl_gegenstaende"]
                if x["anzahl_gegenstaende"] else 0,
                x["nachname"].casefold(),
            )
        )

    st.write(f"**{len(treffer)} Bewerbungen gefunden**")

    if not treffer:
        st.info(
            "Keine Treffer. Fertig bewertete oder entschiedene "
            "Bewerbungen findest du unter „Bewerbungen“."
        )

    for bewerbung in treffer:
        with st.container(border=True):
            info, aktion = st.columns([4, 1])

            with info:
                st.subheader(
                    f"{bewerbung['vorname']} "
                    f"{bewerbung['nachname']} · "
                    f"{bewerbung['matrikel_nr']}"
                )
                st.write(
                    f"**Bewerbung:** {bewerbung['bewerbungsstatus']}"
                    f"**Bewertung:** {bewertungsstand(bewerbung)}"
                    f"**Entscheidung:** {bewerbung['entscheidung']}"
                )
                fortschritt_anzeigen(bewerbung)

            with aktion:
                if st.button(
                    "Öffnen →",
                    key=f"kom_oeffnen_{bewerbung['bewerbungs_nr']}",
                    use_container_width=True,
                ):
                    st.session_state["kom_detail_id"] = (
                        bewerbung["bewerbungs_nr"]
                    )
                    st.rerun()


# ============================================================
# App-Start
# ============================================================

if "angemeldet" not in st.session_state:
    login_anzeigen()
    st.stop()

benutzer = st.session_state["angemeldet"]

st.sidebar.write(
    f"Angemeldet: {benutzer['vorname']} {benutzer['nachname']}"
)

if st.sidebar.button("Abmelden"):
    st.session_state.clear()
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
    st.caption("Prüfe PostgreSQL und die lokale .env-Datei.")