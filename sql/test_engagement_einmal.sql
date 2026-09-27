BEGIN;

DO $$
DECLARE
    v_bewertung bewertung%ROWTYPE;
    v_constraint_name TEXT;
    v_abgelehnt BOOLEAN := FALSE;
BEGIN
    SELECT bw.*
    INTO STRICT v_bewertung
    FROM bewertung bw
    JOIN bewerbung b ON b.bewerbungs_nr = bw.bewerbungs_nr
    JOIN studierender s ON s.personen_id = b.studierenden_id
    WHERE s.matrikel_nr = 'DEMO-1001';

    -- Zweite Bewertung für dasselbe Engagement versuchen.
    BEGIN
        INSERT INTO bewertung
            (bewerbungs_nr, mitglied_id, engagement_id)
        VALUES
            (v_bewertung.bewerbungs_nr,
             v_bewertung.mitglied_id,
             v_bewertung.engagement_id);
    EXCEPTION WHEN unique_violation THEN
        GET STACKED DIAGNOSTICS
            v_constraint_name = CONSTRAINT_NAME;

        IF v_constraint_name <> 'bewertung_engagement_einmal' THEN
            RAISE EXCEPTION
                'Falsche Regel hat den Datensatz abgelehnt: %',
                v_constraint_name;
        END IF;

        v_abgelehnt := TRUE;
    END;

    IF NOT v_abgelehnt THEN
        RAISE EXCEPTION
            'TEST FEHLGESCHLAGEN: Engagement wurde zweimal bewertet';
    END IF;

    RAISE NOTICE 'TEST BESTANDEN: Zweite Bewertung desselben Engagements abgelehnt';
END;
$$;

ROLLBACK;