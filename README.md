# Datenbankprojekt: Verwaltung des Deutschlandstipendiums

> **Projekt- und Berichtsentwurf.** Diese README beschreibt den aktuellen
> Entwicklungsstand, die fachlichen Entscheidungen, die technische Umsetzung
> und die Einrichtung der Anwendung. Für die endgültige Abgabe müssen
> Diagramme, Screenshots, Testergebnisse und der Neuaufbau auf einem zweiten
> Rechner ergänzt beziehungsweise überprüft werden.

## 1. Projektüberblick

Das Projekt unterstützt den Prozess von der Bewerbung um ein Stipendium über
die Bewertung einzelner Bewerbungsbestandteile bis zur Förderentscheidung.

Es gibt drei Benutzergruppen:

- **Bewerberinnen und Bewerber** registrieren sich, erstellen eine Bewerbung,
  ergänzen Angaben, laden PDF-Dokumente hoch und verfolgen ihren Status.
- **Kommissionsmitglieder** prüfen eingereichte Bewerbungen, bewerten einzelne
  Gegenstände anhand von Kriterien und dokumentieren Förderentscheidungen.
- **Koordination** verwaltet Ausschreibungen, Bewerbungszeiträume und
  gegebenenfalls Benutzerkonten. Der genaue Funktionsumfang dieser Rolle
  muss vor der Abgabe mit der tatsächlich laufenden `app/main.py` abgeglichen
  werden.

**Technologien:** PostgreSQL, SQL, Python und Streamlit.

Die Anwendung wird derzeit **lokal als Studienprojekt** betrieben. Sie ist
nicht als öffentliches Hochschulportal freigegeben.

## 2. Aufgabenstellung und Umsetzungsstand

| Anforderung | Stand | Nachweis im Projekt |
|---|---|---|
| Drei Use Cases und Anforderungsanalyse | Arbeitsfassung vorhanden; Berichtstext noch ausarbeiten | Abschnitt 3; ergänzende Dokumentation unter `docs/` |
| Konzeptueller Entwurf mit 20–30 Entitätstypen | Arbeitsfassung vorhanden; aktuelles Diagramm muss mit Implementierung abgeglichen werden | ER-Diagramm unter `docs/` **[ERGÄNZEN]** |
| Logischer Entwurf und Normalformen | Relationen und funktionale Abhängigkeiten untersucht; Änderungen am Bewertungsmodell nachtragen | Abschnitt 5; Dokument unter `docs/` **[ERGÄNZEN]** |
| SQL-DDL mit Primär- und Fremdschlüsseln | In PostgreSQL umgesetzt | `sql/01_schema*.sql` und spätere Änderungsdateien |
| Mindestens eine View | Umgesetzt: berechnete Rangliste | `sql/03_rangliste_view.sql` |
| Mindestens zwei Indizes | Umgesetzt; auf Abfragen bezogen | `sql/04_indizes.sql` |
| Zehn SQL-Abfragen | Erstellt und ausgeführt | `sql/03_abfragen.sql` |
| Datenbankgestütztes Tool | Streamlit-App mit PostgreSQL-Verbindung vorhanden | `app/main.py` |
| Test und Installation durch zweite Person | Noch nicht abschließend durchgeführt | Abschnitt 10 |

**Abgabetermin des Projektberichts laut Aufgabenstellung:** 30.09.
Die Termine und der tatsächlich verlangte Abgabeumfang sollten vor Abgabe
noch einmal mit der aktuellen Kursinformation abgeglichen werden.

## 3. Anforderungsanalyse: die drei Use Cases

### UC1 – Bewerbung einreichen

**Akteur:** Bewerberin oder Bewerber.

**Ziel:** Innerhalb eines geöffneten Bewerbungszeitraums eine Bewerbung
vorbereiten und verbindlich einreichen.

**Hauptablauf:**

1. Die Person registriert sich beziehungsweise meldet sich an.
2. Sie wählt einen offenen Bewerbungszeitraum.
3. Sie legt eine Bewerbung mit Status `Entwurf` an.
4. Sie ergänzt bei Bedarf Engagement, Lebensumstände und Auszeichnungen.
5. Sie lädt Motivationsschreiben und Leistungsnachweis als PDF hoch und
   ordnet jeder Datei ihre Dokumentart zu.
6. Das System prüft die Pflichtdokumente und den Bewerbungszeitraum.
7. Die Person bestätigt das Einreichen.
8. Das System setzt den Status auf `Eingereicht`, speichert das Eingangsdatum
   und erzeugt einen Benachrichtigungseintrag.

**Alternativabläufe:**

- Bewerbungszeitraum geschlossen: Keine neue Einreichung.
- Bereits eine Bewerbung derselben Person für denselben Zeitraum vorhanden:
  Keine zweite Bewerbung.
- Pflichtdokument fehlt: Bewerbung bleibt ein Entwurf.
- Datei ist keine erkennbare PDF oder überschreitet das Größenlimit:
  Upload wird abgelehnt.
- Änderung einer fremden oder bereits eingereichten Bewerbung:
  Änderung wird verweigert.

**Abgrenzung:** Ein Eintrag in `benachrichtigung` ist derzeit keine tatsächlich
versendete E-Mail.

### UC2 – Bewerbungsgegenstände bewerten

**Akteur:** Kommissionsmitglied.

**Ziel:** Einzelne Bestandteile einer eingereichten Bewerbung nachvollziehbar
bewerten.

Die Gegenstände sind **Dokumente, Engagement, Lebensumstände und
Auszeichnungen**. Nicht zwingend dasselbe Mitglied bewertet sämtliche
Gegenstände einer Bewerbung.

**Hauptablauf:**

1. Das Mitglied meldet sich an und wählt den Bewerbungszeitraum.
2. Es sucht eine Bewerbung nach Name oder Matrikelnummer.
3. Es öffnet die Bewerbung und wählt einen Gegenstand.
4. Es betrachtet dessen PDF beziehungsweise erfasste Beschreibung.
5. Es wählt ein Kriterium, vergibt Punkte und ergänzt einen Kommentar.
6. Das System prüft unter anderem Zeitraumzuordnung und Punktegrenze.
7. Die Bewertung wird gespeichert; der Bearbeitungsstand aktualisiert sich.

**Alternativabläufe:**

- Punkte liegen über `max_punkte`: Speicherung wird abgelehnt.
- Kriterium gehört nicht zum Bewerbungszeitraum: Speicherung wird abgelehnt.
- Gegenstand gehört zu einer anderen Bewerbung: Speicherung wird abgelehnt.
- Gegenstand ist bereits durch ein anderes Mitglied bewertet:
  Keine zweite Bewertung dieses Gegenstands.
- PDF-Datenbankeintrag existiert, lokale Datei fehlt: Die Anwendung zeigt
  keine erfundene PDF-Vorschau an.
- Bereits entschiedene Bewerbung: Reguläre Bewertungsänderungen werden
  über den Anwendungsablauf gesperrt.

**Wichtige fachliche Einschränkung:** „Alle *erfassten* Gegenstände bewertet“
beweist für sich genommen nicht, dass alle erforderlichen Unterlagen
überhaupt eingereicht wurden.

### UC3 – Förderentscheidung treffen

**Akteur:** Kommissionsmitglied.

**Ziel:** Nach Ende der Bewerbungsfrist für eine geprüfte Bewerbung
`Bewilligt`, `Warteliste` oder `Abgelehnt` dokumentieren.

**Hauptablauf:**

1. Das Mitglied prüft Bewerbung, Unterlagen, Einzelbewertungen und Score.
2. Es prüft, ob die Frist abgelaufen und die Bewerbung entscheidungsreif ist.
3. Das System zeigt die Zahl bereits bewilligter und maximal verfügbarer
   Förderplätze des Bewerbungszeitraums.
4. Das Mitglied wählt den Förderstatus und gibt eine Begründung an.
5. Das System speichert die Entscheidung und beteiligte Person.
6. Die Bewerbung wird abgeschlossen; ein Benachrichtigungseintrag entsteht.

**Alternativabläufe:**

- Frist läuft noch: Keine neue Entscheidung.
- Pflichtdokumente oder erforderliche Bewertungen fehlen: Keine Entscheidung.
- Es existiert bereits eine Entscheidung: Keine zweite aktuelle Entscheidung.
- Alle Förderplätze sind bewilligt: Weitere Bewilligung wird abgelehnt;
  `Warteliste` und `Abgelehnt` bleiben möglich.
- Begründung fehlt: Die Anwendung weist die Eingabe zurück.

**Fristregel:** Ist `ende = 30.09.`, ist der 30.09. noch Bewerbungstag.
Entscheidungen sind ab dem **01.10.** möglich.

**Kapazitätsregel:** `max_foerderplaetze` gehört zum einzelnen
Bewerbungszeitraum. 25 ist der Standardwert der bisherigen Demo, **keine
unveränderliche Vorgabe für jedes Stipendium**. „Noch verfügbar“ bedeutet
eine Obergrenze; die Kommission ist nicht verpflichtet, alle Plätze zu
vergeben. Die Ausschreibung wird bei ausgeschöpfter Kapazität **nicht**
automatisch vorzeitig geschlossen.

## 4. Konzeptueller Entwurf und Entwurfsentscheidungen

Das ursprüngliche Modell deckte unter anderem Personen, Studierende,
Kommissionsmitglieder, Stipendien, Zeiträume, Bewerbungen, Dokumente,
Bewerbungsangaben, Bewertungen und Entscheidungen ab.

Die Anzahl der **Entitätstypen im finalen ER-Diagramm** muss getrennt von der
Anzahl der SQL-Tabellen angegeben werden: Zwischentabellen für m:n-Beziehungen
sind nicht automatisch zusätzliche fachliche Entitätstypen.

**Finales ER-Diagramm:** `[ERGÄNZEN: relativer Pfad, z. B. docs/er_final.pdf]`

### Während der Entwicklung geänderte Annahmen

| Ausgangsannahme / Problem | Entscheidung und Begründung |
|---|---|
| Eine Bewertung betrifft pauschal eine ganze Bewerbung. | Bewertung betrifft genau **einen konkreten Gegenstand**. Erst dadurch wird erkennbar, welches Dokument oder welche Angabe tatsächlich beurteilt wurde. |
| Mehrere Mitglieder könnten dieselbe Bewerbung unabhängig als Ganzes bewerten. | Verschiedene Mitglieder dürfen verschiedene Gegenstände übernehmen; ein einzelner Gegenstand soll höchstens einmal bewertet werden. |
| Die Rangliste wird als eigenständiger Datenbestand gepflegt. | Score und Rang werden aus abgeschlossenen Bewertungen berechnet, um widersprüchliche gespeicherte Werte zu vermeiden. |
| Förderer ist eine Person. | Förderer können auch Organisationen sein und werden daher eigenständig modelliert. |
| Dokumente und Engagement-Angaben sind dasselbe. | Angaben sind eigenständige fachliche Objekte; PDFs sind Dokumente. Ein optionaler Beleg darf eine Angabe unterstützen, ohne sie zu ersetzen. |
| „Geprüft“ bedeutet „bewilligt“. | Bewertungsstand und Förderentscheidung sind getrennte Prozessschritte. |
| Jeder Zeitraum hat fest 25 Plätze. | Kapazität wird pro Bewerbungszeitraum gespeichert. |
| Kommission kann sofort nach Bewertung entscheiden. | Neue Entscheidungen sind erst **nach** dem letzten Bewerbungstag zulässig. |
| Personenrollen könnten überlappen. | Im vorgesehenen Ablauf sind Bewerber- und Kommissionsrolle getrennt; die Anwendung erwartet pro Login eine eindeutige Rolle. |

**Koordination:** Die Verwaltungsrolle wird in der geplanten schlanken
Implementierung als besondere Rolle eines Kommissionsmitglieds behandelt.
Die tatsächlich umgesetzten Rechte sind vor Abgabe mit der Anwendung und dem
ER-Diagramm abzugleichen.

## 5. Logischer Entwurf, Schlüssel und Normalisierung

Die anfängliche Überführung des ER-Modells ergab **26 relationale Tabellen**.
Später kam unter anderem `login_konto` hinzu und die Bewertungstabelle wurde
geändert. Die Zahl der Tabellen in der aktuellen Datenbank ist deshalb
**nicht mehr ungeprüft mit 26 gleichzusetzen**.

Beispiele wichtiger Relationen und Regeln:

| Relation | Schlüssel und fachliche Regel |
|---|---|
| `bewerbung` | PK `bewerbungs_nr`; FKs zu Studierendem und Zeitraum; `UNIQUE(studierenden_id, zeitraum_id)` |
| `dokument` | PK `dokument_id`; FK zur Bewerbung |
| `bewertung` | PK `bewertung_id`; genau einer von Dokument, Engagement, Lebensumstand und Auszeichnung als Gegenstand |
| `bewertungspunkt` | PK `(bewertung_id, kriterium_id)`; Punkte je Bewertung und Kriterium |
| `zeitraum_kriterium` | PK `(zeitraum_id, kriterium_id)`; Gewichtung eines Kriteriums im Zeitraum |
| `auswahlentscheidung` | Höchstens eine aktuelle Entscheidung je Bewerbung |
| `login_konto` | Ein Login pro Person; eindeutige Login-E-Mail; Passwort nur als Hash |

### Funktionale Abhängigkeiten

Beispiele:

- `bewerbungs_nr → studierenden_id, zeitraum_id, status, ...`
- `(studierenden_id, zeitraum_id) → bewerbungs_nr`, weil je Person und
  Zeitraum höchstens eine Bewerbung zulässig ist.
- `(bewertung_id, kriterium_id) → punkte`
- `(zeitraum_id, kriterium_id) → gewichtung`
- `(foerderer_id, stipendium_id) → finanzierungsbetrag`, soweit ein
  individueller Finanzierungsbetrag erfasst wird.

Die Trennung von `person`, `studierender`, `studiengang`,
`bewerbungszeitraum` und `bewerbung` vermeidet beispielsweise, dass
Studiengangsname und Fristangaben in jeder Bewerbungszeile wiederholt werden.
Unter den dokumentierten funktionalen Abhängigkeiten wurde für die
ursprünglichen Relationen mindestens die **3. Normalform** festgestellt.
Die formale Prüfung des **endgültigen** Schemas, insbesondere nach
Bewertungsmigration und `login_konto`, ist vor Abgabe zu aktualisieren.

**Vollständiges relationales Schema und Normalformnachweis:**
`[ERGÄNZEN: Pfad unter docs/]`

## 6. Datendefinition und technische Regeln

Die SQL-Dateien enthalten `CREATE TABLE`, Primär- und Fremdschlüssel,
`UNIQUE`- und `CHECK`-Bedingungen sowie spätere Änderungen und Trigger.

Bereits umgesetzte beziehungsweise getestete Beispiele:

- Zulässige Statuswerte einer Bewerbung.
- Je Studierendem höchstens eine Bewerbung pro Zeitraum.
- Punkte nicht negativ und nicht oberhalb von `max_punkte`.
- Bewertetes Kriterium gehört zum Zeitraum der Bewerbung.
- Derselbe Engagement-Gegenstand kann nicht zweimal bewertet werden.
- Förderentscheidung frühestens am Tag **nach** `ende`.
- Höchstens `max_foerderplaetze` Bewilligungen je Zeitraum.

Nicht jede fachliche Regel lässt sich allein mit PK und FK ausdrücken.
Tabellenübergreifende Prüfungen erfolgen teilweise in PostgreSQL-Triggern
oder transaktional in der Anwendung.

### Ranglisten-View

`rangliste` berechnet gewichtete Ergebnisse aus Einzelpunkten und
Gewichtungen. Sie berücksichtigt nach bisherigem Stand nur Bewerbungen im
Status `Abgeschlossen` und abgeschlossene Bewertungen.

Die Rangliste ist **intern**: Bewerber sollen keine Daten anderer Personen
sehen. Bewertungsfortschritt und fachliche Vollständigkeit müssen zusätzlich
zu einem vorhandenen Score betrachtet werden.

### Indizes

Zusätzliche Indizes unterstützen insbesondere:

1. das Auffinden von Bewertungen zu einer Bewerbungsnummer;
2. das Auffinden von Dokumenten zu einer Bewerbungsnummer.

Bei sehr wenigen Demodaten kann PostgreSQL trotz Index einen sequenziellen
Scan bevorzugen. Die Begründung der Indizes bezieht sich auf die
entsprechenden Anwendungsabfragen, nicht auf eine garantierte Nutzung
bei drei Testbewerbungen.

### Zehn SQL-Abfragen

Die Datei `sql/03_abfragen.sql` enthält unter anderem Bewerbungsübersicht,
Dokumente, Bewertungsmaßstab, Einzelbewertungen, Score, Rangliste,
unentschiedene Bewerbungen und eine parametrisierte Suche. Sie enthält
Joins, Aggregation, Unterabfrage und Parametrisierung.

## 7. Anwendung und Benutzerführung

**Echte Anwendung:** `app/main.py` verbindet sich mit PostgreSQL.
**UX-Prototyp:** `app/ux_prototyp.py` diente der Erprobung der Oberfläche.
Fiktive Sitzungsdaten des UX-Prototyps sind **keine** dauerhaft gespeicherten
Bewerbungen oder Entscheidungen.

Die echte Anwendung bietet je nach implementiertem Stand:

- Anmeldung mit E-Mail und Passwort;
- Bewerberregistrierung;
- rollenabhängige Bewerber- und Kommissionsansichten;
- Bewerbungsentwürfe, Angaben und PDF-Uploads;
- Bewerbungs-, Bewertungs- und Entscheidungsübersichten;
- Bewertung einzelner Gegenstände und Förderentscheidungen.

**Vor Abgabe überprüfen:** Ob die zuletzt geplanten Funktionen der
Koordinationsrolle – Stipendien und Zeiträume anlegen, Kommissionskonten
anlegen, Konten deaktivieren/reaktivieren – tatsächlich in der aktuellen
`app/main.py` gespeichert und getestet sind. Geplanter Code allein zählt
nicht als implementierte Funktion.

Bewerberabfragen sind in der Anwendung auf die angemeldete Person
eingeschränkt. Das ist eine wichtige Schutzmaßnahme, ersetzt aber **keine
vollständige produktive Berechtigungsarchitektur**: Die lokale App verwendet
weiterhin einen Datenbankzugang mit umfassenderen Rechten.

## 8. Schwierigkeiten, Anpassungen und Erkenntnisse

### 8.1 Bewertungsschema nachträglich geändert

Erst beim Entwerfen der Kommissionsansicht wurde deutlich, dass die erste
Bewertungstabelle den **bewerteten Gegenstand nicht eindeutig bezeichnete**.
Die laufende Datenbank wurde migriert; drei bereits existierende
Demobewertungen wurden ihren Engagement-Angaben zugeordnet.

**Erkenntnis:** ER-Modell, Tabellen und Oberfläche müssen gemeinsam am
konkreten Arbeitsablauf überprüft werden. Nach einer fachlichen Änderung
müssen auch Installationsdateien und Diagramme aktualisiert werden.

### 8.2 Datenbankstatus und fachlicher Zustand unterscheiden

Ein Bewerber mit Status `Eingereicht` kann seinen Entwurf nicht weiter
bearbeiten. Die Meldung war zunächst missverständlich, als mit einem bereits
eingereichten Demokonto ein PDF-Upload getestet wurde.

Ebenso gilt: Eine grüne Leiste für „alle erfassten Gegenstände bewertet“
ist keine automatische Förderzusage und kein Beweis für sämtliche fachlich
erforderlichen Unterlagen.

### 8.3 PDF-Vorschau

Die PDF-Vorschau in Streamlit benötigte eine zusätzliche PDF-Komponente.
Nach deren Installation funktionierte die Vorschau lokal. Ältere
Demo-Dokumenteinträge besitzen zum Teil nur Platzhalterpfade und können
daher trotz Datenbankeintrag keine echte PDF anzeigen.

### 8.4 Navigation und Übersicht

Im UX-Prototyp blieb eine geöffnete Bewerbungsdetailseite nach einem
Menüwechsel zunächst aktiv. Der gespeicherte Navigationszustand musste
beim Wechsel zurückgesetzt werden.

Für die Kommission wurden Suche nach Name/Matrikelnummer, Filter,
Bewerbungskarten und die getrennte Anzeige von Bewertungs- und
Entscheidungsstand als wichtig erkannt.

### 8.5 Frist und Förderplätze

Eine zunächst diskutierte automatische Schließung bei vollständig
vergebenen Plätzen wurde verworfen. Bewerbungsfrist und Zahl verfügbarer
Förderplätze sind **verschiedene Regeln**:

- `ende` begrenzt die Einreichung;
- nach Ablauf von `ende` sind Entscheidungen möglich;
- `max_foerderplaetze` begrenzt ausschließlich die Bewilligungen.

### 8.6 Historische Demodaten

Einige Demo-Entscheidungen wurden **vor Einführung der neuen Fristregel**
gespeichert. Der neue Trigger ändert historische Zeilen nicht rückwirkend.
Solche Daten dürfen im Bericht nicht als erfolgreich bestandener
Fristtest ausgegeben werden.

## 9. Testnachweise

Die Tests wurden überwiegend mit SQL-Transaktionen und abschließendem
`ROLLBACK` durchgeführt. Dadurch blieben die eigens erzeugten Testdaten
nicht in der Projektdatenbank.

| Test | Erwartung | Beobachteter Stand |
|---|---|---|
| 7 bei maximal 10 Punkten | Akzeptiert | Bestanden |
| 11 bei maximal 10 Punkten | Abgelehnt; alter Wert bleibt bestehen | Bestanden |
| Nicht dem Zeitraum zugeordnetes Kriterium | Abgelehnt | Bestanden |
| Zweite Bewertung desselben Engagements | Abgelehnt | Bestanden |
| Entscheidung vor Fristende | Abgelehnt | Bestanden |
| Entscheidung nach Fristende | Akzeptiert | Bestanden |
| Zweite Bewilligung bei Kapazität 1 | Abgelehnt | Bestanden |
| Bewerber registrieren | Bewerberkonto wird angelegt | Lokal erfolgreich durchgeführt |
| Vollständiger UC1–UC3-Ablauf in der App | Durchgängig nachvollziehbar | Hauptabläufe lokal erprobt; Alternativen weiter protokollieren |
| Neuaufbau auf zweitem Rechner | Gleiches Schema und gleiche Tests | **Noch ausstehend** |

**Testprotokolle/Screenshots:** `[ERGÄNZEN: Pfad unter docs/]`

## 10. Projekt lokal einrichten

### Voraussetzungen

- Ubuntu beziehungsweise eine vergleichbare Linux-Umgebung;
- PostgreSQL-Server und PostgreSQL-Client;
- Python 3 mit `venv`;
- Git;
- optional VS Code.

Die bisherige Entwicklungsdatenbank läuft unter PostgreSQL 16. Ein anderes
PostgreSQL-Release muss mit den verwendeten SQL-Funktionen und Triggern
getestet werden.

### Repository beziehen

```bash
git clone <REPOSITORY-URL>
cd deutschlandstipendium-db
```

`<REPOSITORY-URL>` durch eure tatsächliche Repository-Adresse ersetzen.

### Virtuelle Python-Umgebung

```bash
python3 -m venv DBS-Venv
source DBS-Venv/bin/activate
python -m pip install --upgrade pip
python -m pip install 'streamlit[pdf]' 'psycopg[binary]' python-dotenv
```

Für eine reproduzierbare Abgabe sollten die tatsächlich verwendeten
Paketversionen später in `requirements.txt` festgehalten werden:

```bash
python -m pip freeze > requirements.txt
```

Vor dem Commit prüfen, ob darin nur eure tatsächlich benötigten Pakete
stehen; ein Freeze kann auch zusätzliche Entwicklungsabhängigkeiten enthalten.

### PostgreSQL-Benutzer und Datenbank

Beispiel für eine **neue lokale Einrichtung**:

```bash
sudo -u postgres createuser --login --pwprompt stipendium_user
sudo -u postgres createdb --owner=stipendium_user stipendium_db
```

Diese Befehle **nicht erneut ausführen**, wenn Benutzer und Datenbank
bereits existieren. Das Datenbankpasswort nicht ins Repository schreiben.

Verbindung prüfen:

```bash
psql -h localhost -U stipendium_user -d stipendium_db -W \
  -c "SELECT current_user, current_database();"
```

### Lokale Konfiguration

Im Projektordner eine Datei `.env` anlegen:

```dotenv
DB_HOST=localhost
DB_PORT=5432
DB_NAME=stipendium_db
DB_USER=stipendium_user
DB_PASSWORD=HIER_LOKALES_DATENBANKPASSWORT
```

`.env` und `DBS-Venv/` dürfen **nicht** in Git gespeichert sein. Ebenso
müssen `private_uploads/` und Datenbank-Dumps ignoriert werden.

Vor einem Commit prüfen:

```bash
git check-ignore .env DBS-Venv/ private_uploads/
git status
```

**Keine echten personenbezogenen Unterlagen** für die Projektdemo verwenden.

### Schema und Demodaten aufbauen: aktueller Hinweis

Die vorhandene `stipendium_db` entstand **schrittweise**. Das ursprüngliche
Bewertungsschema wurde nachträglich migriert. Eine historische Datei
`sql/04_bewertung_pro_gegenstand.sql` erwartet ausdrücklich die drei
damaligen Demobewertungen und ist **keine allgemeine Migration für eine
beliebige neue Datenbank**.

Deshalb gilt:

> **Die Installationsreihenfolge für eine frische Datenbank ist noch nicht
> abschließend auf einem zweiten Rechner bestätigt.** Die vorhandenen
> `CREATE TABLE`-Dateien, spätere Trigger- und Kontodateien sowie die
> aktualisierten Demodaten müssen dafür in eine eindeutige Reihenfolge
> gebracht und einmal vollständig geprüft werden.

Die bekannten ursprünglichen Schema-Dateien beginnen mit:

```text
sql/01_schema.sql
sql/01_schema_02_personen.sql
sql/01_schema_03_stipendien.sql
sql/01_schema_04_bewerbungen.sql
sql/01_schema_05_angaben_dokumente.sql
sql/01_schema_06_bewertungen.sql
sql/01_schema_07_entscheidungen.sql
sql/01_schema_08_dokumentbeleg.sql
```

Danach folgen Regeldateien, Login-Schema, View, Indizes und gegebenenfalls
Demodaten. **Nicht** alle Dateien aus `sql/` alphabetisch blind ausführen:
Dort liegen auch Tests, einmalige Migrationen und Dateien, die nur auf
bestimmte Demodaten zugeschnitten sind.

**Vor der Abgabe ergänzen:**

- `[ERGÄNZEN: bestätigte Ausführungsreihenfolge bzw. Setup-Skript]`
- `[ERGÄNZEN: Ergebnis des Neuaufbaus auf dem zweiten Rechner]`
- `[ERGÄNZEN: aktuelle Tabellenzahl nach Neuaufbau]`

Die bereits funktionierende `stipendium_db` muss für diese Prüfung **nicht
gelöscht** werden. Nutzt beim Partner eine neue lokale Datenbank.

### Anwendung starten

```bash
source DBS-Venv/bin/activate
python -m streamlit run app/main.py
```

Streamlit zeigt die lokale URL im Terminal an, häufig
`http://localhost:8501/`.

Falls parallel der separate UX-Prototyp läuft, die Ports nicht verwechseln:
`app/main.py` verwendet PostgreSQL; `app/ux_prototyp.py` demonstriert
Oberflächenideen und kann fiktive Sitzungsdaten verwenden.

## 11. Sicherheit und Grenzen

- Login-Passwörter werden als gesalzene Hashes gespeichert, nicht im
  Klartext.
- `.env`, virtuelle Umgebung, private PDFs und Dumps werden nicht
  veröffentlicht.
- Bewerber sollen ausschließlich ihre eigenen Daten sehen.
- Kommissionskonten dürfen nicht über die öffentliche Bewerberregistrierung
  erstellt werden.
- Hochgeladene PDFs werden lokal gespeichert. Die einfache Datei- und
  Größenprüfung ersetzt keinen Malware-Scan.
- Es gibt derzeit keine verifizierte Hochschulidentität, keinen vollständigen
  Passwort-Zurücksetzen-Prozess und keine tatsächliche E-Mail-Zustellung.
- Einige Konsistenzregeln gelten nur über die Anwendung oder erfordern
  weitere Datenbankprüfungen. Die App ist daher **nicht produktionsreif**.

## 12. Offene Arbeiten bis zur Abgabe

1. ER-Diagramm und relationales Modell mit dem tatsächlich verwendeten
   Bewertungsmodell, `login_konto`, Kapazität und Koordinationsrolle
   synchronisieren.
2. Formale Normalformprüfung des **finalen** Schemas abschließen.
3. Installationsreihenfolge konsolidieren und auf dem Rechner des zweiten
   Projektmitglieds testen.
4. Aktuellen Funktionsumfang von Koordination und Bewerberansicht gegen
   `app/main.py` testen und diese README entsprechend aktualisieren.
5. Alternative Abläufe der drei Use Cases mit nachvollziehbaren
   Testprotokollen dokumentieren.
6. Fehlende fachliche Regeln präzisieren, insbesondere welche Kriterien zu
   welcher Gegenstandsart passen und wann eine Bewertung als vollständig gilt.
7. Bericht auf den geforderten Umfang ausarbeiten: Diagramme, DDL-Auszüge,
   relationale Schemata, Normalisierungsbegründung, Abfragen, Indizes,
   Screenshots und Testauswertungen einfügen.
8. Abschlussdemo und Präsentation vorbereiten.

## 13. Fazit

Die Entwicklung zeigt, warum Datenbankentwurf iterativ ist: Erst durch die
konkreten Bewerber- und Kommissionsabläufe wurde deutlich, dass Bewertungen
einem einzelnen Gegenstand zugeordnet sein müssen und dass
Bewerbungsfrist, Bewertungsfortschritt, Förderentscheidung und Kapazität
verschiedene fachliche Sachverhalte sind.

Die PostgreSQL-Datenbank, zahlreiche Regeln und Tests sowie eine
datenbankgestützte Streamlit-Anwendung sind vorhanden. Der wichtigste
verbleibende technische Nachweis ist ein **reproduzierbarer Aufbau aus dem
Repository** auf einem zweiten Rechner. Die endgültige Dokumentation muss
den dabei tatsächlich bestätigten Stand wiedergeben.