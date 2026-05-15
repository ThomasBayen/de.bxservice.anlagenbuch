# Anlagenbuch — Architektur

Diese Datei beschreibt, **wie** das Anlagenbuch gebaut ist: Auslieferungs-Form,
Generator, UUID-Strategie, BeanShell-Skripte. Adressat sind Mitwirkende
(Entwickler, Forks, Community-Beiträge). Für den fachlichen Hintergrund
siehe `Concept_de.md`, für die Tabellen- und Spaltenreferenz `DataModel_de.md`.

## Auslieferung als 2Pack

Erstinstallation läuft komplett über das Standard-2Pack-Fenster eines
bestehenden iDempiere — **kein Server-Zugriff, kein Plugin-Build nötig**.
Enthalten im ZIP:

- DB-Objekte (Tabellen, Spalten, Sequenzen, Listen, Fenster, Tabs, Felder,
  Prozesse, Rules)
- BeanShell-Skripte aus `scripts/*.bsh` als `AD_Rule.Script` eingebettet
- JasperReport-Templates aus `reports/*.jrxml` eingebettet
- Initial-Daten für Anlagenklassen und Wartungstermin-Typen
- Deutsche Übersetzungen (`AD_Element_Trl`, `AD_Field_Trl`, `AD_Window_Trl`,
  `AD_Tab_Trl`, `AD_Process_Trl`, `AD_Ref_List_Trl`)

Tabellennamen, Spaltennamen und UI-Default-Labels sind englisch
(Community-Tauglichkeit). Doku ist deutsch.

**Voraussetzung für saubere Migration zu einem späteren OSGi-Plugin:**
Alle UUIDs werden einmalig fixiert und versioniert abgelegt (siehe unten).

## Repo-Struktur

```
Anlagenbuch/
├── docs/                  Anwender-, Admin- und Architektur-Doku
├── src/                   Quellen der PDF-Outputs (Werkstattmappe, Präsi, Kurzanleitung)
├── 2pack/                 2Pack-Quelle und Build-Wrapper
│   ├── source/spec/       YAML-Specs (eine Datei pro Domäne)
│   ├── source/assemble.py YAML → PackOut.xml-Generator
│   └── build.sh           ruft assemble.py + zippt zu Anlagenbuch.zip
├── scripts/               BeanShell-Skripte (als AD_Rule.Script eingebettet)
├── reports/               JasperReports-Quellen (jrxml, DE + EN)
├── import/                CSV-/ODS-Vorlagen + Mapping-Doku
├── setup/                 Bootstrap-Skripte (Rollen, REST-Helper)
└── uuids.csv              fixierte UUIDs aller Objekte
```

## UUID-Strategie

Alle Objekte (Tabellen, Spalten, Fenster, Tabs, Felder, Listen, List-Werte,
Sequenzen, Prozesse, Rules, Reports, Initialdatensätze) erhalten **einmalig
generierte, im Repo fixierte UUIDs**. `uuids.csv` ist die zentrale Wahrheit:

```
ObjectType,Name,UUID
AD_Table,BXS_Asset,a7b3c1d4-...
AD_Column,BXS_Asset.Value,...
AD_Window,BXS_Asset_Window,...
AD_Reference,BXS_AssetStatus,...
```

Der Generator füllt fehlende Einträge beim ersten Lauf mit `uuid4`-Werten
und schreibt die Datei zurück. Wiederholte 2Pack-Imports sind idempotent —
derselbe logische Schlüssel liefert dieselbe UUID, iDempiere erkennt
bestehende Datensätze und aktualisiert sie statt zu duplizieren.

## Generator (`2pack/source/assemble.py`)

Python-Generator, der die YAML-Specs aus `2pack/source/spec/` zu
`2pack/source/PackOut.xml` umsetzt. Top-Level-Blöcke und ihre Aufgabe:

| YAML-Block            | Erzeugt                                                                                                                  |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `package:`            | `<idempiere>`-Header-Attribute                                                                                           |
| `references:`         | `AD_Reference` (List-Typ) + `AD_Ref_List`s, jeweils mit nested `_Trl(de_DE)`                                             |
| `tables:`             | `AD_Element`s (außer Core-Spalten in `CORE_ELEMENTS`-Map), `AD_Table` mit `AD_Column`-Reihe                              |
| `additional_columns:` | eigenständige `AD_Column`-Records (für `ALTER TABLE` auf bestehende Tabellen, z.B. nachträglicher Forward-FK)            |
| `sequences:`          | DocumentNo-Sequenzen (Tabellen-ID-Sequenz macht iDempiere selbst per `MTable.afterSave`)                                 |
| `windows:`            | `AD_Window` + `AD_Tab`s mit Display-Logic / Where-Clause / Read-only-Flag, `AD_Field` pro Spalte (auto), `AD_Menu`       |
| `rules:`              | `AD_Rule` (BeanShell-Source eingebettet aus `scripts/*.bsh`), `AD_Table_ScriptValidator`-Verknüpfungen                   |
| `processes:`          | `AD_Process` + `AD_Process_Para` + Toolbar-Button-Verknüpfung (`AD_Tab.AD_Process_ID`)                                   |
| `reports:`            | `AD_Process` mit `IsReport=Y`, eingebettete `.jrxml`, `AD_PrintFormat`                                                   |
| `initial_data:`       | Generische PO-Records (`<TableName type="table">`) mit `_UU`-Spalte; PackIn defert sie, bis Tabelle + FK-Referenzen aufgelöst sind |

Build-Zeit unter 2 s, 2Pack-Import-Zeit gegen iDempiere 11 ca. 30 s
inklusive OSGi-Stack-Start.

## DocumentNo-Sequenzen

Belegnummer-Schema: `{Präfix}-{Jahr}-{5-stellig}`. Jahr aus
`ReportedDate` bzw. `Created`.

| Typ              | Präfix-Beispiel  | AD_Sequence-Name          |
| ---------------- | ---------------- | ------------------------- |
| Fehlerbericht    | `FEH-2026-00184` | `BXS_AssetItem_Defect`    |
| Wartungstermin   | `TER-2026-00412` | `BXS_AssetItem_Schedule`  |
| Statusbericht    | `STA-2026-00033` | `BXS_AssetItem_Status`    |
| Werkstattauftrag | `WAU-2026-00031` | `BXS_WorkOrder_DocumentNo`|

Vergabe per `AD_Rule` (BeanShell, `EventType='T'`) als
`TableEventValidator` — siehe `CLAUDE.md` für die drei Stolpersteine
(EventType-Konstante, Vararg-Bridging, Default-Tabellen-Sequenz).

## BeanShell-Skripte (`AD_Rule`)

Jede Logik als eigene `.bsh`-Datei im `scripts/`-Ordner; im 2Pack mit
`Script`-Feld aus der Datei eingebettet.

| Skript                            | Trigger                                | Aufgabe                                                                                       |
| --------------------------------- | -------------------------------------- | --------------------------------------------------------------------------------------------- |
| `assetitem_documentno.bsh`        | TableEvent `TYPE_BEFORE_NEW` auf `BXS_AssetItem` | Setzt `DocumentNo` aus passender Sequenz je nach `Type`                             |
| `workorder_documentno.bsh`        | TableEvent `TYPE_BEFORE_NEW` auf `BXS_WorkOrder` | Setzt `DocumentNo` aus `BXS_WorkOrder_DocumentNo`                                   |
| `assetitem_close.bsh`             | Process „Eintrag schließen"            | Schließt Item; bei `Schedule` Folgetermin anlegen, `NextItem_ID` setzen                       |
| `workorder_pull_open_items.bsh`   | Process „Offene Einträge übernehmen"   | Trägt offene `Defect`/`Schedule`-Items des Assets als `BXS_WorkOrder_Item` ein, `IsResolved=Y`|
| `workorder_complete.bsh`          | Process „Auftrag abschließen"          | Items mit `IsResolved=Y` auf `Done` setzen, Folgetermine anlegen, `WorkOrderStatus=Completed` |
| `asset_create_workorder.bsh`      | Process „Werkstattauftrag aus Anlage"  | Legt `BXS_WorkOrder` an + zieht offene Einträge automatisch hinüber                           |

Konventionen: idempotent wo möglich, Fehler über
`org.compiere.process.ProcessInfo.addLog()`, keine direkten DB-Zugriffe
ohne PO-Modelle.

## Reports (JasperReports)

Zwei jrxml-Dateien je Report — eine deutsche (Default für JBKG), eine
`_en`-Variante. Begründung: Resource-Bundles (`$R{key}`) wären der
Jasper-Standardweg, lösen aber das eigentliche Konsistenzproblem nicht —
ändert ein Admin in iDempiere ein UI-Label, bleibt das Report-Property
unverändert. Der Mehraufwand für zwei jrxml-Dateien zahlt sich gegenüber
dieser Unsicherheit nicht aus.

**Spätere Variante:** Spaltenlabels per JOIN auf `AD_Element_Trl` direkt
aus iDempiere ziehen — einzige Variante, die UI-Änderungen automatisch
in den Report nachzieht. Statische Überschriften dann über `AD_Message`.

Querschnitts-Konventionen für JasperReports (Multi-Selection-Parameter,
`$P{}` vs `$P!{}`, „Seite X von Y", `positionType=Float`, Sub-Datasets)
stehen iDempiere-weit in `~/iDempiere-development/docs/jasperreports-knowhow.md`.

## Menü-Konvention „Anlagenbuch"

Alle Anlagenbuch-Menüpunkte (Fenster und Reports) hängen unter einem
Summary-Knoten „Anlagenbuch", der ganz am Ende des Menübaums angefügt
wird (Parent=Root, SeqNo=999). Verdrahtung läuft komplett über den
Generator — Details in `CLAUDE.md` (inkl. Workaround für die
`MWindow.afterSave`-Tree-Verkabelung).

## Berechtigungen

Master/Login-Rollen-Konzept der Jakob Bayen KG: eine domänenspezifische
**Master-Rolle** `anlagenbuch` (lowercase) hält die Window-/Process-Rechte
auf alle vier Hauptfenster. **Login-Rollen** (`GF`, `Disposition`, …)
inkludieren die Master-Rolle per `AD_Role_Included`. Anlage und Wartung
über `setup/bootstrap_roles.py` (REST-getrieben, idempotent).

Hintergrund-Konzept: `../Datalotte.md` im übergeordneten Repo-Verzeichnis.

## Wichtigste Lessons aus dem 2Pack-Bau

Detail in `~/iDempiere-development/2packtool/docs/11-lessons-handcoded-2pack.md`.
Die Punkte mit dem höchsten Stolperpotenzial:

1. **Trl-Records nested** `type="translation"` statt Sibling `type="table"`.
2. **Standardspalten** (`Value`/`Name`/`IsActive`/…) referenzieren Core-`AD_Element`-IDs;
   kein neues `AD_Element` anlegen.
3. **Initialdaten neu erstellter Tabellen als generische PO-Records** (`<TableName type="table">`) mit
   gesetzter `_UU`-Spalte — PackIn defert sie automatisch, bis Tabelle und FK-Refs aufgelöst sind.
   `<SQLStatement>` läuft synchron und scheitert beim Erstinstall an noch nicht existierenden Tabellen.
4. **`_AccessLevel`-Mismatches** geben subtile Pflicht-Verletzungen — System-Stammdaten = 6,
   Tenant-Bewegungsdaten = 3.
5. **ZIP-Filename `…_SYSTEM_…`** für system-level 2Pack (Wert `AD_Client.Value` für `AD_Client_ID=0`,
   nicht der String `System`).
6. **`AD_Field` für *jede* Tabellenspalte** emittieren (auch System-/Audit-/Parent-Spalten mit
   `IsDisplayed=N`). Ohne füllt `GridTab.setCurrentRow` den Tab-Kontext nicht — Folge:
   Felder grau, Save scheitert mit `AD_Client_ID=-1`, Detail-Tabs leer.
7. **`TableDir` auf Core-Tabellen ohne `AD_Window`** (z.B. `M_Resource` in der Standard-Installation)
   ist ein UI-Killer: NPE in `MLookupFactory.getLookup_TableDir` beim Tab-Init.
8. **`AD_Rule.EventType='T'`** für Table-Event-Validatoren. `M` (Measure for Performance Analysis)
   triggert nicht — der Validator bleibt stumm.
9. **BeanShell + `DB.getSQLValue(...)` mit Parametern**: die varargs-Überladung ist nicht
   dispatchbar — `java.util.List<Object>` füllen.
10. **Default-Tabellen-Sequenz** (`DocumentNo_<Tabelle>`) deaktivieren, sonst greift `PO.saveNew()`
    aus ihr — bevor unsere TBN-Rule überhaupt gefragt wird.

Bei Änderung von `AD_Rule`-Records per `psql`: **iDempiere-Server neu starten**,
sonst greift der MRule-/MTableScriptValidator-Cache und liefert die alte Version
(oder gecachtes „kein Validator gefunden").

## Migration zu einem OSGi-Plugin (offen)

Wird relevant, sobald die Logik wächst über das hinaus, was sich in
`AD_Rule`-Skripten wartbar abbilden lässt, Java-Tests / ModelValidator-Hooks
gefragt sind, oder das Modul als Community-Beitrag veröffentlicht wird.

OSGi-Bundle `de.bxservice.anlagenbuch` mit dem 2Pack als Ressource.
Wegen der stabilen UUIDs werden bestehende Datensätze beim Plugin-Import
nicht dupliziert.
