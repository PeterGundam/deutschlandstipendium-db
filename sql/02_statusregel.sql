ALTER TABLE bewerbung
ADD CONSTRAINT bewerbung_status_gueltig
CHECK (status IN (
    'Entwurf',
    'Eingereicht',
    'In_Pruefung',
    'Abgeschlossen'
));