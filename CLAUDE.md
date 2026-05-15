# Anlagenbuch

Konzept und Roll-out-Material für ein zentrales Wartungs- und Fehlerberichts-System („Anlagenbuch") als iDempiere-Erweiterung bei der Jakob Bayen KG.

## ⚠️ Goldene Regel: Source-of-Truth ist das 2Pack, NICHT die Testdatenbank

**Jede inhaltliche Änderung, die der Benutzer anweist (Felder, Fenster,
Spalten, Rules, Reports, Stammdaten, Reference Lists, Menü, Sequenzen,
…) MUSS zuerst in den 2Pack-Quellen unter `2pack/source/spec/*.yaml`
landen — und dann via `install.sh` / `2pack/build.sh` neu eingespielt
werden.**

Direkte SQL-Änderungen oder REST-API-Edits in der laufenden Test-DB sind
**nur** erlaubt als:

1. kurzfristige Diagnose/Reproduktion (sofort wieder zurückbauen), oder
2. Migration für bereits ausgelieferte Bestände (dann zusätzlich als
   Migrations-SQL ins Repo, plus Anpassung der 2Pack-Quellen für
   Neuinstallationen).

**Niemals** eine vom Benutzer gewünschte Korrektur „mal eben in der DB"
machen, ohne dass die Änderung auch in den 2Pack-YAMLs / BeanShell-
Rules / Reports / `example/`-CSVs steht. Sonst ist die Änderung beim
nächsten Reimport / bei jedem anderen Anwender weg — und genau das macht
das Community-Projekt wertlos.

Workflow für jede Korrektur:
1. Quelle in `2pack/source/spec/…` (oder `scripts/`, `reports/`,
   `import/`, `example/<Tenant>/`) anpassen.
2. `./install.sh` (oder gezielt `2pack/build.sh` + Reimport) laufen lassen.
3. Erst dann in der Test-DB verifizieren.

Wenn ich versucht bin, einen `UPDATE`/`INSERT` direkt gegen die Test-DB
abzusetzen, um schneller fertig zu werden: **stoppen, in die 2Pack-
Quellen schreiben, neu bauen, neu einspielen.**

## Verzeichnisstruktur

- `README.md` / `README_de.md` — Repo-Einstieg, Quick-Start, Doku-Navigation.
- `install.sh` — Repo-weiter Installer: baut 2Pack und spielt es in `$IDEMPIERE_HOME` ein. Liest `setup/config.env`.
- `LICENSE` — AGPL-3.0.
- `TODO.md` — offene Release-Punkte (migriert zu GitHub Issues, sobald Repo öffentlich ist).
- `docs/` — Anwender- und Architektur-Doku (englisch Default, deutsch als `_de.md` daneben). Reihenfolge zum Einlesen: `Concept.md` → `DataModel.md` → `Architecture.md` (für Mitwirkende). Bedienung: `QuickReference.md`, Installation: `Installation.md`, Versionsverlauf: `CHANGELOG.md`.
- `docs/archiv/` — historische Arbeitsdokumente (Brainstorming, ursprüngliches Implementierungs-Briefing). Nicht aktiv pflegen.
- `2pack/` — 2Pack-Quelle (YAML-Specs) + `build.sh`. Baut **drei** ZIPs:
  `Anlagenbuch_01_schema.zip` (Schema, Fenster, Prozesse, Rules, PrintFormats),
  `Anlagenbuch_02_data.zip` (initial-Daten) und
  `Anlagenbuch_03_role.zip` (System-Master-Rolle `anlagenbuch` mit
  Window-/Process-Access, AD_Client_ID=0, IsMasterRole=Y, IsManual=Y).
  Reihenfolge wird beim Folder-Apply alphabetisch erzwungen — nötig, weil
  iDempiere-PIPO Custom-Tabellen-Anlage und Initial-Daten-Insert nicht
  atomar in EINEM Pack-Lauf schafft (PO.checkRecordIDCrossTenant sieht
  uncommittete AD_Column-Zeilen nicht), und weil die Access-Records erst
  funktionieren, wenn die referenzierten Window/Process-Records committet
  sind.
- `scripts/` — BeanShell-Rules und generischer Schema-Smoke-Test.
- `reports/` — JasperReports-Quellen (DE + EN).
- `import/` — generische Templates (CSV, ODS-Erfassungsvorlage) und Master-Rolle-Definition.
- `setup/` — generische Helfer: `lib_rest.py`, `install_de_reports.sql`, `config.env.example`.
- `example/JakobBayenKG/` — JBKG-spezifisches Customer-Deployment-Beispiel (Master-Rolle-Includes, Testdaten-Builder, Bootstrap-Skript). **Dort gehören alle Bayen-spezifischen Bestandteile hin; die Community-Teile bleiben Tenant-neutral.**
- `src/` — Quellen für PDFs (Markdown, LaTeX, Bilder). `src/build.sh` baut nach `docs/`.

**Wichtig:**
- Es gibt **keine Versionierung**. Versionsnummern werden erst vergeben, wenn das Repository öffentlich getaggt wird. Versions-Bezeichner aus älteren Iterationen gehören nirgendwo mehr ins Repo.
- Wenn das Plugin-Archiv gemeint ist, immer „2Pack" schreiben (nicht „Pack"). Verzeichnis heißt `2pack/`.
- JBKG-Spezifika (Datalotte, FreiBier, Bayen-Fahrzeuge) gehören ausschließlich nach `example/JakobBayenKG/`. Die generischen Teile dürfen keine kundenspezifischen Credentials oder Identifier enthalten.

## Trennung Community-Plugin vs. Beispiel-Deployments

Repository-Wurzel + `2pack/`, `scripts/`, `reports/`, `setup/`, `import/`, `tools/`, `docs/`, `src/` ist **mandantenneutral**: Plugin-Code, Generator, Reports, Bootstrap-Helfer und Templates, die jeder Anwender brauchen kann. Keine echten Credentials, keine Tenant-IDs, keine Customer-Vehikel-Daten.

`example/<Tenant>/` enthält **ein konkretes Customer-Deployment**: Master-Rolle-Includes, Stammdaten in `data/`, ein Build-Skript, das die Master-Rolle anwendet und Stammdaten via ODS-Importer einspielt, und eine `config.env.example` mit den Defaults für die jeweilige Umgebung. Heute existiert nur `example/JakobBayenKG/`; perspektivisch könnte auch `example/GardenWorld/` als Community-Demo dazukommen.

Konvention pro Beispiel-Verzeichnis:
- `config.env.example` (getrackt, Defaults) und `config.env` (gitignored, reale Werte)
- `data/*.csv` als Source-of-Truth der Stammdaten
- `build_ods.py` baut daraus ein `<name>.ods` für den ODS-Importer
- `build.sh` orchestriert: Master-Rolle anwenden + ODS importieren + Smoke-Test
- `bootstrap_roles.py` für Master-Rolle-Anlage und Login-Rollen-Include (tenant-spezifisch, weil `LOGIN_ROLE_NAME` umgebungsabhängig ist)
- `masterrolle_includes.csv` listet die Login-Rollen, in die die Master-Rolle eingehängt wird

**Wichtig:** beim Schreiben neuer Skripte/Dateien immer fragen, ob das in den Community-Pfad oder ins Beispiel-Verzeichnis gehört. Im Zweifel: alles, was kundenspezifische Identifier, Credentials, Fahrzeug-/Anlagendaten enthält → Beispiel-Verzeichnis. Alles, was tenant-neutral funktioniert → Community-Pfad.

## Terminologie (in Anwender-Doku einhalten)

- **Anlage** statt „Asset". Einmalige Einführung als Synonym in der Begriffsübersicht ist OK; danach durchgängig „Anlage". In Programmierer-Doku (Datenmodell, Konzept) und DB-Tabellennamen (`BXS_Asset`, `A_Asset`) bleibt „Asset" als technischer Term.
- **Eintrag** statt „Item" für die Detail-Datensätze einer Anlage (Fehlerbericht, Wartungstermin, Statusbericht). Button heißt „Offene Einträge übernehmen". DB-Tabelle bleibt `BXS_AssetItem`.
- **Fehlerbericht** statt „Beanstandung" für `Type=Defect`-Einträge (in Anwender-Doku und UI-Labels). Englischer DB-Term und Reference-List-Value bleiben `Defect`.

## Build

`src/build.sh` baut zuerst `Werkstattmappe_Beispiel.pdf` mit pdflatex (zwei Durchläufe), dann `Praesentation_Mitarbeiter.pdf` mit pandoc → beamer. Beide Outputs landen in `docs/`. Zwischendateien liegen in `src/.build/`.

## ASCII-Mockups in der Präsentation

Die Eingabemasken-Mockups in `Praesentation_Mitarbeiter.md` sind Verbatim-Blöcke mit Box-Linien. Beim Bearbeiten **Display-Spaltenbreite** prüfen (nicht Bytes), weil Umlaute UTF-8 mehrbyte sind:

```
python3 -c "[print(len(l), repr(l)) for l in open('src/Praesentation_Mitarbeiter.md')]"
```

Alle Zeilen einer Box müssen gleiche Codepoint-Anzahl haben, sonst verrutschen die rechten Begrenzer im Render.

## Beispielanlagen

Wir verwalten LKW, PKW, Stapler, Rolltore, Feuerlöscher, Kehrmaschinen, Sackkarren. **Nicht** Tankstelle/Druckluftanlagen — die haben wir nicht im Betrieb.

## DocumentNo-Sequenzen (FEH-/TER-/STA-/WAU-)

Typgesteuerte Belegnummern für `BXS_AssetItem` (FEH-/TER-/STA- je nach
`Type=Defect/Schedule/Status`) und `BXS_WorkOrder` (WAU-) werden über
**AD_Rule TBN-Skripte** vergeben (siehe `2pack/source/spec/70-rules.yaml`).
Verkabelung: drei Stolpersteine, die alle einmal angefallen sind:

1. **`AD_Rule.EventType='T'`** für Table-Event-Validatoren. `M` ist
   *Measure for Performance Analysis* und triggert nicht — der Validator
   bleibt stumm. Konstanten siehe `X_AD_Rule.EVENTTYPE_*`.

2. **BeanShell + `DB.getSQLValue(...)` mit Parametern**: die varargs-
   Überladung `(String,String,Object...)` ist für BeanShell nicht
   dispatchbar (kein Vararg-Bridging). Stattdessen
   `java.util.List<Object>` füllen und die `(String,String,List)`-
   Überladung nutzen. Beispiel in `70-rules.yaml`.

3. **Default-Tabellen-Sequenz deaktivieren**: `MTable.afterSave()` legt
   für jede Tabelle mit `DocumentNo`-Spalte automatisch eine Sequenz
   `DocumentNo_<Tabelle>` an. Solange die aktiv ist, schreibt
   `PO.saveNew()` aus ihr — **bevor** unsere TBN-Rule überhaupt
   gefragt wird (technisch: die Rule SETZT, aber `saveNew()` greift
   später nochmal zu — die Reihenfolge ist subtle, einfacher ist es,
   die Default-Sequenz inaktiv zu halten). 2Pack-Source bügelt das per
   `isactive: false`-Eintrag in `sequences:` aus.

Wenn man Rules per psql ändert: **iDempiere-Server neu starten**, sonst
greift der MRule-/MTableScriptValidator-Cache und liefert die alte
Version (oder cached „kein Validator gefunden").

## Menü-Konvention „Anlagenbuch"

Alle Anlagenbuch-Menüpunkte (Fenster und Reports) hängen unter einem
Summary-Knoten „Anlagenbuch", der **ganz am Ende des Menübaums** angefügt
wird (Parent=Root, SeqNo=999). Verdrahtung läuft komplett über den
Generator:

- `2pack/source/assemble.py` → `emit_anlagenbuch_root()` legt den Knoten
  einmalig an, `emit_menu()` ist die generische Helper-Funktion für
  Kinder (Action W/P/R/N, mit Parent_ID + SeqNo).
- Windows: optionale `menu: { seq: N }`-Sektion in der Window-Spec.
  Default-Parent ist der Anlagenbuch-Knoten.
- Prozesse: nur Prozesse mit `menu: …` in der Process-Spec bekommen einen
  Menü-Eintrag (Tab-Toolbar-Buttons brauchen keinen).
- Tree-Verkabelung läuft über `AD_Menu.Parent_ID` + `SeqNo` im XML, plus
  `Parent_ID reference="uuid"` auf den Anlagenbuch-Root-Knoten. Mechanik
  in iDempiere-Core: `MMenu.afterSave()` ruft beim Insert
  `PO.insert_Tree(TREETYPE_Menu)` — das schreibt initial hartkodiert
  `Parent_ID=0, SeqNo=999` ins `AD_TreeNodeMM`. Direkt im Anschluss liest
  der pipo-`MenuElementHandler.startElement()` das `<Parent_ID>`-Element
  aus dem PackOut-XML und macht ein `UPDATE AD_TREENODEMM SET Parent_ID=?,
  SeqNo=?`. Das funktioniert für Window-, Process- und Report-Menüs
  **gleich** (der Handler unterscheidet nicht nach Action-Typ).
  `MWindow.afterSave()` legt entgegen früherer Annahme **kein** AD_Menu
  an — es synchronisiert nur Name/Description bestehender Menüs.
  → Anlagenbuch braucht **keinen** Post-Install-Tree-Fix; ein früher hier
  dokumentierter `setup/fix_menu_tree.py`-Workaround war eine
  Fehldiagnose und ist entfernt.

SeqNo-Vergabe heute: 10/20 für Hauptfenster (Anlage, Werkstattauftrag),
30/40 für Stammdaten (Anlagenklasse, Wartungstermin-Typ), 100+ für
Reports. Untergruppen sind noch nicht nötig; sobald der Knoten zu voll
wird, neue Summary-Knoten (`action="N"`) als Zwischenebene einziehen.

