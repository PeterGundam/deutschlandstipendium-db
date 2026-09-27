# Datenbankprojekt: Deutschlandstipendium

## Projektziel

Wir entwickeln eine PostgreSQL-Datenbank für die Bewerbung, Bewertung und
Auswahl im Rahmen eines Stipendiums. Später kommt eine Python-/Streamlit-Anwendung
hinzu, die auf die Datenbank zugreift.

Wir arbeiten zu zweit. Jede Person kann zunächst eine eigene lokale PostgreSQL-
Datenbank betreiben und denselben Projektcode über Git teilen.

## Bisheriger Stand

- Das konzeptuelle ER-Modell wurde als Arbeitsfassung festgelegt.
- Daraus wurden 26 relationale Tabellen abgeleitet.
- Funktionale Abhängigkeiten und Normalformen wurden untersucht.
- Alle 26 Tabellen wurden auf dem ersten Rechner in PostgreSQL angelegt.
- Primärschlüssel, Fremdschlüssel und einige UNIQUE-/CHECK-Regeln sind umgesetzt.
- Ein Trigger prüft beim Einfügen oder Ändern von Bewertungspunkten:
  1. Das Kriterium gehört zum Bewerbungszeitraum der Bewerbung.
  2. Die Punkte überschreiten nicht `max_punkte` des Kriteriums.
- Ein Test hat bestätigt: 7 von 10 Punkten sind erlaubt, 11 von 10 nicht.
  Ein weiterer Test lehnt ein nicht zugeordnetes Kriterium ab.
- Testdaten werden am Testende durch `ROLLBACK` entfernt.

**Noch nicht fertig:** Beispieldaten, View, mindestens zwei begründete Indizes,
zehn SQL-Abfragen, Streamlit-Anwendung und Projektbericht.

## Voraussetzungen

- Ubuntu
- PostgreSQL (bei der bisherigen Einrichtung: Version 16)
- Python 3 und `python3-venv`
- Optional: VS Code und Git

## Lokale Python-Umgebung

Im Projektordner:

```bash
python3 -m venv DBS-Venv
source DBS-Venv/bin/activate
```

`DBS-Venv` ist eine **lokale** virtuelle Umgebung und wird nicht in Git
gespeichert. Python-Pakete installieren wir später. Die Datei `app/main.py`
ist bisher nur ein Platzhalter.

## Lokale PostgreSQL-Datenbank anlegen

Auf jedem Rechner wird eine eigene Datenbank eingerichtet. Beispiel:

```bash
sudo -u postgres createuser --login --pwprompt stipendium_user
sudo -u postgres createdb --owner=stipendium_user stipendium_db
```

Falls Benutzer oder Datenbank bereits existieren, diese Befehle **nicht
noch einmal** ausführen. Das Datenbankpasswort niemals in Git speichern oder
im Chat weitergeben.

Verbindung testen:

```bash
psql -h localhost -U stipendium_user -d stipendium_db -W \
  -c "SELECT current_user, current_database();"
```

## Projektdateien

```text
app/
  main.py                              # Spätere Streamlit-Anwendung
docs/                                  # Diagramm und Dokumentation
sql/
  01_schema.sql                        # Person, Fakultät, Studiengang
  01_schema_02_personen.sql             # Studierender, Kommissionsmitglied
  01_schema_03_stipendien.sql           # Account, Förderer, Stipendium, Zeitraum
  01_schema_04_bewerbungen.sql          # Finanzierung, Bewerbung
  01_schema_05_angaben_dokumente.sql    # Angaben und Dokumente
  01_schema_06_bewertungen.sql          # Bewertung und Kriterien
  01_schema_07_entscheidungen.sql       # Entscheidung, Nachricht, Audit-Log
  01_schema_08_dokumentbeleg.sql        # Belege zu Bewerbungsangaben
  02_statusregel.sql                    # Erlaubte Bewerbungsstatus
  02_pruefregel_punkte.sql              # Erste Version der Punkteprüfung
  02_pruefregel_zeitraum_kriterium.sql  # Erweitert die Punkteprüfung
  test_punkte_regel.sql                 # Test mit ROLLBACK
  02_beispieldaten.sql                  # Bisher leer
  03_abfragen.sql                       # Bisher leer
```

## Schema auf einer FRISCHEN, leeren Datenbank einrichten

Die Dateien müssen in dieser Reihenfolge ausgeführt werden. Vom Projektordner aus:

```bash
for datei in \
  sql/01_schema.sql \
  sql/01_schema_02_personen.sql \
  sql/01_schema_03_stipendien.sql \
  sql/01_schema_04_bewerbungen.sql \
  sql/01_schema_05_angaben_dokumente.sql \
  sql/01_schema_06_bewertungen.sql \
  sql/01_schema_07_entscheidungen.sql \
  sql/01_schema_08_dokumentbeleg.sql \
  sql/02_statusregel.sql \
  sql/02_pruefregel_punkte.sql \
  sql/02_pruefregel_zeitraum_kriterium.sql
do
  psql -h localhost -U stipendium_user -d stipendium_db -W \
    -v ON_ERROR_STOP=1 -1 -f "$datei" || break
done
```

Der Befehl fragt für jede Datei nach dem Passwort. Das ist etwas umständlich,
verhindert aber, dass wir es in einer Projektdatei speichern. `-1` führt
jeweils eine Datei als Transaktion aus; bei einem Fehler wird diese Datei
zurückgerollt. `ON_ERROR_STOP=1` stoppt bei SQL-Fehlern.

**Nicht auf einer bereits eingerichteten Datenbank erneut ausführen:**
Die `CREATE TABLE`-Dateien würden dann melden, dass die Tabellen bereits
existieren.

Tabellenanzahl prüfen:

```bash
psql -h localhost -U stipendium_user -d stipendium_db -W -t -c \
"SELECT COUNT(*) FROM information_schema.tables
 WHERE table_schema = 'public' AND table_type = 'BASE TABLE';"
```

Erwartet: `26`.

## Punkte-Test

`sql/test_punkte_regel.sql` enthält temporäre Testdaten. Das Testkriterium
muss darin vor der Punktevergabe in `zeitraum_kriterium` eingetragen werden.
Am Ende steht `ROLLBACK`.

```bash
psql -h localhost -U stipendium_user -d stipendium_db -W \
  -v ON_ERROR_STOP=1 -f sql/test_punkte_regel.sql
```

Erwartet: `NOTICE: TEST BESTANDEN`, `DO` und `ROLLBACK`, aber kein `ERROR`.

## Bekannte offene Konsistenzregeln

Das Schema erzwingt noch **nicht alle** fachlichen Regeln:

- Ein Belegdokument und die belegte Angabe müssen zur selben Bewerbung gehören.
- Ein späteres Senken von `max_punkte` könnte bereits gespeicherte Punkte
  ungültig machen.
- Das nachträgliche Entfernen einer Kriterienzuordnung bzw. Ändern eines
  Bewerbungszeitraums muss berücksichtigt werden.
- Dokumenttyp und Dokument-Untertyp müssen zueinander passen.
- Pro Bewerbung soll es höchstens ein Motivationsschreiben geben.
- Eine abgeschlossene Bewertung soll alle vorgesehenen Kriterien enthalten.
- Eine Auswahlentscheidung soll mindestens ein beteiligtes Mitglied haben.

Der vorhandene Trigger prüft **neue oder geänderte Bewertungspunkte**;
er löst diese weiteren Regeln noch nicht.

Aktueller Stand des Bewertungsmodells
Eine Bewertung bezieht sich auf genau einen Gegenstand:
ein Dokument, eine Engagement-Angabe, einen Lebensumstand oder eine
Auszeichnung. Ein Kommissionsmitglied bewertet diesen Gegenstand;
verschiedene Gegenstände derselben Bewerbung können von verschiedenen
Mitgliedern bewertet werden.

Jeder Gegenstand darf höchstens einmal bewertet werden. Die Punkte werden
pro Bewertung und Kriterium in bewertungspunkt gespeichert.

Die Datei sql/04_bewertung_pro_gegenstand.sql hat das ursprüngliche
Bewertungsschema geändert und die drei vorhandenen Demobewertungen ihren
Engagement-Angaben zugeordnet.

Wichtig beim Neuaufbau: Diese Migration erwartet genau die drei
Demobewertungen aus 02_beispieldaten.sql und
02_beispieldaten_erweitern.sql. Sie muss daher nach beiden
Beispieldaten-Dateien ausgeführt werden. Sie darf nicht erneut auf der
bereits migrierten Datenbank laufen.

Der angepasste test_punkte_regel.sql und test_engagement_einmal.sql
wurden erfolgreich ausgeführt. Beide Tests nehmen ihre Testdaten mit
ROLLBACK zurück.
## Nächste Schritte

1. SQL-Dateien gemeinsam prüfen und Einrichtung auf dem zweiten Rechner testen.
2. Offene Konsistenzregeln priorisieren.
3. Beispieldaten in `sql/02_beispieldaten.sql` eintragen.
4. Mindestens eine View und zwei zur Abfrage passende Indizes erstellen.
5. Zehn SQL-Abfragen entwickeln.
6. Python-/Streamlit-Anwendung bauen und testen.
7. Bericht und Präsentation fertigstellen.