BEGIN;

DO $$
DECLARE
    v_sofias_bewerbung INTEGER;
    v_mitglied INTEGER;
    v_entscheidung INTEGER;
BEGIN
    -- Für jede der drei Demobewerbungen ein Testdokument anlegen.
    WITH neue_dokumente AS (
        INSERT INTO dokument
            (bewerbungs_nr, dateiname, dokumenttyp, dateipfad)
        SELECT b.bewerbungs_nr,
               s.matrikel_nr || '-motivation.pdf',
               'Motivationsschreiben',
               '/demo/' || s.matrikel_nr || '-motivation.pdf'
        FROM bewerbung b
        JOIN studierender s
          ON s.personen_id = b.studierenden_id
        WHERE s.matrikel_nr IN ('DEMO-1001', 'DEMO-1002', 'DEMO-1003')
        RETURNING dokument_id
    )
    INSERT INTO motivationsschreiben (dokument_id)
    SELECT dokument_id FROM neue_dokumente;

    -- Nur für diesen Test gelten die drei Bewerbungen als abgeschlossen.
    UPDATE bewerbung b
    SET status = 'Abgeschlossen'
    FROM studierender s
    WHERE s.personen_id = b.studierenden_id
      AND s.matrikel_nr IN ('DEMO-1001', 'DEMO-1002', 'DEMO-1003');

    -- Sofia erhält testweise eine Entscheidung.
    SELECT b.bewerbungs_nr, bw.mitglied_id
      INTO STRICT v_sofias_bewerbung, v_mitglied
    FROM bewerbung b
    JOIN studierender s
      ON s.personen_id = b.studierenden_id
    JOIN bewertung bw
      ON bw.bewerbungs_nr = b.bewerbungs_nr
    WHERE s.matrikel_nr = 'DEMO-1003';

    INSERT INTO auswahlentscheidung (bewerbungs_nr, foerderstatus)
    VALUES (v_sofias_bewerbung, 'Bewilligt')
    RETURNING entscheidungs_id INTO v_entscheidung;

    INSERT INTO entscheidungsbeteiligung (entscheidungs_id, mitglied_id)
    VALUES (v_entscheidung, v_mitglied);
END;
$$;

\echo 'TEST: Dokumente'
SELECT b.bewerbungs_nr, d.dokument_id, d.dateiname, d.dokumenttyp
FROM bewerbung b
JOIN dokument d ON d.bewerbungs_nr = b.bewerbungs_nr
JOIN studierender s ON s.personen_id = b.studierenden_id
WHERE s.matrikel_nr IN ('DEMO-1001', 'DEMO-1002', 'DEMO-1003')
ORDER BY b.bewerbungs_nr;

\echo 'TEST: Rangliste'
SELECT position, matrikel_nr, gesamt_score
FROM rangliste
WHERE matrikel_nr IN ('DEMO-1001', 'DEMO-1002', 'DEMO-1003')
ORDER BY position;

\echo 'TEST: Entscheidung'
SELECT s.matrikel_nr, a.foerderstatus,
       COUNT(eb.mitglied_id) AS anzahl_beteiligte
FROM auswahlentscheidung a
JOIN bewerbung b ON b.bewerbungs_nr = a.bewerbungs_nr
JOIN studierender s ON s.personen_id = b.studierenden_id
LEFT JOIN entscheidungsbeteiligung eb
  ON eb.entscheidungs_id = a.entscheidungs_id
WHERE s.matrikel_nr = 'DEMO-1003'
GROUP BY s.matrikel_nr, a.entscheidungs_id, a.foerderstatus;

ROLLBACK;