
CREATE TABLE studierender (
    personen_id INTEGER PRIMARY KEY REFERENCES person(personen_id),
    matrikel_nr VARCHAR(30) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL,
    fachsemester INTEGER NOT NULL CHECK (fachsemester >= 1),
    studiengang_id INTEGER NOT NULL REFERENCES studiengang(studiengang_id)
);

CREATE TABLE kommissionsmitglied (
    personen_id INTEGER PRIMARY KEY REFERENCES person(personen_id),
    rolle VARCHAR(100) NOT NULL
);