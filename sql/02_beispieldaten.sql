DO $$
DECLARE
    v_fakultaet_id INTEGER;
    v_studiengang_id INTEGER;
    v_student_id INTEGER;
    v_mitglied_id INTEGER;
    v_stipendium_id INTEGER;
    v_zeitraum_id INTEGER;
    v_bewerbungs_nr INTEGER;
    v_kriterium_id INTEGER;
    v_bewertung_id INTEGER;
BEGIN
    INSERT INTO fakultaet (name)
    VALUES ('Fakultät für Informatik')
    RETURNING fakultaet_id INTO v_fakultaet_id;

    INSERT INTO studiengang (name, fakultaet_id)
    VALUES ('Informatik', v_fakultaet_id)
    RETURNING studiengang_id INTO v_studiengang_id;

    INSERT INTO person (vorname, nachname)
    VALUES ('Lena', 'Beispiel')
    RETURNING personen_id INTO v_student_id;

    INSERT INTO studierender
        (personen_id, matrikel_nr, email, fachsemester, studiengang_id)
    VALUES
        (v_student_id, 'DEMO-1001', 'lena@example.invalid', 3, v_studiengang_id);

    INSERT INTO hochschulaccount (benutzername, studierenden_id)
    VALUES ('lena.beispiel', v_student_id);

    INSERT INTO person (vorname, nachname)
    VALUES ('Mara', 'Muster')
    RETURNING personen_id INTO v_mitglied_id;

    INSERT INTO kommissionsmitglied (personen_id, rolle)
    VALUES (v_mitglied_id, 'Gutachterin');

    INSERT INTO stipendium (bezeichnung, foerderbetrag)
    VALUES ('Deutschlandstipendium – Demo', 300.00)
    RETURNING stipendium_id INTO v_stipendium_id;

    INSERT INTO bewerbungszeitraum (stipendium_id, beginn, ende)
    VALUES (v_stipendium_id, CURRENT_DATE - 60, CURRENT_DATE + 30)
    RETURNING zeitraum_id INTO v_zeitraum_id;

    INSERT INTO bewerbung
        (studierenden_id, zeitraum_id, erstellungsdatum, eingangsdatum, status)
    VALUES
        (v_student_id, v_zeitraum_id, CURRENT_DATE - 35,
         CURRENT_DATE - 34, 'Eingereicht')
    RETURNING bewerbungs_nr INTO v_bewerbungs_nr;

    INSERT INTO engagement (bewerbungs_nr, art, beschreibung)
    VALUES
        (v_bewerbungs_nr, 'Ehrenamt',
         'Unterstützung bei einem studentischen Lernprojekt');

    INSERT INTO bewertungskriterium (name, max_punkte)
    VALUES ('Engagement', 10)
    RETURNING kriterium_id INTO v_kriterium_id;

    -- Diese Zuordnung ist für unseren Punkte-Trigger erforderlich.
    INSERT INTO zeitraum_kriterium (zeitraum_id, kriterium_id, gewichtung)
    VALUES (v_zeitraum_id, v_kriterium_id, 1.00);

    INSERT INTO bewertung
        (bewerbungs_nr, mitglied_id, status, kommentar)
    VALUES
        (v_bewerbungs_nr, v_mitglied_id, 'abgeschlossen',
         'Engagement nachvollziehbar beschrieben')
    RETURNING bewertung_id INTO v_bewertung_id;

    INSERT INTO bewertungspunkt (bewertung_id, kriterium_id, punkte)
    VALUES (v_bewertung_id, v_kriterium_id, 8);
END;
$$;