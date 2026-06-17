# JRXML-Reports

JasperReports-Dateien für die Anwender-Drucke. Querschnitts-Konventionen
(Multi-Select-Parameter, `$P{}` vs `$P!{}`, „Seite X von Y", Sub-Datasets,
positionType=Float, …) stehen iDempiere-weit in
`~/iDempiere-development/docs/jasperreports-knowhow.md`.

**Konvention (ab Mai 2026): ein AD_Process pro Report, sprachneutral.**
Die englische jrxml ist der Default (Dateiname ohne Sprach-Suffix).
Die deutsche Variante hat das Suffix `_de` und wird pro Installation
durch Anpassung des `JasperReport`-Pfads in `AD_Process` aktiviert
(siehe `setup/install_de_reports.sql` bzw. `docs/Installation_de.md`,
Abschnitt „Reports — Sprache umstellen").

| Datei                               | Zweck                                                                                         | Aufruf-Parameter                                                               |
| ----------------------------------- | --------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `WorkshopDossier.jrxml`             | Werkstatt-Druckmappe pro Auftrag (EN, Default)                                                | `$P{Record_ID}` = `BXS_WorkOrder_ID`                                           |
| `WorkshopDossier_de.jrxml`          | wie oben, DE                                                                                  | dito                                                                           |
| `AssetDossier.jrxml`                | Anlagenakte: Stammdaten + anstehende Termine + offene Fehlerberichte + Historie (EN, Default) | `$P{Record_ID}` = `BXS_Asset_ID`                                               |
| `AssetDossier_de.jrxml`             | wie oben, DE                                                                                  | dito                                                                           |
| `AssetStatusOverview.jrxml`         | Flottenweite Status-Übersicht aller Anlagen, gruppiert nach Klasse (EN, Default)              | `AssetClassIDs` (Multi-Select, optional), `OnlyWithOpenItems` (Y/N, default Y) |
| `AssetStatusOverview_de.jrxml`      | wie oben, DE                                                                                  | dito                                                                           |

## Anlagenübersicht Status — Aufruf und Parameter

Anders als die record-scoped Reports (Anlagenakte, Werkstattmappe) wird die
Übersicht **menügesteuert** aufgerufen — kein `RECORD_ID`, dafür zwei Filter
über AD_Process_Para:

- **`AssetClassIDs`** — `Reference=Table` mit `is_multiselect: Y` (intern
  AD_Reference 200162 „Chosen Multiple Selection Table"),
  `AD_Reference_Value`=`BXS_AssetClass_Ref` (Validation-Table-Reference auf
  `BXS_AssetClass`, ebenfalls im 2Pack), leer = alle Klassen. SQL-Pattern für
  Multi-Select (`$P{}`+`$P!{}`) siehe
  `~/iDempiere-development/docs/jasperreports-knowhow.md`.
- **`OnlyWithOpenItems`** — `Reference=Yes-No`, Default `Y`. Wenn `Y`, werden
  nur Anlagen angezeigt, die mindestens einen offenen Fehlerbericht oder einen
  überfälligen Wartungstermin haben.

Der AD_Process-Eintrag ist in `2pack/source/spec/90-reports.yaml` als
`BXS_Print_AssetStatusOverview` definiert (sprachneutral, ein
Prozess pro Report); die beiden AD_Process_Para-Einträge hängen dort
unter `process_params:` und werden vom Generator
(`2pack/gen/assemble.py`, `emit_process_para`) inklusive `*_Trl`
mitgepackt.

Der Menü-Eintrag des Reports wird **automatisch erzeugt** und unter dem
Knoten „Anlagenbuch" eingehängt (Konvention, siehe unten).

## Menü-Konvention „Anlagenbuch"

Alle Anlagenbuch-Menüpunkte (Fenster wie Reports) hängen unter einem
Summary-Knoten **„Anlagenbuch"**, der ganz am Ende des Menübaums steht
(SeqNo 999 unter Root). Reihenfolge der Kinder:

| SeqNo | Eintrag                                                                      |
| ----- | ---------------------------------------------------------------------------- |
| 10    | Anlage (Hauptfenster)                                                        |
| 20    | Werkstattauftrag                                                             |
| 30    | Anlagenklasse (Stammdaten)                                                   |
| 40    | Wartungstermin-Typ (Stammdaten)                                              |
| 110+  | Print-Reports (Werkstattmappe / Anlagenakte / Statusübersicht jeweils DE+EN) |

Verkabelung: AD_Menu.Parent_ID/SeqNo werden vom Generator gesetzt
(siehe `2pack/gen/assemble.py` — `emit_menu`,
`emit_menu_root`). Neue Fenster bekommen optional eine
`menu: { seq: N }`-Sektion in ihrer Window-Spec; neue Prozesse, die im
Menü erscheinen sollen, ein `menu: { seq: N }` an der Process-Spec.
Buttons (Tab-Toolbar-Prozesse) brauchen kein `menu:`.

## Was die Skelette schon können

- Korporates Layout mit Brand-Header (dunkelblau) und Footer-Linie (gelb).
- Vollständige Header-Sektion mit Label/Value-Spalten (Auftragsdaten /
  Stammdaten der Anlage).
- Tabelle „Zu erledigende Positionen" / „Anstehende Termine" /
  „Offene Fehlerberichte" / „Historie" als `<jr:table>` mit
  embedded `<subDataset>` — eine JRXML-Datei pro Report, keine
  Subreport-Dateien nötig.
- Bestätigungs-Sektion in der Werkstattmappe (Tabelle für „erledigt /
  nicht erledigt"-Spalten + Rückgabedatum/Kosten/Beleg).
- Korrekte deutsche Datumsformate (`dd.MM.yyyy` und „d. Monat yyyy")
  bzw. EN-Pendants.
- SQL-Queries gegen das echte Datenmodell (joins gegen `BXS_AssetClass`,
  `BXS_ScheduleType`, `C_BPartner`, `C_BPartner_Location`, `AD_User`).

## Was in Jasper Studio noch zu tun ist

1. **Logo einbetten.** Die Reports erwarten `logo.png` im selben
   Verzeichnis. Mit dem aktuellen `onErrorType="Blank"` zeigen sie das
   Layout sauber auch ohne Logo.
2. **Schriften.** Die Skelette nutzen `SansSerif` als robusten Fallback.
   Auf Corporate Font umstellen, wenn vorhanden.
3. **Feinjustage Spaltenbreiten** in der Positionstabelle und in der
   Bestätigungstabelle der Werkstattmappe (gerade bei sehr langen
   Beleg-Nummern oder Termin-Bezeichnern).
4. **Print-When auf Zählerstand.** Die Spalte „LETZTER ZÄHLERSTAND" in
   `AssetDossier_*.jrxml` nutzt schon `printWhenExpression` auf
   `LastMeterReading != null`. Ggf. zusätzlich auf `AssetClass.C_UOM_ID`
   prüfen, falls man die Spalte komplett ausblenden will.
5. **Bestätigungs-Tabelle füllen** in `WorkshopDossier_*.jrxml`: aktuell
   nur Tabellen-Header. Zeilen für jede Position (1..N) mit Auslassungs-
   linien und Checkbox-Zellen (rechteckige Boxen mit `<rectangle>`)
   ergänzen, sobald die Anzahl Items geklärt ist (max. 10? dynamisch?).

## ⚠️ JasperReports-Version: 5.6.x-kompatibel bleiben

Die Reports werden **nicht** vorkompiliert ausgeliefert — iDempiere
übersetzt die jrxml bei der ersten Benutzung selbst. Die dafür genutzte
Engine ist die vom Plugin `de.bxservice.report` mitgelieferte
**JasperReports 5.6.1**, nicht die neuere Core-Version (6.x). Die jrxml
müssen daher gegen das **5.6.x-Schema** kompilieren.

Konkret: **keine Attribute/Elemente verwenden, die erst in JasperReports
6.x eingeführt wurden.** Klassische Falle ist `textAdjust="StretchHeight"`
(JR 6.0) — Jasper Studio schreibt das beim Speichern automatisch hinein.
Stattdessen das abwärtskompatible `isStretchWithOverflow="true"` benutzen,
das **5.6.x und 6.x** verstehen.

Symptom bei einem 6.x-only-Attribut: Der Druck öffnet das Viewer-Fenster,
zeigt aber **kein PDF** (0 Seiten) — meist ohne sichtbare Exception im
Server-Log, weil schon die XML-Schema-Validierung der jrxml scheitert.

Wer die Reports in Jasper Studio bearbeitet, sollte sie danach gegen eine
5.6.x-Engine gegenprüfen (z.B. die Jars aus `de.bxservice.report.libraries`),
bevor er ausliefert.

## Lokale Validierung

Die Skelette wurden mit dem im iDempiere-Source-Tree mitgelieferten
JasperReports kompiliert:

```bash
cd Anlagenbuch
java -cp <classpath> JrCompile reports/WorkshopDossier_de.jrxml
# Erfolg: schreibt WorkshopDossier_de.jasper neben das jrxml
```

Classpath siehe Helper im `scripts/`-Verzeichnis. Der dazugehörige
`AD_Process`-Eintrag, der die Reports aus iDempiere heraus aufruft,
liegt in `2pack/source/spec/90-reports.yaml`.

## Datenmodell der Reports

Die SQL-Queries stehen im jeweiligen `<queryString>`/`<subDataset>` der
JRXML-Datei. Für Übersicht hier die wichtigsten:

### Werkstattmappe — Hauptquery

```sql
SELECT wo.DocumentNo, wo.Name, wo.ScheduledDate, wo.CompletionDate,
       wo.WorkOrderStatus, wo.Description,
       a.Value, a.Name, a.SerialNo, a.Manufacturer, a.Model, a.YearBuilt,
       cl.Name AS AssetClassName,
       bp.Name AS WorkshopName, bploc.Phone AS WorkshopPhone,
       ud.Name AS DriverName,
       ui.Name AS InternalContactName, ui.Phone AS InternalContactPhone
FROM   BXS_WorkOrder wo
LEFT JOIN BXS_Asset a       ON a.BXS_Asset_ID = wo.BXS_Asset_ID
LEFT JOIN BXS_AssetClass cl ON cl.BXS_AssetClass_ID = a.BXS_AssetClass_ID
LEFT JOIN C_BPartner bp     ON bp.C_BPartner_ID = wo.Workshop_ID
LEFT JOIN C_BPartner_Location bplo ON bplo.C_BPartner_ID = bp.C_BPartner_ID AND bplo.IsActive='Y'
LEFT JOIN C_Location bploc  ON bploc.C_Location_ID = bplo.C_Location_ID
LEFT JOIN AD_User ud        ON ud.AD_User_ID = wo.Driver_ID
LEFT JOIN AD_User ui        ON ui.AD_User_ID = wo.InternalContact_ID
WHERE  wo.BXS_WorkOrder_ID = $P{BXS_WorkOrder_ID};
```

### Werkstattmappe — Items-Subdataset

```sql
SELECT woi.LineNo, i.DocumentNo, i.Type, i.Name, i.Description,
       i.ReportedDate, i.DueDate, i.Priority, i.EstimatedCost,
       u.Name AS ReporterName, st.Name AS ScheduleTypeName
FROM   BXS_WorkOrder_Item woi
JOIN   BXS_AssetItem i      ON i.BXS_AssetItem_ID = woi.BXS_AssetItem_ID
LEFT JOIN AD_User u         ON u.AD_User_ID = i.AD_User_ID
LEFT JOIN BXS_ScheduleType st ON st.BXS_ScheduleType_ID = i.BXS_ScheduleType_ID
WHERE  woi.BXS_WorkOrder_ID = $P{BXS_WorkOrder_ID}
ORDER BY woi.LineNo;
```

### Anlagenakte — Hauptquery

```sql
SELECT a.Value, a.Name, a.Manufacturer, a.Model, a.YearBuilt,
       a.SerialNo, a.CommissionDate, a.Location, a.AssetStatus, a.Note,
       a.LastMeterReading, a.LastMeterDate,
       cl.Name AS AssetClassName, cl.Category,
       u.Name AS UOMSymbol, user_a.Name AS UserName
FROM   BXS_Asset a
LEFT JOIN BXS_AssetClass cl ON cl.BXS_AssetClass_ID = a.BXS_AssetClass_ID
LEFT JOIN C_UOM u           ON u.C_UOM_ID = cl.C_UOM_ID
LEFT JOIN AD_User user_a    ON user_a.AD_User_ID = a.AD_User_ID
WHERE  a.BXS_Asset_ID = $P{BXS_Asset_ID};
```

### Anlagenakte — Anstehende Termine, Offene Fehlerberichte, Historie

Siehe drei `<subDataset>`-Blöcke in `AssetDossier_de.jrxml` (DE-Spalten­namen)
bzw. `AssetDossier.jrxml` (EN-Spaltennamen, Default).

## Deployment in iDempiere

Heute ist Variante 2 (Drop-Ordner + `AD_Process` aus dem 2Pack) der
ausgelieferte Weg. Alternativen für künftige Releases:

1. **AD_Process mit `JasperReport=…`-Attribut** auf einen Pfad im
   Plugin-Bundle. Erfordert ein eigenes Plugin
   (`de.bxservice.anlagenbuch.reports`) mit den `.jasper`-Dateien im
   Resource-Pfad.
2. **JasperBridge-Drop-Ordner (aktiv).** JRXML/jasper liegen unter
   `$IDEMPIERE_HOME/reports/`; der `AD_Process` zeigt auf den
   Dateinamen. `install.sh` kopiert die Dateien dorthin.
3. **Einbettung ins 2Pack.** JRXML-Inhalte als BLOB oder Resource-File
   ausliefern. Komplexer; lohnt erst bei Plugin-Variante.
