CREATE TABLE dokumentbeleg (
    dokument_id INTEGER PRIMARY KEY
        REFERENCES dokument(dokument_id),
    engagement_id INTEGER
        REFERENCES engagement(engagement_id),
    umstand_id INTEGER
        REFERENCES lebensumstand(umstand_id),
    auszeichnung_id INTEGER
        REFERENCES auszeichnung(auszeichnung_id),

    CONSTRAINT dokumentbeleg_genau_eine_angabe
        CHECK (num_nonnulls(
            engagement_id,
            umstand_id,
            auszeichnung_id
        ) = 1)
);