
CREATE OR REPLACE VIEW rangliste AS
WITH scores AS (
    SELECT
        b.bewerbungs_nr,
        b.zeitraum_id,
        s.matrikel_nr,
        p.vorname,
        p.nachname,
        SUM(bp.punkte * zk.gewichtung) AS gesamt_score
    FROM bewerbung b
    JOIN studierender s
        ON s.personen_id = b.studierenden_id
    JOIN person p
        ON p.personen_id = s.personen_id
    JOIN bewertung bw
        ON bw.bewerbungs_nr = b.bewerbungs_nr
       AND bw.status = 'abgeschlossen'
    JOIN bewertungspunkt bp
        ON bp.bewertung_id = bw.bewertung_id
    JOIN zeitraum_kriterium zk
        ON zk.zeitraum_id = b.zeitraum_id
       AND zk.kriterium_id = bp.kriterium_id
    WHERE b.status = 'Abgeschlossen'
    GROUP BY
        b.bewerbungs_nr,
        b.zeitraum_id,
        s.matrikel_nr,
        p.vorname,
        p.nachname
)
SELECT
    zeitraum_id,
    RANK() OVER (
        PARTITION BY zeitraum_id
        ORDER BY gesamt_score DESC
    ) AS position,
    bewerbungs_nr,
    matrikel_nr,
    vorname,
    nachname,
    gesamt_score
FROM scores;