CREATE TABLE hochschulaccount (
    account_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    benutzername VARCHAR(100) NOT NULL UNIQUE,
    studierenden_id INTEGER NOT NULL UNIQUE
        REFERENCES studierender(personen_id)
);

CREATE TABLE foerderer (
    foerderer_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(200) NOT NULL
);

CREATE TABLE stipendium (
    stipendium_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bezeichnung VARCHAR(200) NOT NULL,
    foerderbetrag NUMERIC(10, 2) NOT NULL CHECK (foerderbetrag > 0)
);

CREATE TABLE bewerbungszeitraum (
    zeitraum_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    stipendium_id INTEGER NOT NULL REFERENCES stipendium(stipendium_id),
    beginn DATE NOT NULL,
    ende DATE NOT NULL,
    CHECK (beginn < ende)
);