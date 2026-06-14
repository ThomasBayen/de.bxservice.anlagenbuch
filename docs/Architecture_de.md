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
│   ├── gen/assemble.py    YAML → PackOut.xml-Generator (gevendort)
│   └── build.sh           ruft gen/assemble.py + zippt zu Anlagenbuch.zip
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

## Generator (`2pack/gen/assemble.py`)

Python-Generator, der die YAML-Specs aus `2pack/source/spec/` zu
`2pack/source/PackOut.xml` umsetzt. `gen/assemble.py` ist eine gevendorte
Kopie des kanonischen Generators; nicht direkt editieren (Drift-Marker:
`2pack/gen/.generator-md5`). Top-Level-Blöcke und ihre Aufgabe:

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

Die Rechtevergabe folgt einem Master/Login-Rollen-Schnitt: eine
domänen­spezifische **Master-Rolle** `anlagenbuch` (lowercase) hält die
Window-/Process-Rechte auf alle vier Hauptfenster. **Login-Rollen** (die
tatsächlichen Benutzer­rollen der Zielinstallation) inkludieren die
Master-Rolle per `AD_Role_Included` und tragen selbst keine Anlagenbuch-
spezifischen Rechte. Dadurch lässt sich das Plugin per einem einzigen
Include in eine Login-Rolle aufnehmen oder wieder entfernen, und die
vier Kern­fenster bleiben ohne Pro-Rolle-Pflege synchron.

### Master-Rolle im System-Mandanten

Die Master-Rolle wird vom 2Pack im **System-Mandanten** (`AD_Client_ID=0`,
`IsMasterRole=Y`, `IsManual=Y`) ausgeliefert — als drittes Paket
`Anlagenbuch_03_role.zip`, das nach Schema + Daten alphabetisch importiert
wird. Damit erbt jeder Tenant, der die Rolle via `AD_Role_Included` in eine
seiner Login-Rollen einhängt, automatisch alle Anlagenbuch-spezifischen
Access-Records — auch nachträglich, wenn ein 2Pack-Update neue Fenster
oder Prozesse mitbringt. Kein Tenant muss die Berechtigungen einzeln
pflegen.

Mechanik im Detail:

- `MRoleIncluded.beforeSave` prüft nur Schleifen, **nicht** ob die
  inkludierte Rolle im selben Mandanten liegt.
- Der DB-FK `AD_Role_Included.Included_Role_ID → AD_Role(AD_Role_ID)`
  hat keinen Client-Constraint.
- `MRole.loadChildRoles` und `mergeIncludedAccess` mergen die
  Access-Records der inkludierten Rolle **ungefiltert** in die
  Login-Rolle.
- Login-Query (`Login.getRoles`) filtert die Rollen­auswahl nicht auf
  Tenant-Match — sie zeigt nur dem User explizit zugeordnete Rollen
  (`AD_User_Roles`), nicht inkludierte.

Caveats:

- Die System-Master-Rolle darf nur Access auf System-Records
  (`AD_Client_ID=0`) tragen. Beim 2Pack-Lieferumfang automatisch der
  Fall (alle BXS_*-Records liegen im System-Mandanten).
- **`IsManual=Y` ist zwingend**: ohne diesen Flag legt
  `MRole.afterSave → updateAccessRecords` für ALLE Windows/Processes
  automatisch Access-Records gemäß UserLevel an. Unsere expliziten
  Access-Records kollidieren dann am Unique-Index, der ganze
  Pack-Import schlägt fehl.
- **UserLevel** wird von `MRole.beforeSave` für `AD_Client_ID=0`
  automatisch auf `"S  "` (System) gezwungen. Das ist OK: die
  Master-Rolle dient nur als Access-Container; UserLevel und
  OrgAccess kommen aus der Login-Rolle.
- Selektives Override im Tenant ist nicht vorgesehen — wer einzelne
  Berechtigungen abweichend braucht, muss eine eigene Login-Rolle ohne
  Include pflegen.

### Customer-Deployment

Eine Tenant-Bindung ist Customer-spezifisch. Für JBKG legt
`example/JakobBayenKG/bootstrap_roles.py` idempotent **genau einen**
`AD_Role_Included` an: von der Skript-Login-Rolle `Datalotte` auf die
System-Master-Rolle — nur damit der ODS-Import die Fenster sieht. Mehr
macht das Skript nicht. Welche **menschlichen** Anwender-Login-Rollen
(`GF`, `Disposition`, …) das Anlagenbuch sehen, ist eine bewusste
**manuelle** Admin-Entscheidung pro Rolle in der UI (siehe
`Installation.md`) — es gibt **keine** vorgegebene Rollenliste und keine
Automatik dafür.

## Lessons aus dem 2Pack-Bau

Die Stolpersteine, die beim Hand-Schreiben dieses 2Packs auftauchten —
Trl-Nesting, `AD_Element`-Wiederverwendung für Core-Spalten,
`<SQLStatement>` vs. generic-PO-Initialdaten, `_AccessLevel`-
Mismatches, `AD_Field` für jede Spalte, der `EventType='T'` /
BeanShell-Varargs / Default-`DocumentNo`-Sequenz-Cluster bei
`AD_Rule`-Table-Event-Validatoren, der Server-Restart-Bedarf nach
`psql`-Änderungen an Rules — sind **nicht Anlagenbuch-spezifisch**.
Sie gelten für jeden hand- oder generator-getriebenen 2Pack-Bau.

Die vollständige Liste mit Reproduktions-Hinweisen und Code-Snippets
wird zentral in `2pack-knowhow.md` in der iDempiere-Entwicklungs-
umgebung des Autors gepflegt (nicht Teil dieses Repos; falls
Community-Bedarf besteht, wird sie später in ein eigenes Public-
Projekt ausgelagert). Anlagenbuch-lokale Notizen, die darüber hinaus
gehen — DocumentNo-Präfix-Mapping, Menü-Tree-Verkabelung im Detail —
stehen in der `CLAUDE.md` im Repo-Root.

## Migration zu einem OSGi-Plugin (offen)

Wird relevant, sobald die Logik wächst über das hinaus, was sich in
`AD_Rule`-Skripten wartbar abbilden lässt, Java-Tests / ModelValidator-Hooks
gefragt sind, oder das Modul als Community-Beitrag veröffentlicht wird.

OSGi-Bundle `de.bxservice.anlagenbuch` mit dem 2Pack als Ressource.
Wegen der stabilen UUIDs werden bestehende Datensätze beim Plugin-Import
nicht dupliziert.
