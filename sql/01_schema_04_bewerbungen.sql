CREATE TABLE finanzierung (
    foerderer_id INTEGER NOT NULL REFERENCES foerderer(foerderer_id),
    stipendium_id INTEGER NOT NULL REFERENCES stipendium(stipendium_id),
    finanzierungsbetrag NUMERIC(10, 2)
        CHECK (finanzierungsbetrag > 0),
    PRIMARY KEY (foerderer_id, stipendium_id)
);

CREATE TABLE bewerbung (
    bewerbungs_nr INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    studierenden_id INTEGER NOT NULL
        REFERENCES studierender(personen_id),
    zeitraum_id INTEGER NOT NULL
        REFERENCES bewerbungszeitraum(zeitraum_id),
    erstellungsdatum DATE NOT NULL DEFAULT CURRENT_DATE,
    eingangsdatum DATE,
    status VARCHAR(30) NOT NULL DEFAULT 'Entwurf',
    UNIQUE (studierenden_id, zeitraum_id)
);psql -h localhost -U stipendium_user -d stipendium_db -W \
  -v ON_ERROR_STOP=1 -1 -f sql/01_schema_04_bewerbungen.sql