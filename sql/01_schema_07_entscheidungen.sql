CREATE TABLE auswahlentscheidung (
    entscheidungs_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bewerbungs_nr INTEGER NOT NULL UNIQUE
        REFERENCES bewerbung(bewerbungs_nr),
    foerderstatus VARCHAR(30) NOT NULL
        CHECK (foerderstatus IN ('Bewilligt', 'Warteliste', 'Abgelehnt')),
    entscheidungsdatum DATE NOT NULL DEFAULT CURRENT_DATE,
    begruendung TEXT
);

CREATE TABLE entscheidungsbeteiligung (
    entscheidungs_id INTEGER NOT NULL
        REFERENCES auswahlentscheidung(entscheidungs_id),
    mitglied_id INTEGER NOT NULL
        REFERENCES kommissionsmitglied(personen_id),
    PRIMARY KEY (entscheidungs_id, mitglied_id)
);

CREATE TABLE benachrichtigung (
    benachrichtigungs_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bewerbungs_nr INTEGER NOT NULL
        REFERENCES bewerbung(bewerbungs_nr),
    datum TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    typ VARCHAR(100) NOT NULL,
    sendestatus VARCHAR(30) NOT NULL DEFAULT 'Ausstehend'
);

CREATE TABLE audit_log (
    log_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    mitglied_id INTEGER NOT NULL
        REFERENCES kommissionsmitglied(personen_id),
    bewertung_id INTEGER
        REFERENCES bewertung(bewertung_id),
    entscheidungs_id INTEGER
        REFERENCES auswahlentscheidung(entscheidungs_id),
    zeitstempel TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    aktion VARCHAR(100) NOT NULL,
    alter_wert TEXT,
    neuer_wert TEXT,
    CONSTRAINT audit_log_genau_ein_bezug
        CHECK (num_nonnulls(bewertung_id, entscheidungs_id) = 1)
);