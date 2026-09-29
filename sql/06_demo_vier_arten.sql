DO $$
DECLARE
    v_bewerbung INTEGER;
    v_zeitraum INTEGER;
    v_mitglied INTEGER;

    v_dokument INTEGER;
    v_umstand INTEGER;
    v_auszeichnung INTEGER;
    v_bewertung INTEGER;

    v_k_leistung INTEGER;
    v_k_umstand INTEGER;
    v_k_auszeichnung INTEGER;
BEGIN
    -- Nur für den vorhandenen Demodatensatz von Sofia ausführen.
    SELECT b.bewerbungs_nr, b.zeitraum_id
      INTO STRICT v_bewerbung, v_zeitraum
    FROM bewerbung b
    JOIN studierender s ON s.personen_id = b.studierenden_id
    WHERE s.matrikel_nr = 'DEMO-1003';

    -- Schutz vor versehentlichem zweitem Ausführen.
    IF EXISTS (
        SELECT 1
        FROM dokument
        WHERE bewerbungs_nr = v_bewerbung
          AND dateiname = 'DEMO-1003-leistungsnachweis.pdf'
    ) THEN
        RAISE EXCEPTION 'Die erweiterten Sofiadaten sind bereits vorhanden';
    END IF;

    -- Ein weiteres Kommissionsmitglied bewertet die neuen Gegenstände.
    INSERT INTO person (vorname, nachname)
    VALUES ('Timo', 'Demo')
    RETURNING personen_id INTO v_mitglied;

    INSERT INTO kommissionsmitglied (personen_id, rolle)
    VALUES (v_mitglied, 'Gutachter');

    -- Die neuen Kriterien für Sofias Bewerbungszeitraum festlegen.
    -- Gewichtung 1.00 ist hier bewusst nur eine einfache Demo.
    INSERT INTO bewertungskriterium (name, max_punkte)
    VALUES ('Studienleistung', 10)
    RETURNING kriterium_id INTO v_k_leistung;

    INSERT INTO bewertungskriterium (name, max_punkte)
    VALUES ('Lebensumstände', 10)
    RETURNING kriterium_id INTO v_k_umstand;

    INSERT INTO bewertungskriterium (name, max_punkte)
    VALUES ('Auszeichnungen', 10)
    RETURNING kriterium_id INTO v_k_auszeichnung;

    INSERT INTO zeitraum_kriterium (zeitraum_id, kriterium_id, gewichtung)
    VALUES
        (v_zeitraum, v_k_leistung, 1.00),
        (v_zeitraum, v_k_umstand, 1.00),
        (v_zeitraum, v_k_auszeichnung, 1.00);

    -- 1. Dokument als Bewertungsgegenstand
    INSERT INTO dokument
        (bewerbungs_nr, dateiname, dokumenttyp, dateipfad)
    VALUES
        (v_bewerbung, 'DEMO-1003-leistungsnachweis.pdf',
         'Leistungsnachweis',
         'DEMO_KEINE_ECHTE_DATEI/DEMO-1003-leistungsnachweis.pdf')
    RETURNING dokument_id INTO v_dokument;

    INSERT INTO leistungsnachweis (dokument_id, durchschnittsnote)
    VALUES (v_dokument, 1.70);

    INSERT INTO bewertung
        (bewerbungs_nr, mitglied_id, dokument_id, status, kommentar)
    VALUES
        (v_bewerbung, v_mitglied, v_dokument,
         'abgeschlossen', 'Fiktiver Leistungsnachweis')
    RETURNING bewertung_id INTO v_bewertung;

    INSERT INTO bewertungspunkt (bewertung_id, kriterium_id, punkte)
    VALUES (v_bewertung, v_k_leistung, 7);

    -- 2. Lebensumstand als Bewertungsgegenstand
    INSERT INTO lebensumstand (bewerbungs_nr, beschreibung)
    VALUES (v_bewerbung, 'Fiktive Demoangabe zu besonderen Umständen')
    RETURNING umstand_id INTO v_umstand;

    INSERT INTO bewertung
        (bewerbungs_nr, mitglied_id, umstand_id, status, kommentar)
    VALUES
        (v_bewerbung, v_mitglied, v_umstand,
         'abgeschlossen', 'Fiktive Demoangabe')
    RETURNING bewertung_id INTO v_bewertung;

    INSERT INTO bewertungspunkt (bewertung_id, kriterium_id, punkte)
    VALUES (v_bewertung, v_k_umstand, 5);

    -- 3. Auszeichnung als Bewertungsgegenstand
    INSERT INTO auszeichnung (bewerbungs_nr, titel, beschreibung)
    VALUES
        (v_bewerbung, 'Fiktiver Projektpreis',
         'Auszeichnung ausschließlich für die Projektdemo')
    RETURNING auszeichnung_id INTO v_auszeichnung;

    INSERT INTO bewertung
        (bewerbungs_nr, mitglied_id, auszeichnung_id, status, kommentar)
    VALUES
        (v_bewerbung, v_mitglied, v_auszeichnung,
         'abgeschlossen', 'Fiktive Auszeichnung')
    RETURNING bewertung_id INTO v_bewertung;

    INSERT INTO bewertungspunkt (bewertung_id, kriterium_id, punkte)
    VALUES (v_bewertung, v_k_auszeichnung, 4);
END;
$$;