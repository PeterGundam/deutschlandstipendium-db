    CREATE OR REPLACE FUNCTION pruefe_bewertungspunkte()
    RETURNS TRIGGER AS $$
    DECLARE
        erlaubtes_maximum INTEGER;
    BEGIN
        -- Ist das Kriterium für den Zeitraum dieser Bewerbung vorgesehen?
        IF NOT EXISTS (
            SELECT 1
            FROM bewertung b
            JOIN bewerbung bew
              ON bew.bewerbungs_nr = b.bewerbungs_nr
            JOIN zeitraum_kriterium zk
              ON zk.zeitraum_id = bew.zeitraum_id
            WHERE b.bewertung_id = NEW.bewertung_id
              AND zk.kriterium_id = NEW.kriterium_id
        ) THEN
            RAISE EXCEPTION
                'Kriterium % gehört nicht zum Bewerbungszeitraum dieser Bewertung',
                NEW.kriterium_id;
        END IF;

        -- Bisherige Regel: Punkte dürfen max_punkte nicht überschreiten.
        SELECT max_punkte
          INTO erlaubtes_maximum
          FROM bewertungskriterium
         WHERE kriterium_id = NEW.kriterium_id
         FOR SHARE;

        IF erlaubtes_maximum IS NOT NULL
           AND NEW.punkte > erlaubtes_maximum THEN
            RAISE EXCEPTION
                'Punkte (%) überschreiten das Maximum (%) für Kriterium %',
                NEW.punkte, erlaubtes_maximum, NEW.kriterium_id;
        END IF;

        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    DROP TRIGGER IF EXISTS bewertungspunkt_maximum_pruefen ON bewertungspunkt;

    CREATE TRIGGER bewertungspunkt_maximum_pruefen
    BEFORE INSERT OR UPDATE OF bewertung_id, kriterium_id, punkte
    ON bewertungspunkt
    FOR EACH ROW
    EXECUTE FUNCTION pruefe_bewertungspunkte();

