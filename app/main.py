from pathlib import Path
import base64
import hashlib
import hmac
import os
import secrets
import uuid

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
import streamlit as st


ROOT = Path(__file__).resolve().parent.parent
UPLOAD_ROOT = ROOT / "private_uploads"
MAX_PDF_BYTES = 10 * 1024 * 1024

load_dotenv(ROOT / ".env")

st.set_page_config(
    page_title="Deutschlandstipendium",
    page_icon="🎓",
    layout="wide",
)


# ============================================================
# Datenbank und Passwörter
# ============================================================

def db():
    password = os.getenv("DB_PASSWORD")
    if not password:
        raise RuntimeError("DB_PASSWORD fehlt in der lokalen .env-Datei.")

    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "stipendium_db"),
        user=os.getenv("DB_USER", "stipendium_user"),
        password=password,
        connect_timeout=5,
    )


def query(sql, params=()):
    with db() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def password_hash(password):
    salt = secrets.token_bytes(16)
    n, r, p = 2**14, 8, 1
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=n,
        r=r,
        p=p,
        dklen=64,
        maxmem=64 * 1024 * 1024,
    )
    return (
        f"scrypt${n}${r}${p}$"
        f"{base64.b64encode(salt).decode('ascii')}$"
        f"{base64.b64encode(digest).decode('ascii')}"
    )


def password_ok(password, stored):
    try:
        method, n, r, p, salt64, digest64 = stored.split("$")
        if method != "scrypt":
            return False

        expected = base64.b64decode(digest64, validate=True)
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=base64.b64decode(salt64, validate=True),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
            maxmem=64 * 1024 * 1024,
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, OverflowError):
        return False


SQL_LOGIN = """
SELECT l.personen_id, l.passwort_hash, p.vorname, p.nachname,
       (s.personen_id IS NOT NULL) AS ist_bewerber,
       (k.personen_id IS NOT NULL) AS ist_kommission
FROM login_konto l
JOIN person p ON p.personen_id = l.personen_id
LEFT JOIN studierender s ON s.personen_id = l.personen_id
LEFT JOIN kommissionsmitglied k ON k.personen_id = l.personen_id
WHERE lower(l.email) = lower(%s)
  AND l.aktiv = TRUE
"""


def rolle_aktuell(personen_id):
    """Rolle und Kontostatus bei jedem App-Durchlauf erneut prüfen."""
    rows = query(
        """
        SELECT l.aktiv,
               (s.personen_id IS NOT NULL) AS bewerber,
               (k.personen_id IS NOT NULL) AS kommission
        FROM login_konto l
        LEFT JOIN studierender s ON s.personen_id = l.personen_id
        LEFT JOIN kommissionsmitglied k ON k.personen_id = l.personen_id
        WHERE l.personen_id = %s
        """,
        (personen_id,),
    )
    if len(rows) != 1 or not rows[0]["aktiv"]:
        return None
    if rows[0]["bewerber"] == rows[0]["kommission"]:
        return None
    return "bewerber" if rows[0]["bewerber"] else "kommission"


def status_tabelle(rows, leertext):
    if rows:
        st.dataframe(rows, hide_index=True, width="stretch")
    else:
        st.info(leertext)


# ============================================================
# Einstieg: Login und Registrierung
# ============================================================

def anmelden():
    st.title("🎓 Deutschlandstipendium")
    st.subheader("Anmelden")

    with st.form("login"):
        email = st.text_input("E-Mail-Adresse")
        password = st.text_input("Passwort", type="password")
        submitted = st.form_submit_button("Anmelden", type="primary")

    if not submitted:
        return

    accounts = query(SQL_LOGIN, (email.strip().lower(),))
    account = accounts[0] if len(accounts) == 1 else None

    if not account or not password_ok(password, account["passwort_hash"]):
        st.error("E-Mail-Adresse oder Passwort ist falsch.")
        return

    if account["ist_bewerber"] == account["ist_kommission"]:
        st.error("Dieses Konto hat keine eindeutige Rolle.")
        return

    st.session_state["user"] = {
        "id": account["personen_id"],
        "name": f"{account['vorname']} {account['nachname']}",
        "role": (
            "bewerber" if account["ist_bewerber"]
            else "kommission"
        ),
    }
    st.rerun()


def registrieren():
    st.title("Bewerberkonto erstellen")
    st.caption(
        "Nur Bewerber können sich selbst registrieren. "
        "Kommissionskonten werden separat verwaltet."
    )

    programmes = query(
        """
        SELECT studiengang_id, name
        FROM studiengang
        ORDER BY name, studiengang_id
        """
    )
    if not programmes:
        st.error("Es ist noch kein Studiengang eingetragen.")
        return

    with st.form("registration"):
        first = st.text_input("Vorname *")
        last = st.text_input("Nachname *")
        email = st.text_input("E-Mail-Adresse *")
        matriculation = st.text_input("Matrikelnummer *")
        semester = st.number_input(
            "Fachsemester *", min_value=1, max_value=100
        )
        programme = st.selectbox(
            "Studiengang *",
            programmes,
            format_func=lambda x: (
                f"{x['name']} (ID {x['studiengang_id']})"
            ),
        )
        password = st.text_input(
            "Passwort (mindestens 12 Zeichen) *",
            type="password",
        )
        confirmation = st.text_input(
            "Passwort wiederholen *",
            type="password",
        )
        submitted = st.form_submit_button(
            "Konto erstellen", type="primary"
        )

    if not submitted:
        return

    first, last = first.strip(), last.strip()
    email = email.strip().lower()
    matriculation = matriculation.strip()

    if not all((first, last, email, matriculation)):
        st.warning("Bitte alle Pflichtfelder ausfüllen.")
        return
    if (
        len(first) > 100 or len(last) > 100
        or len(email) > 255 or len(matriculation) > 30
        or "@" not in email
    ):
        st.warning("Bitte Namen, E-Mail und Matrikelnummer prüfen.")
        return
    if len(password) < 12 or password != confirmation:
        st.warning(
            "Das Passwort muss mindestens 12 Zeichen haben "
            "und mit der Wiederholung übereinstimmen."
        )
        return

    try:
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 1
                    FROM studierender
                    WHERE matrikel_nr = %s OR lower(email) = %s
                    """,
                    (matriculation, email),
                )
                if cur.fetchone():
                    raise ValueError(
                        "E-Mail oder Matrikelnummer ist bereits vergeben."
                    )

                cur.execute(
                    """
                    SELECT 1 FROM login_konto
                    WHERE lower(email) = %s
                    """,
                    (email,),
                )
                if cur.fetchone():
                    raise ValueError(
                        "E-Mail oder Matrikelnummer ist bereits vergeben."
                    )

                cur.execute(
                    """
                    INSERT INTO person (vorname, nachname)
                    VALUES (%s, %s) RETURNING personen_id
                    """,
                    (first, last),
                )
                person_id = cur.fetchone()[0]

                cur.execute(
                    """
                    INSERT INTO studierender
                        (personen_id, matrikel_nr, email,
                         fachsemester, studiengang_id)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        person_id, matriculation, email,
                        int(semester), programme["studiengang_id"],
                    ),
                )
                cur.execute(
                    """
                    INSERT INTO hochschulaccount
                        (benutzername, studierenden_id)
                    VALUES (%s, %s)
                    """,
                    (f"bewerber-{person_id}", person_id),
                )
                cur.execute(
                    """
                    INSERT INTO login_konto
                        (personen_id, email, passwort_hash)
                    VALUES (%s, %s, %s)
                    """,
                    (person_id, email, password_hash(password)),
                )

        st.success(
            "Konto erstellt. Wähle „Anmelden“ und melde dich an."
        )
    except ValueError as exc:
        st.error(str(exc))
    except psycopg.errors.UniqueViolation:
        st.error("E-Mail oder Matrikelnummer ist bereits vergeben.")


# ============================================================
# Bewerber: Daten und Schreiboperationen
# ============================================================

SQL_MY_APPLICATIONS = """
SELECT b.bewerbungs_nr, b.zeitraum_id,
       st.bezeichnung AS stipendium, bz.beginn, bz.ende,
       b.status, b.eingangsdatum
FROM bewerbung b
JOIN bewerbungszeitraum bz ON bz.zeitraum_id = b.zeitraum_id
JOIN stipendium st ON st.stipendium_id = bz.stipendium_id
WHERE b.studierenden_id = %s
ORDER BY b.bewerbungs_nr DESC
"""

SQL_MY_DOCUMENTS = """
SELECT d.dokument_id, d.bewerbungs_nr, d.dateiname,
       d.dokumenttyp
FROM dokument d
JOIN bewerbung b ON b.bewerbungs_nr = d.bewerbungs_nr
WHERE b.studierenden_id = %s
ORDER BY d.bewerbungs_nr, d.dokument_id
"""

SQL_OPEN_PERIODS = """
SELECT bz.zeitraum_id, bz.beginn, bz.ende,
       st.bezeichnung
FROM bewerbungszeitraum bz
JOIN stipendium st ON st.stipendium_id = bz.stipendium_id
WHERE CURRENT_DATE BETWEEN bz.beginn AND bz.ende
ORDER BY bz.ende, bz.zeitraum_id
"""


def my_application_selector(user_id, only_drafts=False, key="my_app"):
    applications = query(SQL_MY_APPLICATIONS, (user_id,))
    if only_drafts:
        applications = [
            a for a in applications if a["status"] == "Entwurf"
        ]

    if not applications:
        st.info(
            "Kein bearbeitbarer Entwurf vorhanden."
            if only_drafts else "Du hast noch keine Bewerbung."
        )
        return None

    return st.selectbox(
        "Bewerbung auswählen",
        applications,
        format_func=lambda a: (
            f"Nr. {a['bewerbungs_nr']} · {a['stipendium']} "
            f"· {a['status']}"
        ),
        key=key,
    )


def create_draft(user_id, period_id):
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO bewerbung (studierenden_id, zeitraum_id)
                SELECT %s, zeitraum_id
                FROM bewerbungszeitraum
                WHERE zeitraum_id = %s
                  AND CURRENT_DATE BETWEEN beginn AND ende
                  AND EXISTS (
                      SELECT 1 FROM studierender
                      WHERE personen_id = %s
                  )
                ON CONFLICT (studierenden_id, zeitraum_id) DO NOTHING
                RETURNING bewerbungs_nr
                """,
                (user_id, period_id, user_id),
            )
            row = cur.fetchone()
            return row[0] if row else None


def add_detail(user_id, application_id, kind, fields):
    allowed = {
        "Engagement": (
            "INSERT INTO engagement "
            "(bewerbungs_nr, art, beschreibung) VALUES (%s, %s, %s)"
        ),
        "Lebensumstand": (
            "INSERT INTO lebensumstand "
            "(bewerbungs_nr, beschreibung) VALUES (%s, %s)"
        ),
        "Auszeichnung": (
            "INSERT INTO auszeichnung "
            "(bewerbungs_nr, titel, beschreibung) "
            "VALUES (%s, %s, %s)"
        ),
    }
    if kind not in allowed:
        raise ValueError("Unbekannte Art von Angabe.")

    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1 FROM bewerbung
                WHERE bewerbungs_nr = %s
                  AND studierenden_id = %s
                  AND status = 'Entwurf'
                FOR UPDATE
                """,
                (application_id, user_id),
            )
            if not cur.fetchone():
                raise ValueError(
                    "Nur eigene Entwürfe können ergänzt werden."
                )

            cur.execute(allowed[kind], (application_id, *fields))


def my_details(user_id, application_id):
    return query(
        """
        SELECT 'Engagement' AS art,
               e.art AS titel, e.beschreibung
        FROM engagement e
        JOIN bewerbung b
          ON b.bewerbungs_nr = e.bewerbungs_nr
        WHERE b.studierenden_id = %s
          AND b.bewerbungs_nr = %s
        UNION ALL
        SELECT 'Lebensumstand', 'Besondere Umstände', l.beschreibung
        FROM lebensumstand l
        JOIN bewerbung b ON b.bewerbungs_nr = l.bewerbungs_nr
        WHERE b.studierenden_id = %s
          AND b.bewerbungs_nr = %s
        UNION ALL
        SELECT 'Auszeichnung', a.titel, a.beschreibung
        FROM auszeichnung a
        JOIN bewerbung b ON b.bewerbungs_nr = a.bewerbungs_nr
        WHERE b.studierenden_id = %s
          AND b.bewerbungs_nr = %s
        ORDER BY art, titel
        """,
        (
            user_id, application_id,
            user_id, application_id,
            user_id, application_id,
        ),
    )


def upload_pdf(user_id, application_id, kind, uploaded):
    allowed = (
        "Motivationsschreiben",
        "Leistungsnachweis",
        "Sonstiges Dokument",
    )
    if kind not in allowed:
        raise ValueError("Unbekannte Dokumentart.")
    if uploaded is None:
        raise ValueError("Bitte eine PDF auswählen.")

    original_name = uploaded.name.replace("\\", "/").split("/")[-1]
    content = uploaded.getvalue()

    if not original_name.lower().endswith(".pdf"):
        raise ValueError("Die Datei benötigt die Endung .pdf.")
    if (
        not content.startswith(b"%PDF-")
        or len(content) == 0
        or len(content) > MAX_PDF_BYTES
    ):
        raise ValueError(
            "Bitte eine erkennbare PDF mit höchstens 10 MB auswählen."
        )

    UPLOAD_ROOT.mkdir(mode=0o700, exist_ok=True)
    stored = UPLOAD_ROOT / f"{uuid.uuid4().hex}.pdf"

    try:
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 1
                    FROM bewerbung
                    WHERE bewerbungs_nr = %s
                      AND studierenden_id = %s
                      AND status = 'Entwurf'
                    FOR UPDATE
                    """,
                    (application_id, user_id),
                )
                if not cur.fetchone():
                    raise ValueError(
                        "Uploads sind nur für eigene Entwürfe möglich."
                    )

                if kind != "Sonstiges Dokument":
                    cur.execute(
                        """
                        SELECT 1 FROM dokument
                        WHERE bewerbungs_nr = %s
                          AND dokumenttyp = %s
                        """,
                        (application_id, kind),
                    )
                    if cur.fetchone():
                        raise ValueError(
                            f"Ein {kind} ist bereits vorhanden."
                        )

                with stored.open("xb") as output:
                    output.write(content)

                cur.execute(
                    """
                    INSERT INTO dokument
                        (bewerbungs_nr, dateiname,
                         dokumenttyp, dateipfad)
                    VALUES (%s, %s, %s, %s)
                    RETURNING dokument_id
                    """,
                    (
                        application_id,
                        original_name[:255],
                        kind,
                        str(stored),
                    ),
                )
                document_id = cur.fetchone()[0]

                if kind == "Motivationsschreiben":
                    cur.execute(
                        """
                        INSERT INTO motivationsschreiben (dokument_id)
                        VALUES (%s)
                        """,
                        (document_id,),
                    )
                elif kind == "Leistungsnachweis":
                    cur.execute(
                        """
                        INSERT INTO leistungsnachweis (dokument_id)
                        VALUES (%s)
                        """,
                        (document_id,),
                    )

    except Exception:
        stored.unlink(missing_ok=True)
        raise


def required_documents(cur, application_id):
    """Pflichtunterlagen nur mit passendem Dokument-Untertyp zählen."""
    cur.execute(
        """
        SELECT
          EXISTS (
            SELECT 1 FROM dokument d
            JOIN motivationsschreiben m
              ON m.dokument_id = d.dokument_id
            WHERE d.bewerbungs_nr = %s
              AND d.dokumenttyp = 'Motivationsschreiben'
          ),
          EXISTS (
            SELECT 1 FROM dokument d
            JOIN leistungsnachweis l
              ON l.dokument_id = d.dokument_id
            WHERE d.bewerbungs_nr = %s
              AND d.dokumenttyp = 'Leistungsnachweis'
          )
        """,
        (application_id, application_id),
    )
    return cur.fetchone()


def submit_application(user_id, application_id):
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT b.bewerbungs_nr, bz.beginn, bz.ende
                FROM bewerbung b
                JOIN bewerbungszeitraum bz
                  ON bz.zeitraum_id = b.zeitraum_id
                WHERE b.bewerbungs_nr = %s
                  AND b.studierenden_id = %s
                  AND b.status = 'Entwurf'
                FOR UPDATE OF b
                """,
                (application_id, user_id),
            )
            application = cur.fetchone()
            if not application:
                raise ValueError(
                    "Nur ein eigener Entwurf kann eingereicht werden."
                )

            cur.execute(
                "SELECT CURRENT_DATE BETWEEN %s AND %s",
                (application[1], application[2]),
            )
            if not cur.fetchone()[0]:
                raise ValueError(
                    "Der Bewerbungszeitraum ist nicht mehr offen."
                )

            motivation, performance = required_documents(
                cur, application_id
            )
            if not (motivation and performance):
                raise ValueError(
                    "Motivationsschreiben und Leistungsnachweis fehlen."
                )

            cur.execute(
                """
                UPDATE bewerbung
                SET status = 'Eingereicht',
                    eingangsdatum = CURRENT_DATE
                WHERE bewerbungs_nr = %s
                """,
                (application_id,),
            )
            cur.execute(
                """
                INSERT INTO benachrichtigung
                    (bewerbungs_nr, typ, sendestatus)
                VALUES (%s, 'Eingangsbestätigung', 'Ausstehend')
                """,
                (application_id,),
            )


def own_pdf(user_id, document_id):
    rows = query(
        """
        SELECT d.dateiname, d.dateipfad
        FROM dokument d
        JOIN bewerbung b ON b.bewerbungs_nr = d.bewerbungs_nr
        WHERE d.dokument_id = %s
          AND b.studierenden_id = %s
        """,
        (document_id, user_id),
    )
    if not rows:
        return None
    return read_private_pdf(rows[0]["dateipfad"])


def read_private_pdf(stored_path):
    """Nur von dieser App angelegte Dateien im privaten Ordner lesen."""
    path = Path(stored_path).resolve()
    if not path.is_relative_to(UPLOAD_ROOT.resolve()):
        return None
    if not path.is_file() or path.stat().st_size > MAX_PDF_BYTES:
        return None
    return path.read_bytes()


def applicant_dashboard(user_id):
    st.title("Meine Bewerbung")
    menu = st.sidebar.radio(
        "Bewerberbereich",
        [
            "Übersicht",
            "Bewerbung anlegen",
            "Meine Angaben",
            "Dokumente hochladen",
            "Prüfen & einreichen",
            "Nachrichten & Entscheidung",
        ],
        key="applicant_menu",
    )

    if menu == "Übersicht":
        st.subheader("Meine Bewerbungen")
        status_tabelle(
            query(SQL_MY_APPLICATIONS, (user_id,)),
            "Du hast noch keine Bewerbung.",
        )

        st.subheader("Meine Dokumente")
        documents = query(SQL_MY_DOCUMENTS, (user_id,))
        status_tabelle(
            documents,
            "Noch keine Dokumente hochgeladen.",
        )

        for doc in documents:
            data = own_pdf(user_id, doc["dokument_id"])
            if data is not None:
                st.download_button(
                    f"{doc['dokumenttyp']}: {doc['dateiname']} herunterladen",
                    data=data,
                    file_name=doc["dateiname"],
                    mime="application/pdf",
                    key=f"own_download_{doc['dokument_id']}",
                )

    elif menu == "Bewerbung anlegen":
        st.subheader("Bewerbungsentwurf anlegen")
        periods = query(SQL_OPEN_PERIODS)
        if not periods:
            st.info("Aktuell ist kein Bewerbungszeitraum geöffnet.")
            return

        period = st.selectbox(
            "Offener Zeitraum",
            periods,
            format_func=lambda x: (
                f"{x['bezeichnung']} "
                f"({x['beginn']} bis {x['ende']})"
            ),
        )
        if st.button("Entwurf anlegen", type="primary"):
            number = create_draft(user_id, period["zeitraum_id"])
            if number is None:
                st.info(
                    "Für diesen Zeitraum besteht bereits eine Bewerbung."
                )
            else:
                st.success(f"Entwurf Nr. {number} wurde angelegt.")

    elif menu == "Meine Angaben":
        st.subheader("Engagement, Lebensumstände und Auszeichnungen")
        application = my_application_selector(
            user_id, only_drafts=True, key="details_app"
        )
        if application is None:
            return

        kind = st.selectbox(
            "Welche Angabe möchtest du ergänzen?",
            ["Engagement", "Lebensumstand", "Auszeichnung"],
        )

        with st.form("detail_form"):
            title = ""
            if kind == "Engagement":
                title = st.text_input("Art des Engagements *")
            elif kind == "Auszeichnung":
                title = st.text_input("Titel der Auszeichnung *")

            description = st.text_area("Beschreibung *")
            save = st.form_submit_button(
                "Angabe speichern", type="primary"
            )

        if save:
            if not description.strip() or (
                kind != "Lebensumstand" and not title.strip()
            ):
                st.warning("Bitte die erforderlichen Felder ausfüllen.")
            else:
                fields = (
                    (description.strip(),)
                    if kind == "Lebensumstand"
                    else (title.strip()[:200], description.strip())
                )
                add_detail(
                    user_id,
                    application["bewerbungs_nr"],
                    kind,
                    fields,
                )
                st.success("Angabe gespeichert.")

        st.subheader("Bisherige Angaben")
        status_tabelle(
            my_details(
                user_id, application["bewerbungs_nr"]
            ),
            "Noch keine Angaben erfasst.",
        )
        st.caption(
            "In dieser Version bleiben diese Angaben nach dem "
            "Einreichen unverändert."
        )

    elif menu == "Dokumente hochladen":
        st.subheader("PDF-Dokument hochladen")
        application = my_application_selector(
            user_id, only_drafts=True, key="upload_app"
        )
        if application is None:
            return

        st.caption(
            "Wähle für jede PDF die Dokumentart. "
            "Motivationsschreiben und Leistungsnachweis "
            "sind für das Einreichen erforderlich."
        )
        kind = st.selectbox(
            "Dokumentart",
            [
                "Motivationsschreiben",
                "Leistungsnachweis",
                "Sonstiges Dokument",
            ],
        )
        uploaded = st.file_uploader(
            "PDF auswählen (maximal 10 MB)",
            type=["pdf"],
            max_upload_size=10,
        )

        if st.button("PDF speichern", type="primary"):
            try:
                upload_pdf(
                    user_id,
                    application["bewerbungs_nr"],
                    kind,
                    uploaded,
                )
                st.success("PDF gespeichert.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
            except psycopg.errors.UniqueViolation:
                st.error(
                    "Diese Pflichtdokumentart ist bereits vorhanden."
                )
            except (psycopg.Error, OSError):
                st.error(
                    "Die PDF konnte nicht gespeichert werden."
                )

        st.subheader("Dokumente dieser Bewerbung")
        status_tabelle(
            [
                d for d in query(SQL_MY_DOCUMENTS, (user_id,))
                if d["bewerbungs_nr"]
                == application["bewerbungs_nr"]
            ],
            "Noch keine Dokumente vorhanden.",
        )

    elif menu == "Prüfen & einreichen":
        st.subheader("Bewerbung prüfen und einreichen")
        application = my_application_selector(
            user_id, only_drafts=True, key="submit_app"
        )
        if application is None:
            return

        with db() as conn:
            with conn.cursor() as cur:
                motivation, performance = required_documents(
                    cur, application["bewerbungs_nr"]
                )

        st.write(
            f"{'✅' if motivation else '⬜'} Motivationsschreiben"
        )
        st.write(
            f"{'✅' if performance else '⬜'} Leistungsnachweis"
        )
        st.caption(
            "Engagement, Lebensumstände und Auszeichnungen "
            "sind in dieser Projektversion optional."
        )

        if not (motivation and performance):
            st.warning(
                "Die Pflichtdokumente müssen vor dem Einreichen "
                "hochgeladen werden."
            )

        confirmed = st.checkbox(
            "Ich habe meine Angaben geprüft und möchte "
            "die Bewerbung verbindlich einreichen."
        )
        if st.button(
            "Bewerbung einreichen",
            type="primary",
            disabled=not (
                motivation and performance and confirmed
            ),
        ):
            try:
                submit_application(
                    user_id, application["bewerbungs_nr"]
                )
                st.success("Bewerbung eingereicht.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

    else:
        st.subheader("Meine Nachrichten")
        status_tabelle(
            query(
                """
                SELECT n.datum, n.typ, n.sendestatus,
                       b.bewerbungs_nr
                FROM benachrichtigung n
                JOIN bewerbung b
                  ON b.bewerbungs_nr = n.bewerbungs_nr
                WHERE b.studierenden_id = %s
                ORDER BY n.datum DESC
                """,
                (user_id,),
            ),
            "Noch keine Nachrichten vorhanden.",
        )
        st.caption(
            "„Ausstehend“ bedeutet: In der Datenbank vorgemerkt; "
            "es wurde noch keine E-Mail versendet."
        )

        st.subheader("Meine Entscheidungen")
        status_tabelle(
            query(
                """
                SELECT a.bewerbungs_nr, a.foerderstatus,
                       a.entscheidungsdatum, a.begruendung
                FROM auswahlentscheidung a
                JOIN bewerbung b
                  ON b.bewerbungs_nr = a.bewerbungs_nr
                WHERE b.studierenden_id = %s
                ORDER BY a.entscheidungsdatum DESC
                """,
                (user_id,),
            ),
            "Für dich liegt noch keine Entscheidung vor.",
        )


# ============================================================
# Kommission: Suche, Gegenstände und Bearbeitungsstand
# ============================================================

SQL_COMMISSION_APPLICATIONS = """
WITH items AS (
    SELECT bewerbungs_nr, 'Dokument'::text AS art,
           dokument_id AS item_id FROM dokument
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
counts AS (
    SELECT i.bewerbungs_nr,
           COUNT(*) AS total,
           COUNT(bw.bewertung_id) FILTER (
               WHERE bw.status = 'abgeschlossen'
                 AND EXISTS (
                     SELECT 1 FROM bewertungspunkt bp
                     WHERE bp.bewertung_id = bw.bewertung_id
                 )
           ) AS done
    FROM items i
    LEFT JOIN bewertung bw
      ON bw.bewerbungs_nr = i.bewerbungs_nr
     AND (
         (i.art = 'Dokument' AND bw.dokument_id = i.item_id)
         OR (i.art = 'Engagement' AND bw.engagement_id = i.item_id)
         OR (i.art = 'Lebensumstand' AND bw.umstand_id = i.item_id)
         OR (i.art = 'Auszeichnung' AND bw.auszeichnung_id = i.item_id)
     )
    GROUP BY i.bewerbungs_nr
)
SELECT b.bewerbungs_nr, b.zeitraum_id, b.status,
       s.matrikel_nr, p.vorname, p.nachname,
       COALESCE(c.total, 0) AS total,
       COALESCE(c.done, 0) AS done,
       COALESCE(a.foerderstatus, 'Noch offen') AS entscheidung
FROM bewerbung b
JOIN studierender s ON s.personen_id = b.studierenden_id
JOIN person p ON p.personen_id = s.personen_id
LEFT JOIN counts c ON c.bewerbungs_nr = b.bewerbungs_nr
LEFT JOIN auswahlentscheidung a
  ON a.bewerbungs_nr = b.bewerbungs_nr
WHERE b.status <> 'Entwurf'
ORDER BY p.nachname, p.vorname, b.bewerbungs_nr
"""

SQL_COMMISSION_ITEMS = """
WITH items AS (
    SELECT d.bewerbungs_nr, 'Dokument'::text AS art,
           d.dokument_id AS item_id, d.dateiname::text AS titel,
           d.dokumenttyp::text AS dokumenttyp,
           NULL::text AS beschreibung, d.dateipfad::text AS dateipfad
    FROM dokument d
    UNION ALL
    SELECT e.bewerbungs_nr, 'Engagement', e.engagement_id,
           e.art::text, NULL, e.beschreibung::text, NULL
    FROM engagement e
    UNION ALL
    SELECT l.bewerbungs_nr, 'Lebensumstand', l.umstand_id,
           'Besondere Umstände', NULL, l.beschreibung::text, NULL
    FROM lebensumstand l
    UNION ALL
    SELECT a.bewerbungs_nr, 'Auszeichnung', a.auszeichnung_id,
           a.titel::text, NULL, a.beschreibung::text, NULL
    FROM auszeichnung a
)
SELECT i.*, bw.bewertung_id, bw.mitglied_id,
       bw.status AS bewertungsstatus, bw.kommentar,
       p.vorname || ' ' || p.nachname AS bewertet_von,
       EXISTS (
           SELECT 1 FROM bewertungspunkt bp
           WHERE bp.bewertung_id = bw.bewertung_id
       ) AS hat_punkte
FROM items i
LEFT JOIN bewertung bw
  ON bw.bewerbungs_nr = i.bewerbungs_nr
 AND (
     (i.art = 'Dokument' AND bw.dokument_id = i.item_id)
     OR (i.art = 'Engagement' AND bw.engagement_id = i.item_id)
     OR (i.art = 'Lebensumstand' AND bw.umstand_id = i.item_id)
     OR (i.art = 'Auszeichnung' AND bw.auszeichnung_id = i.item_id)
 )
LEFT JOIN person p ON p.personen_id = bw.mitglied_id
WHERE i.bewerbungs_nr = %s
ORDER BY i.art, i.dokumenttyp NULLS LAST, i.titel, i.item_id
"""

SQL_PERIOD_CRITERIA = """
SELECT zk.kriterium_id, k.name, k.max_punkte, zk.gewichtung
FROM zeitraum_kriterium zk
JOIN bewertungskriterium k
  ON k.kriterium_id = zk.kriterium_id
WHERE zk.zeitraum_id = %s
ORDER BY k.name, k.kriterium_id
"""


def item_label(item):
    if item["art"] == "Dokument":
        return (
            f"{item['dokumenttyp']} · {item['titel']} "
            f"(Dokument-ID {item['item_id']})"
        )
    return (
        f"{item['art']} · {item['titel']} "
        f"(ID {item['item_id']})"
    )


def item_done(item):
    return (
        item["bewertungsstatus"] == "abgeschlossen"
        and item["hat_punkte"]
    )


def review_state(application):
    if application["total"] == 0:
        return "Keine Gegenstände"
    if application["done"] == application["total"]:
        return "Alle erfassten bewertet"
    if application["done"] == 0:
        return "Offen"
    return "Teilweise bewertet"


def show_progress(application):
    total = application["total"]
    done = application["done"]

    if total == 0:
        st.caption("Noch keine Gegenstände erfasst.")
    elif done == total:
        st.markdown(
            """
            <div style="background:#26313d;border-radius:9px;
                        height:13px;overflow:hidden;">
              <div style="background:#22c55e;width:100%;
                          height:13px;"></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(
            f"✅ {done} von {total} erfassten Gegenständen bewertet"
        )
    else:
        st.progress(
            done / total,
            text=f"{done} von {total} erfassten Gegenständen bewertet",
        )


def review_item(member_id, application_id, item, criterion_id,
                points, comment):
    columns = {
        "Dokument": "dokument_id",
        "Engagement": "engagement_id",
        "Lebensumstand": "umstand_id",
        "Auszeichnung": "auszeichnung_id",
    }
    source_tables = {
        "Dokument": ("dokument", "dokument_id"),
        "Engagement": ("engagement", "engagement_id"),
        "Lebensumstand": ("lebensumstand", "umstand_id"),
        "Auszeichnung": ("auszeichnung", "auszeichnung_id"),
    }

    if item["art"] not in columns:
        raise ValueError("Unbekannter Bewertungsgegenstand.")

    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT b.zeitraum_id, b.status
                FROM bewerbung b
                WHERE b.bewerbungs_nr = %s
                FOR UPDATE
                """,
                (application_id,),
            )
            application = cur.fetchone()
            if not application or application[1] not in (
                "Eingereicht", "In_Pruefung"
            ):
                raise ValueError(
                    "Diese Bewerbung ist nicht zur Bewertung freigegeben."
                )

            cur.execute(
                """
                SELECT 1 FROM kommissionsmitglied
                WHERE personen_id = %s
                """,
                (member_id,),
            )
            if not cur.fetchone():
                raise ValueError("Kein Kommissionskonto.")

            cur.execute(
                """
                SELECT 1 FROM auswahlentscheidung
                WHERE bewerbungs_nr = %s
                """,
                (application_id,),
            )
            if cur.fetchone():
                raise ValueError(
                    "Nach der Entscheidung ist die Bewertung gesperrt."
                )

            table, id_column = source_tables[item["art"]]
            # Tabellennamen stammen ausschließlich aus dem festen Mapping.
            cur.execute(
                f"""
                SELECT 1 FROM {table}
                WHERE {id_column} = %s
                  AND bewerbungs_nr = %s
                FOR UPDATE
                """,
                (item["item_id"], application_id),
            )
            if not cur.fetchone():
                raise ValueError(
                    "Dieser Gegenstand gehört nicht zur Bewerbung."
                )

            cur.execute(
                """
                SELECT k.max_punkte
                FROM zeitraum_kriterium zk
                JOIN bewertungskriterium k
                  ON k.kriterium_id = zk.kriterium_id
                WHERE zk.zeitraum_id = %s
                  AND zk.kriterium_id = %s
                """,
                (application[0], criterion_id),
            )
            maximum = cur.fetchone()
            if not maximum or not 0 <= points <= maximum[0]:
                raise ValueError(
                    "Kriterium oder Punktzahl ist für "
                    "diesen Zeitraum ungültig."
                )

            column = columns[item["art"]]
            cur.execute(
                f"""
                SELECT bewertung_id, mitglied_id, kommentar
                FROM bewertung
                WHERE {column} = %s
                FOR UPDATE
                """,
                (item["item_id"],),
            )
            existing = cur.fetchone()

            if existing and existing[1] != member_id:
                raise ValueError(
                    "Dieser Gegenstand wurde von einem anderen "
                    "Kommissionsmitglied übernommen."
                )

            if existing:
                review_id = existing[0]
                old_comment = existing[2] or ""
                cur.execute(
                    """
                    SELECT punkte FROM bewertungspunkt
                    WHERE bewertung_id = %s
                      AND kriterium_id = %s
                    """,
                    (review_id, criterion_id),
                )
                old_points_row = cur.fetchone()

                cur.execute(
                    """
                    UPDATE bewertung
                    SET status = 'abgeschlossen',
                        kommentar = %s,
                        bewertungsdatum = CURRENT_DATE
                    WHERE bewertung_id = %s
                    """,
                    (comment, review_id),
                )

                cur.execute(
                    """
                    INSERT INTO audit_log
                        (mitglied_id, bewertung_id, aktion,
                         alter_wert, neuer_wert)
                    VALUES (%s, %s, 'Bewertung aktualisiert',
                            %s, %s)
                    """,
                    (
                        member_id, review_id,
                        f"Punkte: {old_points_row[0] if old_points_row else '—'}; "
                        f"Kommentar: {old_comment}",
                        f"Punkte: {points}; Kommentar: {comment}",
                    ),
                )
            else:
                cur.execute(
                    f"""
                    INSERT INTO bewertung
                        (bewerbungs_nr, mitglied_id, {column},
                         status, kommentar)
                    VALUES (%s, %s, %s, 'abgeschlossen', %s)
                    RETURNING bewertung_id
                    """,
                    (
                        application_id, member_id,
                        item["item_id"], comment,
                    ),
                )
                review_id = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO bewertungspunkt
                    (bewertung_id, kriterium_id, punkte)
                VALUES (%s, %s, %s)
                ON CONFLICT (bewertung_id, kriterium_id)
                DO UPDATE SET punkte = EXCLUDED.punkte
                """,
                (review_id, criterion_id, points),
            )

            if application[1] == "Eingereicht":
                cur.execute(
                    """
                    UPDATE bewerbung
                    SET status = 'In_Pruefung'
                    WHERE bewerbungs_nr = %s
                    """,
                    (application_id,),
                )


def decision_ready(cur, application_id):
    motivation, performance = required_documents(
        cur, application_id
    )
    if not (motivation and performance):
        return False, "Pflichtdokumente fehlen."

    cur.execute(
        """
        WITH items AS (
            SELECT 'Dokument'::text AS art, dokument_id AS id
            FROM dokument WHERE bewerbungs_nr = %s
            UNION ALL
            SELECT 'Engagement', engagement_id
            FROM engagement WHERE bewerbungs_nr = %s
            UNION ALL
            SELECT 'Lebensumstand', umstand_id
            FROM lebensumstand WHERE bewerbungs_nr = %s
            UNION ALL
            SELECT 'Auszeichnung', auszeichnung_id
            FROM auszeichnung WHERE bewerbungs_nr = %s
        )
        SELECT COUNT(*) AS total,
               COUNT(bw.bewertung_id) FILTER (
                   WHERE bw.status = 'abgeschlossen'
                     AND EXISTS (
                         SELECT 1 FROM bewertungspunkt bp
                         WHERE bp.bewertung_id = bw.bewertung_id
                     )
               ) AS done
        FROM items i
        LEFT JOIN bewertung bw
          ON bw.bewerbungs_nr = %s
         AND (
             (i.art = 'Dokument' AND bw.dokument_id = i.id)
             OR (i.art = 'Engagement' AND bw.engagement_id = i.id)
             OR (i.art = 'Lebensumstand' AND bw.umstand_id = i.id)
             OR (i.art = 'Auszeichnung' AND bw.auszeichnung_id = i.id)
         )
        """,
        (
            application_id, application_id,
            application_id, application_id,
            application_id,
        ),
    )
    total, done = cur.fetchone()
    if total == 0 or done != total:
        return False, f"Erst {done} von {total} Gegenständen bewertet."
    return True, "Alle erfassten Gegenstände bewertet."


def make_decision(member_id, application_id, result, reason):
    if result not in ("Bewilligt", "Warteliste", "Abgelehnt"):
        raise ValueError("Ungültige Förderentscheidung.")
    if not reason.strip():
        raise ValueError("Bitte eine Begründung eingeben.")

    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT status FROM bewerbung
                WHERE bewerbungs_nr = %s
                FOR UPDATE
                """,
                (application_id,),
            )
            row = cur.fetchone()
            if not row or row[0] not in (
                "Eingereicht", "In_Pruefung"
            ):
                raise ValueError(
                    "Diese Bewerbung ist nicht entscheidungsbereit."
                )

            cur.execute(
                """
                SELECT 1 FROM kommissionsmitglied
                WHERE personen_id = %s
                """,
                (member_id,),
            )
            if not cur.fetchone():
                raise ValueError("Kein Kommissionskonto.")

            cur.execute(
                """
                SELECT 1 FROM auswahlentscheidung
                WHERE bewerbungs_nr = %s
                """,
                (application_id,),
            )
            if cur.fetchone():
                raise ValueError(
                    "Für diese Bewerbung besteht bereits eine Entscheidung."
                )

            ready, reason_not_ready = decision_ready(
                cur, application_id
            )
            if not ready:
                raise ValueError(reason_not_ready)

            cur.execute(
                """
                INSERT INTO auswahlentscheidung
                    (bewerbungs_nr, foerderstatus, begruendung)
                VALUES (%s, %s, %s)
                RETURNING entscheidungs_id
                """,
                (application_id, result, reason.strip()),
            )
            decision_id = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO entscheidungsbeteiligung
                    (entscheidungs_id, mitglied_id)
                VALUES (%s, %s)
                """,
                (decision_id, member_id),
            )

            cur.execute(
                """
                UPDATE bewerbung
                SET status = 'Abgeschlossen'
                WHERE bewerbungs_nr = %s
                """,
                (application_id,),
            )

            cur.execute(
                """
                INSERT INTO benachrichtigung
                    (bewerbungs_nr, typ, sendestatus)
                VALUES (%s, 'Förderentscheidung', 'Ausstehend')
                """,
                (application_id,),
            )

            cur.execute(
                """
                INSERT INTO audit_log
                    (mitglied_id, entscheidungs_id,
                     aktion, neuer_wert)
                VALUES (%s, %s, 'Entscheidung erfasst', %s)
                """,
                (member_id, decision_id, result),
            )




def commission_list(applications):
    st.subheader("Bewerbungen finden")

    search = st.text_input(
        "Name oder Matrikelnummer suchen",
        key="commission_search",
    ).strip().casefold()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        application_filter = st.selectbox(
            "Bewerbungsstatus",
            [
                "Alle", "Eingereicht",
                "In_Pruefung", "Abgeschlossen",
            ],
        )
    with col2:
        review_filter = st.selectbox(
            "Bewertungsstand",
            [
                "Alle", "Offen", "Teilweise bewertet",
                "Alle erfassten bewertet", "Keine Gegenstände",
            ],
        )
    with col3:
        decision_filter = st.selectbox(
            "Entscheidung",
            [
                "Alle", "Noch offen", "Bewilligt",
                "Warteliste", "Abgelehnt",
            ],
        )
    with col4:
        sorting = st.selectbox(
            "Sortieren nach",
            [
                "Name A–Z", "Name Z–A",
                "Matrikelnummer", "Bearbeitungsfortschritt",
            ],
        )

    results = []
    for application in applications:
        searchable = (
            f"{application['vorname']} "
            f"{application['nachname']} "
            f"{application['matrikel_nr']}"
        ).casefold()

        if search and search not in searchable:
            continue
        if (
            application_filter != "Alle"
            and application["status"] != application_filter
        ):
            continue
        if (
            review_filter != "Alle"
            and review_state(application) != review_filter
        ):
            continue
        if (
            decision_filter != "Alle"
            and application["entscheidung"] != decision_filter
        ):
            continue
        results.append(application)

    if sorting == "Name A–Z":
        results.sort(
            key=lambda x: (
                x["nachname"].casefold(),
                x["vorname"].casefold(),
            )
        )
    elif sorting == "Name Z–A":
        results.sort(
            key=lambda x: (
                x["nachname"].casefold(),
                x["vorname"].casefold(),
            ),
            reverse=True,
        )
    elif sorting == "Matrikelnummer":
        results.sort(key=lambda x: x["matrikel_nr"])
    else:
        results.sort(
            key=lambda x: (
                x["done"] / x["total"] if x["total"] else 0,
                x["nachname"].casefold(),
            )
        )

    st.write(f"**{len(results)} Treffer**")

    for application in results:
        with st.container(border=True):
            left, right = st.columns([4, 1])

            with left:
                st.subheader(
                    f"{application['vorname']} "
                    f"{application['nachname']} · "
                    f"{application['matrikel_nr']}"
                )
                st.write(
                    f"**Bewerbung:** {application['status']}"
                    f"**Bewertung:** {review_state(application)}"
                    f"**Entscheidung:** {application['entscheidung']}"
                )
                show_progress(application)

            with right:
                if st.button(
                    "Öffnen →",
                    key=f"open_{application['bewerbungs_nr']}",
                    use_container_width=True,
                ):
                    st.session_state["commission_detail"] = (
                        application["bewerbungs_nr"]
                    )
                    st.rerun()

    if not results:
        st.info("Keine Bewerbung passt zu Suche und Filtern.")

def zeitraum_entscheidung_info(zeitraum_id: int) -> dict:
    """Frist, Kapazität und heutiges Datum direkt aus PostgreSQL lesen."""
    rows = query(
        """
        SELECT
            bz.ende,
            bz.ende + 1 AS entscheidungen_ab,
            CURRENT_DATE AS heute,
            bz.max_foerderplaetze,
            (
                SELECT COUNT(*)
                FROM bewerbung b
                JOIN auswahlentscheidung a
                  ON a.bewerbungs_nr = b.bewerbungs_nr
                WHERE b.zeitraum_id = bz.zeitraum_id
                  AND a.foerderstatus = 'Bewilligt'
            ) AS bereits_bewilligt
        FROM bewerbungszeitraum bz
        WHERE bz.zeitraum_id = %s
        """,
        (zeitraum_id,),
    )
    if len(rows) != 1:
        raise ValueError("Bewerbungszeitraum nicht gefunden.")
    return rows[0]

def commission_detail(application, member_id):
    number = application["bewerbungs_nr"]

    if st.button("← Zur Trefferliste"):
        st.session_state.pop("commission_detail", None)
        st.rerun()

    st.title(
        f"{application['vorname']} {application['nachname']}"
    )
    st.caption(
        f"{application['matrikel_nr']} · Bewerbung Nr. {number}"
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Bewerbung", application["status"])
    c2.metric("Bewertung", review_state(application))
    c3.metric("Entscheidung", application["entscheidung"])
    show_progress(application)

    items = query(SQL_COMMISSION_ITEMS, (number,))

    tab_review, tab_overview, tab_decision = st.tabs(
        [
            "Unterlage & Bewertung",
            "Bearbeitungsstand",
            "Auswahlentscheidung",
        ]
    )

    with tab_review:
        if not items:
            st.info("Noch keine erfassten Gegenstände.")
        else:
            selected = st.selectbox(
                "Gegenstand auswählen",
                items,
                format_func=lambda item: (
                    "✓ " if item_done(item) else "○ "
                ) + item_label(item),
                key=f"selected_item_{number}",
            )

            left, right = st.columns([1.2, 1], gap="large")

            with left:
                st.subheader(item_label(selected))

                if selected["art"] == "Dokument":
                    data = read_private_pdf(
                        selected["dateipfad"]
                    )
                    if data is None:
                        st.info(
                            "Zu diesem Datenbankeintrag liegt hier "
                            "keine echte lokale PDF vor. Ältere "
                            "Demodateipfade sind nur Platzhalter."
                        )
                    else:
                        if hasattr(st, "pdf"):
                            st.pdf(data, height=550)
                        else:
                            st.info(
                                "Diese Streamlit-Version bietet keine "
                                "eingebaute PDF-Vorschau."
                            )
                        st.download_button(
                            "PDF öffnen / herunterladen",
                            data=data,
                            file_name=selected["titel"],
                            mime="application/pdf",
                            key=(
                                f"commission_download_{number}_"
                                f"{selected['item_id']}"
                            ),
                        )
                else:
                    st.text_area(
                        "Erfasste Angabe",
                        value=selected["beschreibung"] or "",
                        height=250,
                        disabled=True,
                        key=(
                            f"item_text_{number}_"
                            f"{selected['art']}_"
                            f"{selected['item_id']}"
                        ),
                    )

            with right:
                st.subheader("Bewertung")
                if selected["bewertet_von"]:
                    st.caption(
                        f"Bearbeitet von: {selected['bewertet_von']}"
                    )

                if item_done(selected):
                    st.success("Bewertet")
                elif selected["bewertung_id"] is not None:
                    st.warning("Bewertung noch nicht abgeschlossen")
                else:
                    st.info("Noch offen")

                existing_points = []
                if selected["bewertung_id"] is not None:
                    existing_points = query(
                        """
                        SELECT bp.kriterium_id, k.name,
                               bp.punkte
                        FROM bewertungspunkt bp
                        JOIN bewertungskriterium k
                          ON k.kriterium_id = bp.kriterium_id
                        WHERE bp.bewertung_id = %s
                        ORDER BY k.name
                        """,
                        (selected["bewertung_id"],),
                    )

                status_tabelle(
                    existing_points,
                    "Noch keine Punkte vergeben.",
                )

                locked = (
                    application["entscheidung"] != "Noch offen"
                    or application["status"]
                    not in ("Eingereicht", "In_Pruefung")
                    or (
                        selected["mitglied_id"] is not None
                        and selected["mitglied_id"] != member_id
                    )
                )

                if locked:
                    st.caption(
                        "Diese Bewertung kann mit diesem Konto "
                        "nicht verändert werden."
                    )
                else:
                    criteria = query(
                        SQL_PERIOD_CRITERIA,
                        (application["zeitraum_id"],),
                    )

                    if not criteria:
                        st.warning(
                            "Für diesen Zeitraum sind keine "
                            "Bewertungskriterien eingerichtet."
                        )
                    else:
                        criterion = st.selectbox(
                            "Kriterium",
                            criteria,
                            format_func=lambda x: (
                                f"{x['name']} "
                                f"(max. {x['max_punkte']} Punkte; "
                                f"Gewicht {x['gewichtung']})"
                            ),
                            key=f"criterion_{number}",
                        )

                        previous = next(
                            (
                                row["punkte"]
                                for row in existing_points
                                if row["kriterium_id"]
                                == criterion["kriterium_id"]
                            ),
                            0,
                        )

                        with st.form(
                            f"review_{number}_"
                            f"{selected['art']}_"
                            f"{selected['item_id']}_"
                            f"{criterion['kriterium_id']}"
                        ):
                            points = st.number_input(
                                "Punkte",
                                min_value=0,
                                max_value=criterion["max_punkte"],
                                value=previous,
                                step=1,
                            )
                            comment = st.text_area(
                                "Kommentar",
                                value=selected["kommentar"] or "",
                            )
                            save = st.form_submit_button(
                                "Bewertung speichern",
                                type="primary",
                            )

                        if save:
                            try:
                                review_item(
                                    member_id,
                                    number,
                                    selected,
                                    criterion["kriterium_id"],
                                    int(points),
                                    comment.strip(),
                                )
                                st.success("Bewertung gespeichert.")
                                st.rerun()
                            except ValueError as exc:
                                st.error(str(exc))
                            except psycopg.Error:
                                st.error(
                                    "Bewertung konnte nicht "
                                    "gespeichert werden."
                                )

    with tab_overview:
        status_tabelle(
            [
                {
                    "Art": item["art"],
                    "Dokumenttyp": (
                        item["dokumenttyp"]
                        if item["art"] == "Dokument"
                        else "—"
                    ),
                    "Gegenstand / Dateiname": item["titel"],
                    "ID": item["item_id"],
                    "Stand": (
                        "Bewertet" if item_done(item)
                        else "Offen"
                    ),
                    "Bearbeitet von": item["bewertet_von"] or "—",
                }
                for item in items
            ],
            "Keine Gegenstände vorhanden.",
        )
        st.caption(
            "Die grüne Leiste zeigt nur, dass alle bislang "
            "erfassten Gegenstände bewertet wurden."
        )
    with tab_decision:
        st.subheader("Förderentscheidung")

        info = zeitraum_entscheidung_info(
            application["zeitraum_id"]
        )
        frist_abgelaufen = info["heute"] > info["ende"]
        plaetze_frei = (
            info["max_foerderplaetze"]
            - info["bereits_bewilligt"]
        )

        frist_spalte, platz_spalte = st.columns(2)
        frist_spalte.metric(
            "Entscheidungen möglich ab",
            str(info["entscheidungen_ab"]),
        )
        platz_spalte.metric(
            "Bereits bewilligte Plätze",
            (
                f"{info['bereits_bewilligt']} / "
                f"{info['max_foerderplaetze']}"
            ),
        )

        if application["entscheidung"] != "Noch offen":
            st.success(
                "Für diese Bewerbung wurde bereits entschieden: "
                f"{application['entscheidung']}."
            )
            st.caption(
                "Eine bestehende Entscheidung wird hier nicht erneut "
                "gespeichert. Ältere Demodaten können vor Einführung "
                "der Fristregel angelegt worden sein."
            )

        elif not frist_abgelaufen:
            st.warning(
                f"Die Bewerbungsfrist läuft bis einschließlich "
                f"{info['ende']}. Eine Entscheidung ist erst ab "
                f"{info['entscheidungen_ab']} möglich."
            )

        elif application["status"] not in (
            "Eingereicht",
            "In_Pruefung",
        ):
            st.info(
                "Diese Bewerbung hat keinen Status, in dem eine "
                "neue Förderentscheidung erfasst werden kann."
            )

        else:
            with db() as conn:
                with conn.cursor() as cur:
                    bereit, meldung = decision_ready(cur, number)

            if bereit:
                st.success(meldung)
            else:
                st.warning(meldung)

            if plaetze_frei <= 0:
                st.info(
                    "Alle Förderplätze sind bereits vergeben. "
                    "Warteliste und Ablehnung bleiben möglich."
                )
                moegliche_ergebnisse = [
                    "Warteliste",
                    "Abgelehnt",
                ]
            else:
                st.caption(
                    f"Noch {plaetze_frei} Förderplatz/-plätze verfügbar."
                )
                moegliche_ergebnisse = [
                    "Bewilligt",
                    "Warteliste",
                    "Abgelehnt",
                ]

            with st.form(f"decision_{number}"):
                ergebnis = st.selectbox(
                    "Förderentscheidung",
                    moegliche_ergebnisse,
                )
                begruendung = st.text_area("Begründung *")
                bestaetigung = st.checkbox(
                    "Ich bestätige diese endgültige Entscheidung."
                )
                speichern = st.form_submit_button(
                    "Entscheidung erfassen",
                    type="primary",
                    disabled=not bereit,
                )

            if speichern:
                if not bestaetigung:
                    st.warning(
                        "Bitte bestätige zuerst die Entscheidung."
                    )
                else:
                    try:
                        make_decision(
                            member_id,
                            number,
                            ergebnis,
                            begruendung,
                        )
                        st.success("Entscheidung gespeichert.")
                        st.rerun()

                    except ValueError as exc:
                        st.error(str(exc))

                    except psycopg.Error as exc:
                        # Zwischen Anzeige und Klick könnte ein anderes
                        # Mitglied den letzten freien Platz vergeben haben.
                        meldung_db = str(exc)

                        if "Keine freien Förderplätze" in meldung_db:
                            st.error(
                                "Inzwischen sind alle Förderplätze "
                                "vergeben. Bitte aktualisiere die Seite "
                                "und wähle Warteliste oder Abgelehnt."
                            )
                        elif (
                            "Förderentscheidungen sind erst"
                            in meldung_db
                        ):
                            st.error(
                                "Die Bewerbungsfrist ist noch nicht "
                                "abgelaufen."
                            )
                        else:
                            st.error(
                                "Die Entscheidung konnte nicht "
                                "gespeichert werden."
                            )
    


def commission_dashboard(member_id):
    st.sidebar.radio(
        "Kommissionsbereich",
        ["Bewerbungen", "Rangliste", "Entscheidungen"],
        key="commission_menu",
        on_change=lambda: st.session_state.pop(
            "commission_detail", None
        ),
    )

    menu = st.session_state["commission_menu"]

    if menu == "Rangliste":
        st.title("Interne Rangliste")
        status_tabelle(
            query(
                """
                SELECT zeitraum_id, position, bewerbungs_nr,
                       matrikel_nr, vorname, nachname,
                       gesamt_score
                FROM rangliste
                ORDER BY zeitraum_id, position, bewerbungs_nr
                """
            ),
            "Noch keine abgeschlossenen Bewerbungen.",
        )
        return

    if menu == "Entscheidungen":
        st.title("Auswahlentscheidungen")
        status_tabelle(
            query(
                """
                SELECT a.bewerbungs_nr, s.matrikel_nr,
                       a.foerderstatus, a.entscheidungsdatum,
                       a.begruendung
                FROM auswahlentscheidung a
                JOIN bewerbung b
                  ON b.bewerbungs_nr = a.bewerbungs_nr
                JOIN studierender s
                  ON s.personen_id = b.studierenden_id
                ORDER BY a.entscheidungsdatum DESC,
                         a.entscheidungs_id DESC
                """
            ),
            "Noch keine Entscheidungen vorhanden.",
        )
        return

    applications = query(SQL_COMMISSION_APPLICATIONS)
    detail_id = st.session_state.get("commission_detail")

    if detail_id is not None:
        application = next(
            (
                a for a in applications
                if a["bewerbungs_nr"] == detail_id
            ),
            None,
        )
        if application is None:
            st.session_state.pop("commission_detail", None)
            st.warning("Bewerbung nicht verfügbar.")
        else:
            commission_detail(application, member_id)
        return

    st.title("Kommissions-Dashboard")
    st.caption(
        "Nur eingereichte oder später bearbeitete Bewerbungen "
        "werden angezeigt; Entwürfe sind privat."
    )
    commission_list(applications)


# ============================================================
# App-Start
# ============================================================

try:
    if "user" not in st.session_state:
        access = st.radio(
            "Zugang",
            ["Anmelden", "Als Bewerber registrieren"],
            horizontal=True,
        )
        if access == "Anmelden":
            anmelden()
        else:
            registrieren()
        st.stop()

    user = st.session_state["user"]
    current_role = rolle_aktuell(user["id"])

    if current_role != user["role"]:
        st.session_state.clear()
        st.warning(
            "Die Sitzung ist nicht mehr gültig. "
            "Bitte erneut anmelden."
        )
        st.stop()

    st.sidebar.write(f"Angemeldet: {user['name']}")
    if st.sidebar.button("Abmelden"):
        st.session_state.clear()
        st.rerun()

    if current_role == "bewerber":
        applicant_dashboard(user["id"])
    else:
        commission_dashboard(user["id"])

except (psycopg.Error, RuntimeError):
    st.error(
        "Die Datenbankabfrage konnte nicht ausgeführt werden. "
        "Prüfe PostgreSQL und die lokale .env-Datei."
    )