DO $$
DECLARE
    v_zeitraum_id INTEGER;
    v_mitglied_id INTEGER;
    v_kriterium_id INTEGER;
    v_studiengang_id INTEGER;
    v_personen_id INTEGER;
    v_bewerbungs_nr INTEGER;
    v_bewertung_id INTEGER;
    kandidat RECORD;
BEGIN
    -- Zeitraum, Kommissionsmitglied und Kriterium aus der vorhandenen
    -- Beispielbewertung von Lena ermitteln.
    SELECT b.zeitraum_id, bw.mitglied_id, bp.kriterium_id, s.studiengang_id
    INTO v_zeitraum_id, v_mitglied_id, v_kriterium_id, v_studiengang_id
    FROM studierender s
    JOIN bewerbung b
      ON b.studierenden_id = s.personen_id
    JOIN bewertung bw
      ON bw.bewerbungs_nr = b.bewerbungs_nr
    JOIN bewertungspunkt bp
      ON bp.bewertung_id = bw.bewertung_id
    JOIN bewertungskriterium k
      ON k.kriterium_id = bp.kriterium_id
    WHERE s.matrikel_nr = 'DEMO-1001'
      AND k.name = 'Engagement'
    LIMIT 1;

    IF v_zeitraum_id IS NULL THEN
        RAISE EXCEPTION
            'Die Beispielbewerbung DEMO-1001 mit Engagement-Bewertung fehlt';
    END IF;

    -- Schutz gegen versehentliches mehrfaches Ausführen.
    IF EXISTS (
        SELECT 1
        FROM studierender
        WHERE matrikel_nr IN ('DEMO-1002', 'DEMO-1003')
    ) THEN
        RAISE EXCEPTION
            'Erweiterte Beispieldaten sind bereits vorhanden';
    END IF;

    FOR kandidat IN
        SELECT *
        FROM (VALUES
            ('DEMO-1002', 'Noah', 'Testmann',
             'noah@example.invalid', 'noah.testmann', 6),
            ('DEMO-1003', 'Sofia', 'Mustermann',
             'sofia@example.invalid', 'sofia.mustermann', 9)
        ) AS daten(matrikel_nr, vorname, nachname, email, benutzername, punkte)
    LOOP
        INSERT INTO person (vorname, nachname)
        VALUES (kandidat.vorname, kandidat.nachname)
        RETURNING personen_id INTO v_personen_id;

        INSERT INTO studierender
            (personen_id, matrikel_nr, email, fachsemester, studiengang_id)
        VALUES
            (v_personen_id, kandidat.matrikel_nr, kandidat.email,
             4, v_studiengang_id);

        INSERT INTO hochschulaccount (benutzername, studierenden_id)
        VALUES (kandidat.benutzername, v_personen_id);

        INSERT INTO bewerbung
            (studierenden_id, zeitraum_id, erstellungsdatum,
             eingangsdatum, status)
        VALUES
            (v_personen_id, v_zeitraum_id,
             CURRENT_DATE - 20, CURRENT_DATE - 19, 'Eingereicht')
        RETURNING bewerbungs_nr INTO v_bewerbungs_nr;

        INSERT INTO engagement (bewerbungs_nr, art, beschreibung)
        VALUES
            (v_bewerbungs_nr, 'Ehrenamt',
             'Beispielangabe für den Vergleich von Bewerbungen');

        INSERT INTO bewertung
            (bewerbungs_nr, mitglied_id, status, kommentar)
        VALUES
            (v_bewerbungs_nr, v_mitglied_id,
             'abgeschlossen', 'Beispielbewertung für das Projekt')
        RETURNING bewertung_id INTO v_bewertung_id;

        INSERT INTO bewertungspunkt (bewertung_id, kriterium_id, punkte)
        VALUES (v_bewertung_id, v_kriterium_id, kandidat.punkte);
    END LOOP;
END;
$$;