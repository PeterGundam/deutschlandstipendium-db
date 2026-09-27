-- Eine Bewertung erhält genau einen konkreten Bewertungsgegenstand.
ALTER TABLE bewertung
    ADD COLUMN dokument_id INTEGER REFERENCES dokument(dokument_id),
    ADD COLUMN engagement_id INTEGER REFERENCES engagement(engagement_id),
    ADD COLUMN umstand_id INTEGER REFERENCES lebensumstand(umstand_id),
    ADD COLUMN auszeichnung_id INTEGER REFERENCES auszeichnung(auszeichnung_id);

-- Sicherheitsprüfung: Die folgende Zuordnung ist NUR für unsere
-- drei bekannten Demobewertungen vorgesehen.
DO $$
BEGIN
    IF (SELECT COUNT(*) FROM bewertung) <> 3
       OR EXISTS (
           SELECT 1
           FROM bewertung bw
           JOIN bewerbung b ON b.bewerbungs_nr = bw.bewerbungs_nr
           JOIN studierender s ON s.personen_id = b.studierenden_id
           WHERE s.matrikel_nr NOT IN
               ('DEMO-1001', 'DEMO-1002', 'DEMO-1003')
       )
       OR EXISTS (
           SELECT 1
           FROM bewertung bw
           WHERE (
               SELECT COUNT(*)
               FROM engagement e
               WHERE e.bewerbungs_nr = bw.bewerbungs_nr
           ) <> 1
       )
    THEN
        RAISE EXCEPTION
            'Migration gestoppt: Bewertungen entsprechen nicht den drei erwarteten Demo-Datensätzen';
    END IF;
END;
$$;

-- Jede bisherige Demobewertung dem Engagement ihrer Bewerbung zuordnen.
UPDATE bewertung bw
SET engagement_id = e.engagement_id
FROM engagement e
WHERE e.bewerbungs_nr = bw.bewerbungs_nr;

-- Genau eine der vier Gegenstands-IDs muss gesetzt sein.
ALTER TABLE bewertung
    ADD CONSTRAINT bewertung_genau_ein_gegenstand
    CHECK (num_nonnulls(
        dokument_id, engagement_id, umstand_id, auszeichnung_id
    ) = 1);

-- Jeder einzelne Gegenstand darf insgesamt nur einmal bewertet werden.
-- PostgreSQL erlaubt dabei mehrere NULL-Werte in einer UNIQUE-Spalte.
ALTER TABLE bewertung
    ADD CONSTRAINT bewertung_dokument_einmal UNIQUE (dokument_id),
    ADD CONSTRAINT bewertung_engagement_einmal UNIQUE (engagement_id),
    ADD CONSTRAINT bewertung_umstand_einmal UNIQUE (umstand_id),
    ADD CONSTRAINT bewertung_auszeichnung_einmal UNIQUE (auszeichnung_id);

-- Die alte Regel ist nun falsch: Dasselbe Mitglied darf mehrere
-- unterschiedliche Gegenstände derselben Bewerbung bewerten.
ALTER TABLE bewertung
    DROP CONSTRAINT IF EXISTS bewertung_bewerbungs_nr_mitglied_id_key,
    DROP CONSTRAINT IF EXISTS bewertung_einmal_pro_bewerbung;
    CREATE OR REPLACE FUNCTION pruefe_bewertungsgegenstand()
RETURNS TRIGGER AS $$
DECLARE
    zugehoerige_bewerbung INTEGER;
BEGIN
    IF NEW.dokument_id IS NOT NULL THEN
        SELECT bewerbungs_nr INTO zugehoerige_bewerbung
        FROM dokument WHERE dokument_id = NEW.dokument_id;
    ELSIF NEW.engagement_id IS NOT NULL THEN
        SELECT bewerbungs_nr INTO zugehoerige_bewerbung
        FROM engagement WHERE engagement_id = NEW.engagement_id;
    ELSIF NEW.umstand_id IS NOT NULL THEN
        SELECT bewerbungs_nr INTO zugehoerige_bewerbung
        FROM lebensumstand WHERE umstand_id = NEW.umstand_id;
    ELSIF NEW.auszeichnung_id IS NOT NULL THEN
        SELECT bewerbungs_nr INTO zugehoerige_bewerbung
        FROM auszeichnung WHERE auszeichnung_id = NEW.auszeichnung_id;
    END IF;

    IF zugehoerige_bewerbung IS DISTINCT FROM NEW.bewerbungs_nr THEN
        RAISE EXCEPTION
            'Bewertungsgegenstand gehört nicht zu Bewerbung %',
            NEW.bewerbungs_nr;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER bewertungsgegenstand_pruefen
BEFORE INSERT OR UPDATE OF
    bewerbungs_nr, dokument_id, engagement_id, umstand_id, auszeichnung_id
ON bewertung
FOR EACH ROW
EXECUTE FUNCTION pruefe_bewertungsgegenstand();