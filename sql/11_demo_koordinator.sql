DO $$
DECLARE
    v_personen_id INTEGER;
BEGIN
    IF EXISTS (
        SELECT 1
        FROM person p
        JOIN kommissionsmitglied k
          ON k.personen_id = p.personen_id
        WHERE p.vorname = 'Projekt'
          AND p.nachname = 'Koordination'
          AND k.rolle = 'Koordination'
    ) THEN
        RAISE EXCEPTION 'Das Demo-Koordinatorkonto existiert bereits';
    END IF;

    INSERT INTO person (vorname, nachname)
    VALUES ('Projekt', 'Koordination')
    RETURNING personen_id INTO v_personen_id;

    INSERT INTO kommissionsmitglied (personen_id, rolle)
    VALUES (v_personen_id, 'Koordination');

    RAISE NOTICE
        'Koordinationsperson mit Personen-ID % angelegt',
        v_personen_id;
END;
$$;