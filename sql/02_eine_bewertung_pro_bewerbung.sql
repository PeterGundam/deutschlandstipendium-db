ALTER TABLE bewertung
ADD CONSTRAINT bewertung_einmal_pro_bewerbung
UNIQUE (bewerbungs_nr);