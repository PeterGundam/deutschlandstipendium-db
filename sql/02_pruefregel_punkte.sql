CREATE OR REPLACE FUNCTION pruefe_bewertungspunkte()
RETURNS TRIGGER AS $$
DECLARE
    erlaubtes_maximum INTEGER;
BEGIN
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

CREATE TRIGGER bewertungspunkt_maximum_pruefen
BEFORE INSERT OR UPDATE OF punkte, kriterium_id
ON bewertungspunkt
FOR EACH ROW
EXECUTE FUNCTION pruefe_bewertungspunkte();