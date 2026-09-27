-- 1. Bewerbungen mit Namen, Stipendium und Zeitraum (JOIN)
\echo '1. Bewerbungsübersicht'
SELECT b.bewerbungs_nr, p.vorname, p.nachname,
       s.matrikel_nr, b.status,
       st.bezeichnung AS stipendium, bz.beginn, bz.ende
FROM bewerbung b
JOIN studierender s ON s.personen_id = b.studierenden_id
JOIN person p ON p.personen_id = s.personen_id
JOIN bewerbungszeitraum bz ON bz.zeitraum_id = b.zeitraum_id
JOIN stipendium st ON st.stipendium_id = bz.stipendium_id
ORDER BY b.bewerbungs_nr;


-- 2. Anzahl der Bewerbungen je Zeitraum und Status (Aggregation)
\echo '2. Bewerbungen je Zeitraum und Status'
SELECT zeitraum_id, status, COUNT(*) AS anzahl
FROM bewerbung
GROUP BY zeitraum_id, status
ORDER BY zeitraum_id, status;


-- 3. Hochgeladene Dokumente je Bewerbung
\echo '3. Dokumente'
SELECT b.bewerbungs_nr, d.dokument_id, d.dateiname, d.dokumenttyp
FROM bewerbung b
JOIN dokument d ON d.bewerbungs_nr = b.bewerbungs_nr
ORDER BY b.bewerbungs_nr, d.dokument_id;


-- 4. Bewertungsmaßstab je Bewerbungszeitraum
\echo '4. Kriterien und Gewichtungen'
SELECT zk.zeitraum_id, k.name AS kriterium,
       k.max_punkte, zk.gewichtung
FROM zeitraum_kriterium zk
JOIN bewertungskriterium k ON k.kriterium_id = zk.kriterium_id
ORDER BY zk.zeitraum_id, k.name;


-- 5. Einzelbewertungen mit Art des bewerteten Gegenstands
\echo '5. Einzelbewertungen'
SELECT bw.bewertung_id, bw.bewerbungs_nr,
       p.vorname || ' ' || p.nachname AS mitglied,
       CASE
           WHEN bw.dokument_id IS NOT NULL THEN 'Dokument'
           WHEN bw.engagement_id IS NOT NULL THEN 'Engagement'
           WHEN bw.umstand_id IS NOT NULL THEN 'Lebensumstand'
           WHEN bw.auszeichnung_id IS NOT NULL THEN 'Auszeichnung'
       END AS gegenstandsart,
       k.name AS kriterium, bp.punkte
FROM bewertung bw
JOIN kommissionsmitglied km ON km.personen_id = bw.mitglied_id
JOIN person p ON p.personen_id = km.personen_id
JOIN bewertungspunkt bp ON bp.bewertung_id = bw.bewertung_id
JOIN bewertungskriterium k ON k.kriterium_id = bp.kriterium_id
ORDER BY bw.bewerbungs_nr, bw.bewertung_id, k.name;


-- 6. Gewichteter Gesamtscore je Bewerbung
--    Hier unabhängig vom Bewerbungsstatus, damit auch die Demodaten sichtbar sind.
\echo '6. Gesamtscores'
SELECT b.bewerbungs_nr, s.matrikel_nr,
       SUM(bp.punkte * zk.gewichtung) AS gesamt_score
FROM bewerbung b
JOIN studierender s ON s.personen_id = b.studierenden_id
JOIN bewertung bw
    ON bw.bewerbungs_nr = b.bewerbungs_nr
   AND bw.status = 'abgeschlossen'
JOIN bewertungspunkt bp ON bp.bewertung_id = bw.bewertung_id
JOIN zeitraum_kriterium zk
    ON zk.zeitraum_id = b.zeitraum_id
   AND zk.kriterium_id = bp.kriterium_id
GROUP BY b.bewerbungs_nr, s.matrikel_nr
ORDER BY gesamt_score DESC;


-- 7. Rangliste: nur abgeschlossene Bewerbungen
\echo '7. Rangliste'
SELECT zeitraum_id, position, matrikel_nr, gesamt_score
FROM rangliste
ORDER BY zeitraum_id, position;


-- 8. Bewerbungen ohne Auswahlentscheidung (Unterabfrage)
\echo '8. Noch nicht entschiedene Bewerbungen'
SELECT b.bewerbungs_nr, b.status
FROM bewerbung b
WHERE NOT EXISTS (
    SELECT 1
    FROM auswahlentscheidung a
    WHERE a.bewerbungs_nr = b.bewerbungs_nr
)
ORDER BY b.bewerbungs_nr;


-- 9. Entscheidungen und Zahl der beteiligten Mitglieder
\echo '9. Auswahlentscheidungen'
SELECT a.entscheidungs_id, a.bewerbungs_nr,
       a.foerderstatus, a.entscheidungsdatum,
       COUNT(eb.mitglied_id) AS anzahl_beteiligte
FROM auswahlentscheidung a
LEFT JOIN entscheidungsbeteiligung eb
    ON eb.entscheidungs_id = a.entscheidungs_id
GROUP BY a.entscheidungs_id
ORDER BY a.entscheidungsdatum DESC;


-- 10. Parametrisierte Suche nach Matrikelnummer
--     $1 ist ein Parameter, kein fest eingebauter Suchwert.
\echo '10. Parametrisierte Bewerbungssuche'
PREPARE suche_bewerbungen(TEXT) AS
SELECT s.matrikel_nr, b.bewerbungs_nr, b.status,
       b.erstellungsdatum, b.eingangsdatum
FROM studierender s
JOIN bewerbung b ON b.studierenden_id = s.personen_id
WHERE s.matrikel_nr = $1
ORDER BY b.bewerbungs_nr;

-- Demonstration des Parameters:
EXECUTE suche_bewerbungen('DEMO-1001');
DEALLOCATE suche_bewerbungen;