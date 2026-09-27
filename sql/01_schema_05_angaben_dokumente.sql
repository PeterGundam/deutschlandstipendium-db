CREATE TABLE dokument (
    dokument_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bewerbungs_nr INTEGER NOT NULL
        REFERENCES bewerbung(bewerbungs_nr),
    dateiname VARCHAR(255) NOT NULL,
    dokumenttyp VARCHAR(50) NOT NULL,
    dateipfad TEXT NOT NULL
);

CREATE TABLE motivationsschreiben (
    dokument_id INTEGER PRIMARY KEY
        REFERENCES dokument(dokument_id)
);

CREATE TABLE leistungsnachweis (
    dokument_id INTEGER PRIMARY KEY
        REFERENCES dokument(dokument_id),
    durchschnittsnote NUMERIC(3, 2)
        CHECK (durchschnittsnote BETWEEN 1.00 AND 5.00)
);

CREATE TABLE engagement (
    engagement_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bewerbungs_nr INTEGER NOT NULL
        REFERENCES bewerbung(bewerbungs_nr),
    art VARCHAR(100) NOT NULL,
    beschreibung TEXT NOT NULL
);

CREATE TABLE lebensumstand (
    umstand_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bewerbungs_nr INTEGER NOT NULL
        REFERENCES bewerbung(bewerbungs_nr),
    beschreibung TEXT NOT NULL
);

CREATE TABLE auszeichnung (
    auszeichnung_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bewerbungs_nr INTEGER NOT NULL
        REFERENCES bewerbung(bewerbungs_nr),
    titel VARCHAR(200) NOT NULL,
    beschreibung TEXT
);