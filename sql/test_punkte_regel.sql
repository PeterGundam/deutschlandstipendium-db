BEGIN;

DO $$
DECLARE
    v_student INTEGER;
    v_mitglied INTEGER;
    v_fakultaet INTEGER;
    v_studiengang INTEGER;
    v_stipendium INTEGER;
    v_zeitraum INTEGER;
    v_bewerbung INTEGER;
    v_bewertung INTEGER;
    v_kriterium INTEGER;
    v_punkte INTEGER;
    v_abgelehnt BOOLEAN := FALSE;
    v_fremdes_kriterium INTEGER;
    v_fremdes_abgelehnt BOOLEAN := FALSE;
    v_engagement INTEGER;
BEGIN
    -- Nur die Datensätze anlegen, die eine Bewertung benötigt.
    INSERT INTO fakultaet (name) VALUES ('Testfakultaet')
    RETURNING fakultaet_id INTO v_fakultaet;

    INSERT INTO studiengang (name, fakultaet_id)
    VALUES ('Teststudiengang', v_fakultaet)
    RETURNING studiengang_id INTO v_studiengang;

    INSERT INTO person (vorname, nachname) VALUES ('Test', 'Student')
    RETURNING personen_id INTO v_student;

    INSERT INTO studierender
        (personen_id, matrikel_nr, email, fachsemester, studiengang_id)
    VALUES
        (v_student, 'TEST-PUNKTE-001', 'test@example.invalid', 1, v_studiengang);

    INSERT INTO person (vorname, nachname) VALUES ('Test', 'Mitglied')
    RETURNING personen_id INTO v_mitglied;

    INSERT INTO kommissionsmitglied (personen_id, rolle)
    VALUES (v_mitglied, 'Gutachter');

    INSERT INTO stipendium (bezeichnung, foerderbetrag)
    VALUES ('Teststipendium', 300.00)
    RETURNING stipendium_id INTO v_stipendium;

    INSERT INTO bewerbungszeitraum (stipendium_id, beginn, ende)
    VALUES (v_stipendium, CURRENT_DATE - 1, CURRENT_DATE + 1)
    RETURNING zeitraum_id INTO v_zeitraum;

    INSERT INTO bewerbung (studierenden_id, zeitraum_id)
    VALUES (v_student, v_zeitraum)
    RETURNING bewerbungs_nr INTO v_bewerbung;

        -- Schritt 2: Gegenstand anlegen, der bewertet werden soll
    INSERT INTO engagement (bewerbungs_nr, art, beschreibung)
    VALUES (v_bewerbung, 'Ehrenamt', 'Testgegenstand für die Punkteprüfung')
    RETURNING engagement_id INTO v_engagement;

    -- Schritt 3: Bewertung diesem Engagement zuordnen
    INSERT INTO bewertung (bewerbungs_nr, mitglied_id, engagement_id)
    VALUES (v_bewerbung, v_mitglied, v_engagement)
    RETURNING bewertung_id INTO v_bewertung;

    INSERT INTO bewertungskriterium (name, max_punkte)
    VALUES ('Testkriterium', 10)
    RETURNING kriterium_id INTO v_kriterium;
    INSERT INTO zeitraum_kriterium (zeitraum_id, kriterium_id, gewichtung)
    VALUES (v_zeitraum, v_kriterium, 1.00);

    -- Gültiger Fall: 7 von maximal 10 Punkten.
    INSERT INTO bewertungspunkt (bewertung_id, kriterium_id, punkte)
    VALUES (v_bewertung, v_kriterium, 7);
    INSERT INTO bewertungskriterium (name, max_punkte)
    VALUES ('Nicht zugeordnetes Testkriterium', 10)
    RETURNING kriterium_id INTO v_fremdes_kriterium;

    BEGIN
        INSERT INTO bewertungspunkt (bewertung_id, kriterium_id, punkte)
        VALUES (v_bewertung, v_fremdes_kriterium, 5);
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM NOT LIKE
        'Kriterium % gehört nicht zum Bewerbungszeitraum dieser Bewertung' THEN
            RAISE;
        END IF;
        v_fremdes_abgelehnt := TRUE;
    END;

IF NOT v_fremdes_abgelehnt THEN
    RAISE EXCEPTION
        'TEST FEHLGESCHLAGEN: Nicht zugeordnetes Kriterium wurde akzeptiert';
END IF;


    -- Ungültiger Fall: Änderung auf 11 Punkte muss scheitern.
    BEGIN
        UPDATE bewertungspunkt
        SET punkte = 11
        WHERE bewertung_id = v_bewertung
          AND kriterium_id = v_kriterium;
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM NOT LIKE 'Punkte (11) überschreiten das Maximum (10)%' THEN
            RAISE;
        END IF;
        v_abgelehnt := TRUE;
    END;

    IF NOT v_abgelehnt THEN
        RAISE EXCEPTION 'TEST FEHLGESCHLAGEN: 11 Punkte wurden akzeptiert';
    END IF;

    SELECT punkte INTO v_punkte
    FROM bewertungspunkt
    WHERE bewertung_id = v_bewertung
      AND kriterium_id = v_kriterium;

    IF v_punkte <> 7 THEN
        RAISE EXCEPTION 'TEST FEHLGESCHLAGEN: Gespeicherte Punkte sind % statt 7',
            v_punkte;
    END IF;

    RAISE NOTICE 'TEST BESTANDEN: 7 akzeptiert, 11 abgelehnt, Wert bleibt 7';
END;
$$;

ROLLBACK;