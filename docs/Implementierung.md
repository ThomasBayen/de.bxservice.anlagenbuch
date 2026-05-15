# Implementierung — Lessons Learned

Technische Stolpersteine und nicht-offensichtliche iDempiere-/2Pack-/
Generator-Erkenntnisse, die beim Bau des Anlagenbuchs aufgefallen sind.
Keine Roadmap, kein Status — reine Referenz.

## 2Pack / PIPO

- **`Trl`-Records nested emittieren**, nicht als Sibling. Übersetzungen
  gehören als `type="translation"`-Kind unter den jeweiligen
  `AD_Element`-/`AD_Field`-/`AD_Window`-Record, nicht als separater
  `type="table"`-Sibling-Record.
- **Standard-Spalten (Value/Name/Description/Help) referenzieren
  bestehende Core-`AD_Element`-IDs.** Niemals neue `AD_Element`-Records
  für Standard-Namen anlegen — sonst Duplikate. Mapping liegt in der
  `CORE_ELEMENTS`-Konstante im Generator.
- **Initial-Daten neu erstellter Tabellen via `<SQLStatement>`**, nicht
  über PO-Records. `MSequence` sieht in derselben Transaktion erstellte
  Sequenzen nicht — der PO-Insert kennt keine `Record_ID`. Mit
  `<SQLStatement>` + explizitem ID-Bereich (`1_000_000+`) + `ON CONFLICT
  DO NOTHING` läuft das idempotent.
- **`AccessLevel` muss zur Tabellen-Semantik passen**: System-Stammdaten
  AccessLevel=6, Tenant-Bewegungsdaten AccessLevel=3. Mismatch erzeugt
  subtile Pflicht-Verletzungen beim PO-Save.
- **ZIP-Filename `_SYSTEM_…` für System-Level-Pack.** Der Wert kommt aus
  `AD_Client.Value` für ID 0 (Wert ist `System`, nicht der String
  „System"). Falsche Schreibweise bricht den Importer-Pfad.
- **AD_Field für JEDE Tabellenspalte emittieren** — auch für
  System-/Audit-/Parent-Spalten mit `IsDisplayed=N`. Ohne diese
  Records füllt `GridTab.setCurrentRow` den Tab-Kontext nicht. Folgen:
  Felder grau (`isEditable` prüft `IsActive`-Kontext, der ohne
  AD_Field-Record leer bleibt), Save scheitert mit `AD_Client_ID=-1`,
  Detail-Tabs zeigen keine Datensätze (Parent-Link nicht aufgelöst).
- **Custom-Tabellen-Anlage und Initial-Daten-Insert NICHT im selben
  Pack-Lauf**: `PO.checkRecordIDCrossTenant` sieht uncommittete
  `AD_Column`-Zeilen nicht und liefert leere `keyColumns` →
  `ArrayIndexOutOfBoundsException`. Lösung: Schema-ZIP und Daten-ZIP
  separat, mit Commit dazwischen (RUN_ApplyPackInFromFolder.sh
  appliziert ZIPs alphabetisch — `_01_schema` / `_02_data`).

## Core-Tabellen-Referenzen

- **`TableDir` auf Core-Tabelle ohne konfiguriertes `AD_Window` ist ein
  UI-Killer.** Beispiel: `M_Resource` hat in der Standard-Installation
  kein Window; `MLookupFactory.getLookup_TableDir` wirft beim Tab-Init
  NPE, der die ganze Tab-Initialisierung blockt. Vor `TableDir`-FK
  immer prüfen, ob die Ziel-Tabelle ein `AD_Window` hat. `S_Resource`
  hat eines.

## Generator-Architektur

- **`additional_columns` in die Tabellen-Spec mergen**, damit
  `emit_window` auch für diese Spalten `AD_Field`-Records erzeugt.
  Sonst hätten z.B. virtuelle `column_sql`-Spalten zwar `AD_Column`,
  wären aber in keinem Tab sichtbar.
- **`primary_window`-Verkabelung** an `AD_Table` muss NACH den Windows
  emittiert werden — sonst keine UUID zum Auflösen.
- **Processes vor Windows emittieren**, damit Button-Spalten in
  `emit_window` auf die bereits gepoolten `AD_Process`-UUIDs verweisen
  können.
- **Anlagenbuch-Summary-Menu zuerst.** Der `MenuElementHandler`
  verarbeitet `AD_Menu`-Records in XML-Reihenfolge und braucht den
  Parent bereits in der DB, bevor Kinder ihn via UUID auflösen.

## ORDER BY in `column_sql`

- **`order by` muss kleingeschrieben werden**, sonst frisst
  `MRole.addAccessSQL` die Klausel beim SQL-Rewriting. Der
  ods-Importer ist hier NICHT schuld — der Bug sitzt im Core-
  Access-Rewriter. Kleinschreibung des `order by` ist der saubere
  Workaround.

## AD_Rule (BeanShell)

- **`AD_Rule.EventType='T'` für Table-Event-Validatoren.** `M` ist
  *Measure for Performance Analysis* und triggert nicht — der
  Validator bleibt stumm. Konstanten siehe `X_AD_Rule.EVENTTYPE_*`.
- **`DB.getSQLValue(...)` mit Parametern aus BeanShell**: die
  varargs-Überladung `(String,String,Object...)` ist für BeanShell
  nicht dispatchbar (kein Vararg-Bridging). Stattdessen
  `java.util.List<Object>` füllen und die `(String,String,List)`-
  Überladung nutzen.
- **Default-Tabellen-Sequenz deaktivieren**, wenn man `DocumentNo` per
  TBN-Rule setzt. `MTable.afterSave()` legt automatisch eine Sequenz
  `DocumentNo_<Tabelle>` an; solange die aktiv ist, schreibt
  `PO.saveNew()` aus ihr — die Reihenfolge zwischen Rule-SETZT und
  `saveNew()`-greift-zu ist subtle. Sauberer: Default-Sequenz per
  `isactive: false` in der 2Pack-`sequences:`-Spec inaktiv halten.
- **Nach Rule-Änderungen per psql iDempiere-Server neu starten**, sonst
  greift der `MRule`-/`MTableScriptValidator`-Cache und liefert die
  alte Version (oder gecachtes „kein Validator gefunden").

## Menü-Verkabelung

- **`MWindow.afterSave()` legt das Window-Menü autonom bei Root an**.
  Der nachfolgende `AD_Menu`-Merge via UUID aktualisiert
  `AD_TreeNodeMM` nicht — das funktioniert nur für Process- und
  Report-Menüs, NICHT für Window-Menüs. Workaround:
  `setup/fix_menu_tree.py` enthält `fix_window_menu_tree()`, das
  nach jedem 2Pack-Reimport die BXS-Window-Menüs idempotent unter
  den Anlagenbuch-Knoten verschiebt.
