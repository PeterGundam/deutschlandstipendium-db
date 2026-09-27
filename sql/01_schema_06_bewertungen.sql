CREATE TABLE bewertungskriterium (
    kriterium_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    max_punkte INTEGER NOT NULL CHECK (max_punkte > 0)
);

CREATE TABLE zeitraum_kriterium (
    zeitraum_id INTEGER NOT NULL
        REFERENCES bewerbungszeitraum(zeitraum_id),
    kriterium_id INTEGER NOT NULL
        REFERENCES bewertungskriterium(kriterium_id),
    gewichtung NUMERIC(5, 2) NOT NULL CHECK (gewichtung > 0),
    PRIMARY KEY (zeitraum_id, kriterium_id)
);

CREATE TABLE bewertung (
    bewertung_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bewerbungs_nr INTEGER NOT NULL
        REFERENCES bewerbung(bewerbungs_nr),
    mitglied_id INTEGER NOT NULL
        REFERENCES kommissionsmitglied(personen_id),
    bewertungsdatum DATE NOT NULL DEFAULT CURRENT_DATE,
    status VARCHAR(30) NOT NULL DEFAULT 'Entwurf',
    kommentar TEXT,
    UNIQUE (bewerbungs_nr, mitglied_id)
);

CREATE TABLE bewertungspunkt (
    bewertung_id INTEGER NOT NULL
        REFERENCES bewertung(bewertung_id),
    kriterium_id INTEGER NOT NULL
        REFERENCES bewertungskriterium(kriterium_id),
    punkte INTEGER NOT NULL CHECK (punkte >= 0),
    PRIMARY KEY (bewertung_id, kriterium_id)
);