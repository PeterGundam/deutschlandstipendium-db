BEGIN;

DO $$
DECLARE
    v_stipendium_id INTEGER;
    v_student_1 INTEGER;
    v_student_2 INTEGER;
    v_zeitraum INTEGER;
    v_bewerbung_1 INTEGER;
    v_bewerbung_2 INTEGER;
    v_bewilligt INTEGER;
    v_abgelehnt BOOLEAN := FALSE;
BEGIN
    -- Vorhandenes Demo-Stipendium und zwei Demo-Studierende verwenden.
    SELECT bz.stipendium_id INTO STRICT v_stipendium_id
    FROM bewerbung b
    JOIN studierender s ON s.personen_id = b.studierenden_id
    JOIN bewerbungszeitraum bz ON bz.zeitraum_id = b.zeitraum_id
    WHERE s.matrikel_nr = 'DEMO-1001'
    ORDER BY b.bewerbungs_nr
    LIMIT 1;

    SELECT personen_id INTO STRICT v_student_1
    FROM studierender WHERE matrikel_nr = 'DEMO-1001';

    SELECT personen_id INTO STRICT v_student_2
    FROM studierender WHERE matrikel_nr = 'DEMO-1002';

    -- Neuer Testzeitraum: gestern abgelaufen, genau ein Förderplatz.
    INSERT INTO bewerbungszeitraum
        (stipendium_id, beginn, ende, max_foerderplaetze)
    VALUES
        (v_stipendium_id, CURRENT_DATE - 3, CURRENT_DATE - 1, 1)
    RETURNING zeitraum_id INTO v_zeitraum;

    INSERT INTO bewerbung
        (studierenden_id, zeitraum_id, status, eingangsdatum)
    VALUES
        (v_student_1, v_zeitraum, 'Eingereicht', CURRENT_DATE - 2)
    RETURNING bewerbungs_nr INTO v_bewerbung_1;

    INSERT INTO bewerbung
        (studierenden_id, zeitraum_id, status, eingangsdatum)
    VALUES
        (v_student_2, v_zeitraum, 'Eingereicht', CURRENT_DATE - 2)
    RETURNING bewerbungs_nr INTO v_bewerbung_2;

    -- TEST 1: Eine Bewilligung NACH Ablauf der Frist muss funktionieren.
    INSERT INTO auswahlentscheidung
        (bewerbungs_nr, foerderstatus, begruendung)
    VALUES
        (v_bewerbung_1, 'Bewilligt', 'Temporärer Fristtest');

    RAISE NOTICE
        'TEST 1 BESTANDEN: Entscheidung nach Fristablauf akzeptiert';

    -- TEST 2: Der einzige Platz ist belegt. Zweite Bewilligung
    -- muss durch den Trigger abgelehnt werden.
    BEGIN
        INSERT INTO auswahlentscheidung
            (bewerbungs_nr, foerderstatus, begruendung)
        VALUES
            (v_bewerbung_2, 'Bewilligt', 'Muss abgelehnt werden');
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM NOT LIKE 'Keine freien Förderplätze:%' THEN
            RAISE;
        END IF;
        v_abgelehnt := TRUE;
    END;

    IF NOT v_abgelehnt THEN
        RAISE EXCEPTION
            'TEST 2 FEHLGESCHLAGEN: Zweite Bewilligung wurde akzeptiert';
    END IF;

    SELECT COUNT(*) INTO v_bewilligt
    FROM auswahlentscheidung a
    JOIN bewerbung b ON b.bewerbungs_nr = a.bewerbungs_nr
    WHERE b.zeitraum_id = v_zeitraum
      AND a.foerderstatus = 'Bewilligt';

    IF v_bewilligt <> 1 THEN
        RAISE EXCEPTION
            'TEST 2 FEHLGESCHLAGEN: Erwartet 1 Bewilligung, gefunden %',
            v_bewilligt;
    END IF;

    RAISE NOTICE
        'TEST 2 BESTANDEN: Zweite Bewilligung abgelehnt; es bleibt bei 1 von 1 Plätzen';
END;
$$;

ROLLBACK;