-- Förderplätze werden pro Bewerbungszeitraum festgelegt.
-- 25 ist nur der Standardwert, kein festes Limit für alle Zeiträume.
ALTER TABLE bewerbungszeitraum
    ADD COLUMN IF NOT EXISTS max_foerderplaetze INTEGER;

ALTER TABLE bewerbungszeitraum
    ALTER COLUMN max_foerderplaetze SET DEFAULT 25;

UPDATE bewerbungszeitraum
SET max_foerderplaetze = 25
WHERE max_foerderplaetze IS NULL;

ALTER TABLE bewerbungszeitraum
    ALTER COLUMN max_foerderplaetze SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'bewerbungszeitraum'::regclass
          AND conname = 'bewerbungszeitraum_plaetze_positiv'
    ) THEN
        ALTER TABLE bewerbungszeitraum
            ADD CONSTRAINT bewerbungszeitraum_plaetze_positiv
            CHECK (max_foerderplaetze > 0);
    END IF;
END;
$$;


-- Neue Entscheidungen: erst NACH dem letzten Bewerbungstag.
-- Bewilligungen: höchstens max_foerderplaetze je Zeitraum.
CREATE OR REPLACE FUNCTION pruefe_entscheidung_nach_frist_und_plaetze()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_ende DATE;
    v_maximum INTEGER;
    v_bewilligt INTEGER;
BEGIN
    -- Die Zeitraumzeile wird gesperrt. Zwei gleichzeitige
    -- Bewilligungen für denselben Zeitraum werden so nacheinander geprüft.
    SELECT bz.ende, bz.max_foerderplaetze
    INTO v_ende, v_maximum
    FROM bewerbung b
    JOIN bewerbungszeitraum bz
      ON bz.zeitraum_id = b.zeitraum_id
    WHERE b.bewerbungs_nr = NEW.bewerbungs_nr
    FOR UPDATE OF bz;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Zur Bewerbung % wurde kein Bewerbungszeitraum gefunden',
            NEW.bewerbungs_nr;
    END IF;

    -- Bei ende = 30.09. ist CURRENT_DATE > ende erstmals am 01.10. wahr.
    IF CURRENT_DATE <= v_ende THEN
        RAISE EXCEPTION
            'Förderentscheidungen sind erst ab dem Tag nach dem % möglich',
            v_ende;
    END IF;

    IF NEW.foerderstatus = 'Bewilligt' THEN

        SELECT COUNT(*)
        INTO v_bewilligt
        FROM auswahlentscheidung a
        JOIN bewerbung b
          ON b.bewerbungs_nr = a.bewerbungs_nr
        WHERE b.zeitraum_id = (
            SELECT zeitraum_id
            FROM bewerbung
            WHERE bewerbungs_nr = NEW.bewerbungs_nr
        )
          AND a.foerderstatus = 'Bewilligt'
          AND (
              TG_OP = 'INSERT'
              OR a.entscheidungs_id <> NEW.entscheidungs_id
          );

        IF v_bewilligt >= v_maximum THEN
            RAISE EXCEPTION
                'Keine freien Förderplätze: % von % Plätzen sind bereits bewilligt',
                v_bewilligt, v_maximum;
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS auswahlentscheidung_frist_und_plaetze
ON auswahlentscheidung;

CREATE TRIGGER auswahlentscheidung_frist_und_plaetze
BEFORE INSERT OR UPDATE OF foerderstatus, bewerbungs_nr
ON auswahlentscheidung
FOR EACH ROW
EXECUTE FUNCTION pruefe_entscheidung_nach_frist_und_plaetze();


-- Eine spätere Änderung der Kapazität darf bereits erfolgte
-- Bewilligungen nicht ungültig machen.
CREATE OR REPLACE FUNCTION pruefe_kapazitaetsaenderung()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_bewilligt INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO v_bewilligt
    FROM auswahlentscheidung a
    JOIN bewerbung b
      ON b.bewerbungs_nr = a.bewerbungs_nr
    WHERE b.zeitraum_id = NEW.zeitraum_id
      AND a.foerderstatus = 'Bewilligt';

    IF NEW.max_foerderplaetze < v_bewilligt THEN
        RAISE EXCEPTION
            'Kapazität % liegt unter % bereits bewilligten Plätzen',
            NEW.max_foerderplaetze, v_bewilligt;
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS bewerbungszeitraum_kapazitaet_pruefen
ON bewerbungszeitraum;

CREATE TRIGGER bewerbungszeitraum_kapazitaet_pruefen
BEFORE UPDATE OF max_foerderplaetze
ON bewerbungszeitraum
FOR EACH ROW
EXECUTE FUNCTION pruefe_kapazitaetsaenderung();