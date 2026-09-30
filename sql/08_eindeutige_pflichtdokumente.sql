    CREATE UNIQUE INDEX dokument_ein_motivationsschreiben_pro_bewerbung
    ON dokument (bewerbungs_nr)
    WHERE dokumenttyp = 'Motivationsschreiben';

    CREATE UNIQUE INDEX dokument_ein_leistungsnachweis_pro_bewerbung
    ON dokument (bewerbungs_nr)
    WHERE dokumenttyp = 'Leistungsnachweis';
    psql -h localhost -U stipendium_user -d stipendium_db -W \
      -v ON_ERROR_STOP=1 -1 -f sql/08_eindeutige_pflichtdokumente.sql


