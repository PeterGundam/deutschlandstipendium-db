import html

import streamlit as st


st.set_page_config(
    page_title="Deutschlandstipendium – UX-Prototyp",
    page_icon="🎓",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container { max-width: 1200px; padding-top: 2rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


BEWERBER_SEITEN = [
    "Übersicht",
    "Meine Angaben",
    "Dokumente hochladen",
    "Prüfen & einreichen",
    "Nachrichten & Entscheidung",
]

KOMMISSION_SEITEN = [
    "Übersicht",
    "Bewerbungen",
    "Bewertungsaufgaben",
    "Rangliste",
    "Entscheidungen",
]

# Ausschließlich fiktive Daten für den Oberflächen-Test.
BEWERBUNGEN = {
    "A": {
        "name": "Lena Beispiel",
        "matrikel": "DEMO-1001",
        "status": "Eingereicht",
        "gegenstaende": [
            {
                "id": "a-motivation",
                "art": "Dokument",
                "titel": "Motivationsschreiben",
                "kriterium": "Motivation",
                "max_punkte": 10,
                "inhalt": (
                    "Fiktiver Inhalt des Motivationsschreibens:\n\n"
                    "Ich bewerbe mich, weil ich mein Studium mit "
                    "gesellschaftlichem Engagement verbinde."
                ),
            },
            {
                "id": "a-leistung",
                "art": "Dokument",
                "titel": "Leistungsnachweis",
                "kriterium": "Studienleistung",
                "max_punkte": 10,
                "inhalt": (
                    "Fiktiver Leistungsnachweis.\n\n"
                    "Durchschnittsnote: 1,7.\n\n"
                    "Hier würde später die echte PDF angezeigt."
                ),
            },
            {
                "id": "a-engagement",
                "art": "Engagement",
                "titel": "Studentisches Lernprojekt",
                "kriterium": "Engagement",
                "max_punkte": 10,
                "inhalt": (
                    "Art: Ehrenamt\n\n"
                    "Beschreibung: Wöchentliche Unterstützung "
                    "eines studentischen Lernprojekts."
                ),
            },
            {
                "id": "a-auszeichnung",
                "art": "Auszeichnung",
                "titel": "Fiktiver Projektpreis",
                "kriterium": "Auszeichnungen",
                "max_punkte": 10,
                "inhalt": (
                    "Titel: Fiktiver Projektpreis\n\n"
                    "Beschreibung: Auszeichnung für ein "
                    "studentisches Gemeinschaftsprojekt."
                ),
            },
        ],
    },
    "B": {
        "name": "Noah Testmann",
        "matrikel": "DEMO-1002",
        "status": "In_Pruefung",
        "gegenstaende": [
            {
                "id": "b-motivation",
                "art": "Dokument",
                "titel": "Motivationsschreiben",
                "kriterium": "Motivation",
                "max_punkte": 10,
                "inhalt": "Fiktiver Motivationstext von Noah.",
            },
            {
                "id": "b-umstand",
                "art": "Lebensumstand",
                "titel": "Besonderer Lebensumstand",
                "kriterium": "Lebensumstände",
                "max_punkte": 10,
                "inhalt": (
                    "Fiktive sensible Angabe für den UX-Test.\n\n"
                    "In der echten Anwendung nur für berechtigte "
                    "Kommissionsmitglieder sichtbar."
                ),
            },
        ],
    },
    "C": {
        "name": "Sofia Mustermann",
        "matrikel": "DEMO-1003",
        "status": "Abgeschlossen",
        "gegenstaende": [
            {
                "id": "c-engagement",
                "art": "Engagement",
                "titel": "Ehrenamt",
                "kriterium": "Engagement",
                "max_punkte": 10,
                "inhalt": "Fiktives ehrenamtliches Engagement.",
            },
            {
                "id": "c-leistung",
                "art": "Dokument",
                "titel": "Leistungsnachweis",
                "kriterium": "Studienleistung",
                "max_punkte": 10,
                "inhalt": (
                    "Fiktiver Leistungsnachweis.\n\n"
                    "Hier würde später die echte PDF angezeigt."
                ),
            },
        ],
    },
}


def initialisieren():
    defaults = {
        "ux_rolle": None,
        "bewerber_seite": "Übersicht",
        "kommission_seite": "Übersicht",
        "detail_bewerbung": None,
        "suche_bewerbung": "",
        "filter_status": "Alle",
        "filter_bewertung": "Offene Bewertungsaufgaben",
        "sortierung": "Name A–Z",
        "filter_entscheidung": "Alle",
        "demo_bewertungen": {
            "a-engagement": {
                "punkte": 8,
                "kommentar": "Engagement nachvollziehbar.",
            },
            "c-engagement": {
                "punkte": 9,
                "kommentar": "Engagement geprüft.",
            },
            "c-leistung": {
                "punkte": 7,
                "kommentar": "Leistungsnachweis geprüft.",
            },
        },
        "demo_entscheidungen": {},
        "demo_uploads": [],
        "demo_angaben": {
            "engagement": "",
            "auszeichnungen": "",
            "lebensumstaende": "",
        },
    }

    for schluessel, wert in defaults.items():
        if schluessel not in st.session_state:
            st.session_state[schluessel] = wert


def start_oeffnen():
    st.session_state.ux_rolle = None
    st.session_state.detail_bewerbung = None


def rolle_oeffnen(rolle):
    st.session_state.ux_rolle = rolle
    st.session_state.detail_bewerbung = None
    if rolle == "Bewerber":
        st.session_state.bewerber_seite = "Übersicht"
    elif rolle == "Kommission":
        st.session_state.kommission_seite = "Übersicht"


def bewerber_oeffnen(seite):
    st.session_state.bewerber_seite = seite


def kommission_oeffnen(seite):
    st.session_state.kommission_seite = seite
    st.session_state.detail_bewerbung = None


def bewerbung_oeffnen(kennung):
    st.session_state.detail_bewerbung = kennung


def zur_trefferliste():
    st.session_state.detail_bewerbung = None


def gegenstaende(kennung):
    return BEWERBUNGEN[kennung]["gegenstaende"]


def ist_bewertet(gegenstand):
    return gegenstand["id"] in st.session_state.demo_bewertungen


def bearbeitungsstand(kennung):
    liste = gegenstaende(kennung)
    fertig = sum(ist_bewertet(g) for g in liste)
    return fertig, len(liste)


def bewertungslabel(kennung):
    fertig, gesamt = bearbeitungsstand(kennung)
    if gesamt > 0 and fertig == gesamt:
        return "Geprüft"
    if fertig > 0:
        return "Teilweise bewertet"
    return "Offen"


def fortschritt_anzeigen(kennung):
    """Vollständiger Fortschritt wird ausdrücklich grün gezeichnet."""
    fertig, gesamt = bearbeitungsstand(kennung)
    prozent = round(100 * fertig / gesamt) if gesamt else 0

    if gesamt and fertig == gesamt:
        st.markdown(
            f"""
            <div aria-label="{fertig} von {gesamt} Gegenständen bewertet"
                 style="background:#25303b;border-radius:12px;
                        height:13px;overflow:hidden;">
                <div style="background:#22c55e;width:100%;
                            height:13px;"></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(f"✅ {fertig} von {gesamt} bewertet · Geprüft")
    else:
        st.progress(
            prozent,
            text=f"{fertig} von {gesamt} Gegenständen bewertet",
        )


# -------------------------------------------------------------------
# Einstieg und Bewerber-Prototyp
# -------------------------------------------------------------------

def startseite():
    st.title("🎓 Deutschlandstipendium")
    st.subheader("Bewerben und bewerten – mit einem klaren Arbeitsablauf")
    st.info(
        "UX-Prototyp: keine echte Anmeldung und keine Änderungen "
        "an PostgreSQL."
    )

    links, rechts = st.columns(2, gap="large")

    with links:
        st.markdown("### Für Bewerber")
        st.write(
            "Bewerbung vorbereiten, Angaben erfassen und "
            "Dokumentarten auswählen."
        )
        st.button(
            "Bewerberansicht testen",
            on_click=rolle_oeffnen,
            args=("Bewerber",),
            use_container_width=True,
            type="primary",
        )
        st.button(
            "Als Bewerber registrieren",
            on_click=rolle_oeffnen,
            args=("Registrierung",),
            use_container_width=True,
        )

    with rechts:
        st.markdown("### Für die Kommission")
        st.write(
            "Bewerbungen suchen, Unterlagen bewerten und "
            "Entscheidungen treffen."
        )
        st.button(
            "Kommissionsansicht testen",
            on_click=rolle_oeffnen,
            args=("Kommission",),
            use_container_width=True,
        )


def registrierung():
    st.title("Bewerberkonto erstellen")
    st.caption("UX-Vorschau: Es wird kein Konto angelegt.")

    with st.form("registrierung"):
        vorname = st.text_input("Vorname *")
        nachname = st.text_input("Nachname *")
        email = st.text_input("E-Mail-Adresse *")
        matrikel = st.text_input("Matrikelnummer *")
        passwort = st.text_input("Passwort *", type="password")
        wiederholung = st.text_input(
            "Passwort wiederholen *", type="password"
        )
        gesendet = st.form_submit_button(
            "Registrierung testen", type="primary"
        )

    if gesendet:
        if not all(
            x.strip()
            for x in [vorname, nachname, email, matrikel, passwort]
        ):
            st.warning("Bitte alle Pflichtfelder ausfüllen.")
        elif "@" not in email:
            st.warning("Bitte eine plausible E-Mail-Adresse eingeben.")
        elif passwort != wiederholung:
            st.warning("Die Passwörter stimmen nicht überein.")
        else:
            st.success("Vorschau erfolgreich. Kein Konto gespeichert.")

    st.button("← Zur Startseite", on_click=start_oeffnen)


def bewerber_dashboard():
    st.sidebar.title("Meine Bewerbung")
    st.sidebar.radio(
        "Navigation", BEWERBER_SEITEN, key="bewerber_seite"
    )
    st.sidebar.button("Zur Startseite", on_click=start_oeffnen)

    seite = st.session_state.bewerber_seite
    st.title("Mein Bewerber-Dashboard")
    st.caption("Fiktive Daten · Änderungen nur für diese Sitzung")

    if seite == "Übersicht":
        st.subheader("Willkommen!")
        a, b, c = st.columns(3)
        a.metric("Status", "Entwurf")
        b.metric(
            "Ausgewählte Dokumente",
            len(st.session_state.demo_uploads),
        )
        c.metric("Nächster Schritt", "Angaben ergänzen")
        st.button(
            "Mit meinen Angaben fortfahren →",
            on_click=bewerber_oeffnen,
            args=("Meine Angaben",),
            type="primary",
        )

    elif seite == "Meine Angaben":
        st.subheader("Meine Angaben")

        with st.form("angaben"):
            engagement = st.text_area(
                "Engagement",
                value=st.session_state.demo_angaben["engagement"],
            )
            auszeichnungen = st.text_area(
                "Auszeichnungen (optional)",
                value=st.session_state.demo_angaben["auszeichnungen"],
            )
            lebensumstaende = st.text_area(
                "Lebensumstände (optional)",
                value=st.session_state.demo_angaben["lebensumstaende"],
            )
            speichern = st.form_submit_button("Angaben übernehmen")

        if speichern:
            st.session_state.demo_angaben = {
                "engagement": engagement,
                "auszeichnungen": auszeichnungen,
                "lebensumstaende": lebensumstaende,
            }
            st.success("Angaben für diese Sitzung übernommen.")

        links, rechts = st.columns(2)
        links.button(
            "← Übersicht",
            on_click=bewerber_oeffnen,
            args=("Übersicht",),
        )
        rechts.button(
            "Weiter zu Dokumenten →",
            on_click=bewerber_oeffnen,
            args=("Dokumente hochladen",),
            type="primary",
        )

    elif seite == "Dokumente hochladen":
        st.subheader("Dokumente hochladen")
        st.write("Wähle für **jede PDF** ihre Dokumentart aus.")

        with st.form("upload"):
            art = st.selectbox(
                "Dokumentart",
                [
                    "Motivationsschreiben",
                    "Leistungsnachweis",
                    "Beleg für Engagement",
                    "Beleg für Auszeichnung",
                    "Sonstiges Dokument",
                ],
            )
            datei = st.file_uploader("PDF auswählen", type=["pdf"])
            speichern = st.form_submit_button(
                "Zuordnung testen", type="primary"
            )

        if speichern:
            if datei is None:
                st.warning("Bitte zuerst eine PDF auswählen.")
            else:
                st.session_state.demo_uploads.append(
                    {"Dateiname": datei.name, "Dokumentart": art}
                )
                st.success(
                    "Zuordnung vorgemerkt. Die PDF wurde nicht gespeichert."
                )

        if st.session_state.demo_uploads:
            st.dataframe(
                st.session_state.demo_uploads,
                hide_index=True,
                width="stretch",
            )

        links, rechts = st.columns(2)
        links.button(
            "← Angaben",
            on_click=bewerber_oeffnen,
            args=("Meine Angaben",),
        )
        rechts.button(
            "Weiter zur Prüfung →",
            on_click=bewerber_oeffnen,
            args=("Prüfen & einreichen",),
            type="primary",
        )

    elif seite == "Prüfen & einreichen":
        st.subheader("Bewerbung prüfen")
        arten = {
            d["Dokumentart"] for d in st.session_state.demo_uploads
        }
        motivation = "Motivationsschreiben" in arten
        leistung = "Leistungsnachweis" in arten

        st.write(
            ("✅" if motivation else "⬜")
            + " Motivationsschreiben ausgewählt"
        )
        st.write(
            ("✅" if leistung else "⬜")
            + " Leistungsnachweis ausgewählt"
        )

        if motivation and leistung:
            st.success("Die vorgesehenen Dokumentarten sind ausgewählt.")
        else:
            st.warning("Es fehlen noch Pflichtdokumente.")

        st.info(
            "Verbindliches Einreichen erfolgt erst in der "
            "echten Datenbankanwendung."
        )
        st.button("Verbindlich einreichen", disabled=True)
        st.button(
            "← Zurück zu Dokumenten",
            on_click=bewerber_oeffnen,
            args=("Dokumente hochladen",),
        )

    else:
        st.subheader("Nachrichten & Entscheidung")
        st.info(
            "Hier erscheinen später eigene Nachrichten und "
            "die eigene Entscheidung."
        )
        st.button(
            "← Übersicht",
            on_click=bewerber_oeffnen,
            args=("Übersicht",),
        )


# -------------------------------------------------------------------
# Suche, Filter und Sortierung für die Kommission
# -------------------------------------------------------------------

def bewerbungen_filtern():
    suchtext = st.session_state.suche_bewerbung.strip().casefold()
    status_filter = st.session_state.filter_status
    bewertungs_filter = st.session_state.filter_bewertung
    entscheidungs_filter = st.session_state.filter_entscheidung

    treffer = []

    for kennung, daten in BEWERBUNGEN.items():
        durchsuchbar = (
            daten["name"] + " " + daten["matrikel"]
        ).casefold()

        if suchtext and suchtext not in durchsuchbar:
            continue

        if status_filter != "Alle" and daten["status"] != status_filter:
            continue

        bewertungsstand = bewertungslabel(kennung)

        if (
            bewertungs_filter == "Offene Bewertungsaufgaben"
            and bewertungsstand == "Geprüft"
        ):
            continue

        if (
            bewertungs_filter in ("Offen", "Teilweise bewertet", "Geprüft")
            and bewertungsstand != bewertungs_filter
        ):
            continue

        entscheidung = st.session_state.demo_entscheidungen.get(kennung)
        entscheidungsstand = (
            entscheidung["status"] if entscheidung else "Noch offen"
        )

        if (
            entscheidungs_filter != "Alle"
            and entscheidungsstand != entscheidungs_filter
        ):
            continue

        treffer.append(kennung)

    sortierung = st.session_state.sortierung
    status_reihenfolge = {
        "Entwurf": 0,
        "Eingereicht": 1,
        "In_Pruefung": 2,
        "Abgeschlossen": 3,
    }

    if sortierung == "Name A–Z":
        treffer.sort(key=lambda k: BEWERBUNGEN[k]["name"].casefold())

    elif sortierung == "Name Z–A":
        treffer.sort(
            key=lambda k: BEWERBUNGEN[k]["name"].casefold(),
            reverse=True,
        )

    elif sortierung == "Matrikelnummer":
        treffer.sort(key=lambda k: BEWERBUNGEN[k]["matrikel"])

    elif sortierung == "Bewerbungsstatus":
        treffer.sort(
            key=lambda k: (
                status_reihenfolge.get(BEWERBUNGEN[k]["status"], 99),
                BEWERBUNGEN[k]["name"].casefold(),
            )
        )

    elif sortierung == "Bearbeitungsfortschritt":
        treffer.sort(
            key=lambda k: (
                bearbeitungsstand(k)[0] / bearbeitungsstand(k)[1]
                if bearbeitungsstand(k)[1] else 0,
                BEWERBUNGEN[k]["name"].casefold(),
            )
        )

    return treffer


def suchseite():
    st.subheader("Bewerbungen finden")
    st.caption(
        "Geprüfte und entschiedene Bewerbungen bleiben über die Filter "
        "„Alle“ oder ihren jeweiligen Status auffindbar."
    )

    st.text_input(
        "Name oder Matrikelnummer",
        placeholder="z. B. Lena oder DEMO-1001",
        key="suche_bewerbung",
    )

    spalte_status, spalte_bewertung, spalte_entscheidung, spalte_sortierung = (
        st.columns(4)
    )

    with spalte_status:
        st.selectbox(
            "Bewerbungsstatus",
            ["Alle", "Eingereicht", "In_Pruefung", "Abgeschlossen"],
            key="filter_status",
        )

    with spalte_bewertung:
        st.selectbox(
            "Bewertungsstand",
            [
                "Offene Bewertungsaufgaben",
                "Alle",
                "Offen",
                "Teilweise bewertet",
                "Geprüft",
            ],
            key="filter_bewertung",
        )

    with spalte_entscheidung:
        st.selectbox(
            "Entscheidung",
            ["Alle", "Noch offen", "Bewilligt", "Warteliste", "Abgelehnt"],
            key="filter_entscheidung",
        )

    with spalte_sortierung:
        st.selectbox(
            "Sortieren nach",
            [
                "Name A–Z",
                "Name Z–A",
                "Matrikelnummer",
                "Bewerbungsstatus",
                "Bearbeitungsfortschritt",
            ],
            key="sortierung",
        )

    treffer = bewerbungen_filtern()
    st.write(f"**{len(treffer)} Treffer**")

    if not treffer:
        st.info(
            "Keine passenden Bewerbungen. Prüfe insbesondere, ob der "
            "Bewertungsfilter „Offene Bewertungsaufgaben“ eine bereits "
            "geprüfte Bewerbung ausblendet."
        )
        return

    for kennung in treffer:
        daten = BEWERBUNGEN[kennung]
        entscheidung = st.session_state.demo_entscheidungen.get(kennung)
        entscheidungsstand = (
            entscheidung["status"] if entscheidung else "Noch offen"
        )

        with st.container(border=True):
            info, aktion = st.columns([4, 1])

            with info:
                st.markdown(
                    f"### {daten['name']} · {daten['matrikel']}"
                )
                st.write(
                    f"**Bewerbungsstatus:** {daten['status']}"
                    f"**Bewertungsstand:** {bewertungslabel(kennung)}"
                )
                st.write(f"**Entscheidung:** {entscheidungsstand}")
                fortschritt_anzeigen(kennung)

            with aktion:
                st.button(
                    "Bewerbung öffnen →",
                    key=f"oeffnen_{kennung}",
                    on_click=bewerbung_oeffnen,
                    args=(kennung,),
                    use_container_width=True,
                )


# -------------------------------------------------------------------
# Bewerbungsdetail, Bewertung und Entscheidung
# -------------------------------------------------------------------

def entscheidung_erfassen(kennung):
    entscheidung = st.session_state.demo_entscheidungen.get(kennung)

    if entscheidung:
        st.success(
            f"Entscheidung erfasst: **{entscheidung['status']}**"
        )
        st.write(
            "**Begründung:** "
            + (entscheidung["begruendung"] or "Keine Begründung")
        )
        st.caption(
            "Im Prototyp ist die Bewertung nach einer Entscheidung "
            "gesperrt. Eine spätere Korrektur bräuchte einen "
            "gesonderten, protokollierten Ablauf."
        )
        return

    if bewertungslabel(kennung) != "Geprüft":
        st.warning(
            "Eine Entscheidung ist erst möglich, wenn alle "
            "erfassten Gegenstände bewertet wurden."
        )
        return

    st.info(
        "Die Bewertung ist vollständig. Jetzt kann die Kommission "
        "separat über die Förderung entscheiden."
    )

    with st.form(f"entscheidung_{kennung}"):
        status = st.selectbox(
            "Förderentscheidung",
            ["Bewilligt", "Warteliste", "Abgelehnt"],
        )
        begruendung = st.text_area("Begründung")
        bestaetigung = st.checkbox(
            "Ich möchte diese Entscheidung im Prototyp festhalten."
        )
        speichern = st.form_submit_button(
            "Entscheidung erfassen",
            type="primary",
        )

    if speichern:
        if not bestaetigung:
            st.warning("Bitte die Entscheidung zunächst bestätigen.")
        else:
            st.session_state.demo_entscheidungen[kennung] = {
                "status": status,
                "begruendung": begruendung.strip(),
            }
            st.rerun()


def detailseite(kennung):
    daten = BEWERBUNGEN[kennung]
    liste = gegenstaende(kennung)
    entschieden = kennung in st.session_state.demo_entscheidungen

    st.button(
        "← Zur Trefferliste",
        on_click=zur_trefferliste,
    )

    st.title(daten["name"])
    st.caption(
        f"{daten['matrikel']} · Bewerbungsstatus: "
        f"{daten['status']}"
    )

    fortschritt_anzeigen(kennung)

    if bewertungslabel(kennung) == "Geprüft":
        st.success(
            "Alle erfassten Gegenstände sind bewertet. "
            "Bewertungsstand: Geprüft."
        )
    else:
        st.info(
            f"Bewertungsstand: {bewertungslabel(kennung)}"
        )

    if entschieden:
        st.info(
            "Für diese Bewerbung wurde bereits eine "
            "Förderentscheidung erfasst."
        )

    tab_bewerten, tab_stand, tab_entscheidung = st.tabs(
        [
            "Gegenstände bewerten",
            "Bearbeitungsstand",
            "Auswahlentscheidung",
        ]
    )

    with tab_stand:
        zeilen = []
        for gegenstand in liste:
            bewertung = st.session_state.demo_bewertungen.get(
                gegenstand["id"]
            )
            zeilen.append(
                {
                    "Art": gegenstand["art"],
                    "Gegenstand": gegenstand["titel"],
                    "Kriterium": gegenstand["kriterium"],
                    "Status": (
                        "Bearbeitet" if bewertung else "Offen"
                    ),
                    "Punkte": (
                        f"{bewertung['punkte']}/"
                        f"{gegenstand['max_punkte']}"
                        if bewertung else "—"
                    ),
                }
            )

        st.dataframe(zeilen, hide_index=True, width="stretch")

    with tab_bewerten:
        offen = [g for g in liste if not ist_bewertet(g)]
        bewertet = [g for g in liste if ist_bewertet(g)]

        a, b = st.columns(2)
        with a:
            st.markdown(f"**Noch offen ({len(offen)})**")
            for g in offen:
                st.write(f"○ {g['art']}: {g['titel']}")
            if not offen:
                st.write("Keine offenen Gegenstände.")

        with b:
            st.markdown(f"**Bearbeitet ({len(bewertet)})**")
            for g in bewertet:
                st.write(f"✓ {g['art']}: {g['titel']}")
            if not bewertet:
                st.write("Noch nichts bewertet.")

        st.divider()

        zuordnung = {g["id"]: g for g in liste}
        gegenstand_id = st.selectbox(
            "Unterlage oder Angabe auswählen",
            list(zuordnung),
            format_func=lambda gid: (
                ("✓ " if ist_bewertet(zuordnung[gid]) else "○ ")
                + zuordnung[gid]["art"]
                + ": "
                + zuordnung[gid]["titel"]
            ),
            key=f"gegenstand_{kennung}",
        )

        gegenstand = zuordnung[gegenstand_id]
        vorhandene_bewertung = (
            st.session_state.demo_bewertungen.get(gegenstand_id)
        )

        links, rechts = st.columns([1.2, 1], gap="large")

        with links:
            st.markdown("### Unterlage / Angabe")
            if gegenstand["art"] == "Dokument":
                st.caption(
                    "Fiktive Vorschau; keine echte PDF geladen."
                )

            st.text_area(
                "Inhalt",
                value=gegenstand["inhalt"],
                height=280,
                disabled=True,
                key=f"inhalt_{gegenstand_id}",
            )

        with rechts:
            st.markdown("### Bewertung")
            st.write(
                f"**Kriterium:** {gegenstand['kriterium']}"
            )

            if entschieden:
                st.warning(
                    "Bewertung gesperrt: Die Auswahlentscheidung "
                    "wurde bereits erfasst."
                )
                if vorhandene_bewertung:
                    st.metric(
                        "Punkte",
                        f"{vorhandene_bewertung['punkte']}/"
                        f"{gegenstand['max_punkte']}",
                    )
                    st.write(
                        "**Kommentar:** "
                        + (
                            vorhandene_bewertung["kommentar"]
                            or "Kein Kommentar"
                        )
                    )
            else:
                if vorhandene_bewertung:
                    st.info(
                        "Bereits bewertet. Du kannst dieselbe "
                        "Bewertung hier korrigieren."
                    )

                with st.form(f"bewertung_{gegenstand_id}"):
                    punkte = st.number_input(
                        "Punkte",
                        min_value=0,
                        max_value=gegenstand["max_punkte"],
                        value=(
                            vorhandene_bewertung["punkte"]
                            if vorhandene_bewertung else 0
                        ),
                        step=1,
                    )
                    kommentar = st.text_area(
                        "Kommentar",
                        value=(
                            vorhandene_bewertung["kommentar"]
                            if vorhandene_bewertung else ""
                        ),
                    )
                    speichern = st.form_submit_button(
                        "Bewertung aktualisieren"
                        if vorhandene_bewertung
                        else "Bewertung speichern",
                        type="primary",
                    )

                if speichern:
                    # Dieselbe ID wird aktualisiert: keine zweite
                    # Bewertung desselben Gegenstands entsteht.
                    st.session_state.demo_bewertungen[
                        gegenstand_id
                    ] = {
                        "punkte": int(punkte),
                        "kommentar": kommentar.strip(),
                    }
                    st.rerun()

    with tab_entscheidung:
        entscheidung_erfassen(kennung)

    st.caption(
        "UX-Prototyp: Bewertungen und Entscheidungen bleiben "
        "nur in dieser Streamlit-Sitzung."
    )


# -------------------------------------------------------------------
# Kommissions-Navigation
# -------------------------------------------------------------------

def kommissions_dashboard():
    st.sidebar.title("Auswahlkommission")
    st.sidebar.radio(
        "Navigation",
        KOMMISSION_SEITEN,
        key="kommission_seite",
        on_change=zur_trefferliste,
    )
    st.sidebar.button(
        "Zur Startseite",
        on_click=start_oeffnen,
    )

    st.caption(
        "UX-Prototyp · keine Änderungen an PostgreSQL"
    )

    if st.session_state.detail_bewerbung is not None:
        detailseite(st.session_state.detail_bewerbung)
        return

    seite = st.session_state.kommission_seite

    if seite == "Übersicht":
        st.title("Kommissions-Dashboard")

        gesamt = sum(
            len(gegenstaende(k)) for k in BEWERBUNGEN
        )
        fertig = sum(
            bearbeitungsstand(k)[0] for k in BEWERBUNGEN
        )
        geprueft = sum(
            bewertungslabel(k) == "Geprüft"
            for k in BEWERBUNGEN
        )

        a, b, c = st.columns(3)
        a.metric("Bewerbungen", len(BEWERBUNGEN))
        b.metric("Offene Gegenstände", gesamt - fertig)
        c.metric("Geprüfte Bewerbungen", geprueft)

        st.button(
            "Offene Aufgaben anzeigen →",
            on_click=kommission_oeffnen,
            args=("Bewertungsaufgaben",),
            type="primary",
        )

    elif seite in ("Bewerbungen", "Bewertungsaufgaben"):
        st.title(
            "Bewertungsaufgaben"
            if seite == "Bewertungsaufgaben"
            else "Bewerbungen"
        )
        suchseite()

    elif seite == "Rangliste":
        st.title("Interne Rangliste")
        st.info(
            "Dieser UX-Prototyp berechnet keine verbindliche "
            "Rangliste. Die echte App verwendet dafür "
            "die PostgreSQL-View."
        )

    else:
        st.title("Auswahlentscheidungen")
        st.write(
            "Öffne eine geprüfte Bewerbung, um ihre "
            "Entscheidung zu erfassen."
        )

        zeilen = []
        for kennung, daten in BEWERBUNGEN.items():
            entscheidung = (
                st.session_state.demo_entscheidungen.get(kennung)
            )
            zeilen.append(
                {
                    "Name": daten["name"],
                    "Matrikelnummer": daten["matrikel"],
                    "Bewertungsstand": bewertungslabel(kennung),
                    "Entscheidung": (
                        entscheidung["status"]
                        if entscheidung else "Noch offen"
                    ),
                }
            )

        st.dataframe(
            zeilen,
            hide_index=True,
            width="stretch",
        )


initialisieren()

if st.session_state.ux_rolle is None:
    startseite()
elif st.session_state.ux_rolle == "Registrierung":
    registrierung()
elif st.session_state.ux_rolle == "Bewerber":
    bewerber_dashboard()
elif st.session_state.ux_rolle == "Kommission":
    kommissions_dashboard()