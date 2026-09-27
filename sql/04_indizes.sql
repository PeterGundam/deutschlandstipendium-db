-- Unterstützt die Suche nach allen Bewertungen einer Bewerbung,
-- z. B. bei der Berechnung des Gesamtscores (Abfrage 6).
CREATE INDEX IF NOT EXISTS idx_bewertung_bewerbungs_nr
ON bewertung (bewerbungs_nr);

-- Unterstützt das Abrufen der Dokumente einer Bewerbung (Abfrage 3).
CREATE INDEX IF NOT EXISTS idx_dokument_bewerbungs_nr
ON dokument (bewerbungs_nr);