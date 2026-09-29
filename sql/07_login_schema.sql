CREATE TABLE login_konto (
    konto_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    personen_id INTEGER NOT NULL UNIQUE
        REFERENCES person(personen_id),
    email TEXT NOT NULL,
    passwort_hash TEXT NOT NULL,
    aktiv BOOLEAN NOT NULL DEFAULT TRUE,
    angelegt_am TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT login_email_nicht_leer
        CHECK (length(trim(email)) > 0)
);

-- Verhindert doppelte Login-E-Mails auch bei unterschiedlicher
-- Groß-/Kleinschreibung.
CREATE UNIQUE INDEX login_konto_email_eindeutig
ON login_konto (lower(email));