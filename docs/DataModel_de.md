# Anlagenbuch — Datenmodell

Stand: dritter Entwurf (FailureMode/Severity entfernt, MeterUnit über `C_UOM`, Fenster-Struktur überarbeitet). Tabellen-Präfix `BXS_`. Englische Bezeichner für Tabellen und Spalten, deutsche Labels in der UI.

iDempiere-Standardspalten (`AD_Client_ID`, `AD_Org_ID`, `IsActive`, `Created`, `CreatedBy`, `Updated`, `UpdatedBy`, `<Tablename>_UU`) sind in den Spaltenlisten unten **weggelassen** und werden in jeder Tabelle als gegeben angenommen.

## 1. Übersicht (ER-Skizze)

```
                              C_BPartner             C_Invoice
                                   ▲                      ▲
                                   │ Workshop_ID          │ Invoice_ID
                                   │                      │
   BXS_AssetClass ─┐               │                      │
       │           ▼               │                      │
   C_UOM     BXS_Asset ◀──────── BXS_WorkOrder ◀── BXS_WorkOrder_Item
                  ▲                                       │
                  │                                       │ Item_ID
                  └──────── BXS_AssetItem ◀───────────────┘
                                 │
                                 ├── Type ∈ {Defect, Schedule, Status}
                                 │
                                 └──▶ BXS_ScheduleType   (nur Type=Schedule)

   Listen (AD_Reference): AssetStatus, ItemType, ItemStatus,
                          WorkOrderStatus, Priority
```

## 2. Tabellen

### 2.1 BXS_Asset

Stammdaten eines verwalteten Objekts. Eine Tabelle für alle Klassen.

| Spalte              | Typ                 | Pflicht | Bemerkung                                            |
| ------------------- | ------------------- | ------- | ---------------------------------------------------- |
| `BXS_Asset_ID`      | ID                  | ja      | PK                                                   |
| `Value`             | String(40)          | ja      | Suchschlüssel, z.B. „LKW-MB-2078"                    |
| `Name`              | String(120)         | ja      | Anzeigename                                          |
| `Description`       | Text                | nein    |                                                      |
| `BXS_AssetClass_ID` | FK → BXS_AssetClass | ja      | Fahrzeug / Stapler / Anlage / IT / Immobilie         |
| `AssetStatus`       | List                | ja      | InService / OutOfService / Disposed                  |
| `Manufacturer`      | String(60)          | nein    |                                                      |
| `Model`             | String(60)          | nein    |                                                      |
| `SerialNo`          | String(40)          | nein    | bei Fahrzeugen die FIN                               |
| `YearBuilt`         | Number(4)           | nein    |                                                      |
| `CommissionDate`    | Date                | nein    | Inbetriebnahme                                       |
| `M_Resource_ID`     | FK → M_Resource     | nein    | optional, falls dispositionsrelevant                 |
| `AD_User_ID`        | FK → AD_User        | nein    | Stammnutzer (z.B. fester Fahrer)                     |
| `Location`          | String(120)         | nein    | Standort, frei                                       |
| `LastMeterReading`  | Number (virtual)    | nein    | calculated: jüngster `MeterReading` aller AssetItems |
| `LastMeterDate`     | Date (virtual)      | nein    | calculated: zugehöriges Datum                        |
| `Note`              | Text                | nein    |                                                      |

UI: Wenn `BXS_AssetClass.C_UOM_ID` leer ist (z.B. Immobilie), werden `LastMeterReading`/`LastMeterDate` ausgeblendet (Display Logic). Das Kennzeichen wird bei Fahrzeugen Teil von `Name` bzw. `Value` (z.B. „KR-JB 2078 Mercedes Atego").

`LastMeterReading` und `LastMeterDate` sind als Virtual Columns realisiert (iDempiere `IsVirtualColumn=Y` mit SQL-Subquery auf `BXS_AssetItem.MeterReading` mit `MAX` über `MeterDate`/`CompletionDate`/`ReportedDate`).

### 2.2 BXS_AssetClass

Fachliche Anlagen-Klasse. Pro Tenant frei erweiterbar (z.B. mehrere LKW-Klassen für unterschiedliche TÜV-Intervalle). Verhalten/Anzeigelogik liegt eine Stufe darüber in `Category`.

| Spalte              | Typ        | Pflicht | Bemerkung                                                    |
| ------------------- | ---------- | ------- | ------------------------------------------------------------ |
| `BXS_AssetClass_ID` | ID         | ja      | PK                                                           |
| `Value`             | String(40) | ja      |                                                              |
| `Name`              | String(60) | ja      |                                                              |
| `Description`       | Text       | nein    |                                                              |
| `Category`          | List       | ja      | `BXS_AssetCategory` — Vehicle / Equipment / Stationary / Building / IT / Other. Steuert UI-Verhalten. |
| `C_UOM_ID`          | FK → C_UOM | nein    | Einheit für Zählerstand. Leer ⇒ Asset hat keinen Zählerstand |

**Kategorie-Verhalten** (Liste `BXS_AssetCategory`, fest):

| Wert         | Anwendung | UI / Workflow |
|--------------|-----------|---------------|
| `Vehicle`    | Fahrzeuge und große Maschinen mit Zähler (LKW, PKW, Stapler, Kehrmaschine) | Zählerstand sichtbar; Bringer im Werkstattauftrag empfohlen; Standort wechselt |
| `Equipment`  | Mobile Kleingeräte ohne Zähler (Sackkarre, Hubwagen, Werkzeug) | Zählerstand optional; Standort wechselt |
| `Stationary` | Fest installierte Betriebstechnik (Rolltor, Feuerlöscher, Heizung) | Zählerstand ausgeblendet; Standort fest |
| `Building`   | Immobilie / Gebäudeteil | Adresse statt Standort; eigene Reports später möglich |
| `IT`         | IT-Hardware mit Inventarcharakter (Server, Switch, Drucker) | optional Betriebsstunden |
| `Other`      | Auffangkategorie | keine Sonderlogik |

Initial-Datensätze (im 2Pack ausgeliefert). Der `Value` folgt einem
nummerischen Schema in Zehnerschritten: **1xx** KfZ (motorisierte
Straßenfahrzeuge), **2xx** andere Fahrzeuge/Equipment mit Fahrzeug­charakter
(Stapler, Anhänger, Hubwagen), **3xx** Equipment/Stationary, **4xx** IT,
**5xx** Immobilie. Damit bleibt die Klassen-Liste sortierbar, wenn der
Anwender feinere Untergliederungen anlegt.

| Value       | Name              | Category   | Bemerkung                                                                   |
| ----------- | ----------------- | ---------- | --------------------------------------------------------------------------- |
| `100`       | Fahrzeug          | Vehicle    | KfZ (motorisierte Straßenfahrzeuge): LKW, PKW; eigene Klassen 1xx ableitbar |
| `200`       | Stapler           | Vehicle    | Andere Fahrzeuge mit Equipment-Charakter (Stapler, Anhänger, Hubwagen); UVV |
| `300`       | Technische Anlage | Stationary | Sonstige Betriebstechnik: Rolltore, Feuerlöscher                            |
| `400`       | IT-Gerät          | IT         | Server, Switch, Drucker                                                     |
| `500`       | Immobilie         | Building   | Gebäudeteile, Gewerke                                                       |

`C_UOM_ID` (Kilometer/Stunde) wird beim Kunden manuell zugeordnet, weil die UOM-IDs tenant-spezifisch sind.

### 2.3 BXS_AssetItem

**Zentrale Tabelle.** Vereinigt drei fachliche Konzepte über das Diskriminator-Feld `Type`:

- `Defect` — Fehlerbericht: jemand hat einen Mangel festgestellt.
- `Schedule` — Wartungstermin: ein Termin (TÜV, SP, UVV, Garantie-Ablauf, …) ist zu einem Datum fällig.
- `Status` — Statusbericht: Zustandsmomentaufnahme ohne Mangel, häufig bei Erstaufnahme oder Sichtung.

Pro Type werden in der UI andere Felder eingeblendet (Display Logic). Items werden nicht in einem eigenen Hauptfenster gepflegt, sondern als Detail-Tabs am Asset (siehe Abschnitt 4).

| Spalte                | Typ                   | Pflicht | Defect | Schedule | Status | Bemerkung                                            |
| --------------------- | --------------------- | ------- |:------:|:--------:|:------:| ---------------------------------------------------- |
| `BXS_AssetItem_ID`    | ID                    | ja      | •      | •        | •      | PK                                                   |
| `DocumentNo`          | String(30)            | ja      | •      | •        | •      | iDempiere-Sequence pro Type                          |
| `BXS_Asset_ID`        | FK → BXS_Asset        | ja      | •      | •        | •      |                                                      |
| `Type`                | List                  | ja      | •      | •        | •      | Defect / Schedule / Status                           |
| `Name`                | String(60)            | ja      | •      | •        | •      | Kurzbeschreibung für Listen                          |
| `Description`         | Text                  | nein    | •      | ○        | •      | Langtext                                             |
| `ReportedDate`        | Date                  | ja      | •      | ○        | •      | Tag der Feststellung / Erfassung                     |
| `DueDate`             | Date                  | –       | –      | •        | –      | Fälligkeit (nur Schedule)                            |
| `AD_User_ID`          | FK → AD_User          | nein    | •      | –        | •      | Melder / Erfasser                                    |
| `Priority`            | List                  | nein    | •      | –        | –      | Low / Medium / High                                  |
| `BXS_ScheduleType_ID` | FK → BXS_ScheduleType | –       | –      | •        | –      | TÜV/SP/UVV/Garantie/…                                |
| `IsMandatory`         | Boolean (virtual)     | –       | –      | •        | –      | abgeleitet aus `BXS_ScheduleType.IsMandatoryDefault` |
| `MeterReading`        | Number                | nein    | •      | •        | •      | Zählerstand bei Feststellung/Erledigung              |
| `EstimatedCost`       | Amount                | nein    | •      | •        | –      | Kostenschätzung                                      |
| `ItemStatus`          | List                  | ja      | •      | •        | •      | Open / Done / Cancelled / Skipped                    |
| `CompletionDate`      | Date                  | nein    | •      | •        | –      | bei Done gesetzt (Status: =`ReportedDate`)           |
| `BXS_WorkOrder_ID`    | FK → BXS_WorkOrder    | nein    | •      | •        | –      | Auftrag, der dieses Item erledigt hat                |
| `NextItem_ID`         | FK → BXS_AssetItem    | nein    | –      | •        | –      | Folge-Schedule, wenn generiert                       |
| `Note`                | Text                  | nein    | •      | •        | •      |                                                      |

Legende: • Pflichtfeld oder typischerweise relevant, ○ optional, – wird in der UI für diesen Type ausgeblendet.

**Lifecycle:**

- **Defect:** angelegt mit `ItemStatus=Open`. Schließt entweder manuell (Selbstbehebung, dann `Done` mit `CompletionDate`) oder über einen Werkstattauftrag (Skript setzt `Done`, `CompletionDate`, `BXS_WorkOrder_ID`). `Cancelled` für Falschmeldungen.
- **Schedule:** angelegt mit `ItemStatus=Open`. Wird über Schließen-Button (Skript) auf `Done` gesetzt; gleichzeitig erzeugt das Skript einen neuen Schedule mit Default-Werten und setzt `NextItem_ID`. `Skipped` für entfallende Termine (z.B. Asset wurde verkauft, bevor TÜV fällig war).
- **Status:** wird beim Anlegen direkt auf `Done` gesetzt, `CompletionDate=ReportedDate`. Nie `Open`.

**Folgetermin-Datum:** Beim automatischen Anlegen eines Folge-Schedules wird `DueDate` vorbelegt mit:

```
DueDate_neu = ersterTagDesMonats(CompletionDate_alt) + ScheduleType.DefaultIntervalMonths
```

Begründung: TÜV/SP/UVV-Intervalle laufen in der Praxis vom Prüfdatum aus, nicht vom alten Soll-Datum. Auf den Monatsersten gerundet, weil die TÜV-Plakette monatsgenau ist.

### 2.4 BXS_ScheduleType

Termin-Typ-Stammdaten.

| Spalte                  | Typ                 | Pflicht | Bemerkung                                   |
| ----------------------- | ------------------- | ------- | ------------------------------------------- |
| `BXS_ScheduleType_ID`   | ID                  | ja      | PK                                          |
| `Value`                 | String(40)          | ja      | z.B. `TUV`, `SP`, `UVV`, `WARRANTY`         |
| `Name`                  | String(60)          | ja      | Anzeigename                                 |
| `Description`           | Text                | nein    |                                             |
| `DefaultIntervalMonths` | Number              | nein    | Vorschlag für Folgetermin (z.B. 12, 24)     |
| `IsMandatoryDefault`    | Boolean             | ja      | Default für Pflicht-Flag bei neuen Terminen |
| `BXS_AssetClass_ID`     | FK → BXS_AssetClass | nein    | falls nur für eine Klasse relevant          |

Initial-Datensätze: `TUV` (12 Monate, Pflicht, Fahrzeug), `SP` (12 Monate, Pflicht, Fahrzeug), `UVV` (12 Monate, Pflicht, Stapler), `WARRANTY` (variabel, Kür), `INSPECTION` (frei, Kür).

### 2.5 BXS_WorkOrder

Werkstattauftrag.

| Spalte               | Typ             | Pflicht | Bemerkung                                                                                          |
| -------------------- | --------------- | ------- | -------------------------------------------------------------------------------------------------- |
| `BXS_WorkOrder_ID`   | ID              | ja      | PK                                                                                                 |
| `DocumentNo`         | String(30)      | ja      | iDempiere-Sequence                                                                                 |
| `BXS_Asset_ID`       | FK → BXS_Asset  | ja      |                                                                                                    |
| `Name`               | String(60)      | ja      | Kurzbeschreibung für Listen, z.B. „TÜV + Klappe + Reifen"                                          |
| `Workshop_ID`        | FK → C_BPartner | ja      | Werkstatt                                                                                          |
| `Driver_ID`          | FK → AD_User    | nein    | Bringer / Fahrer (Ressource), die das Fahrzeug zur Werkstatt bringt                                |
| `InternalContact_ID` | FK → AD_User    | nein    | Ansprechpartner intern für Rückfragen der Werkstatt; Telefonnummer ergibt sich aus `AD_User.Phone` |
| `ScheduledDate`      | Date            | nein    | geplanter Werkstatt-Termin                                                                         |
| `ActualDate`         | Date            | nein    | tatsächlicher Beginn                                                                               |
| `CompletionDate`     | Date            | nein    | Rückgabedatum                                                                                      |
| `EstimatedCost`      | Amount          | nein    | Summe der Item-Schätzungen oder manuell                                                            |
| `ActualCost`         | Amount          | nein    | finale Kosten                                                                                      |
| `ExternalDocumentNo` | String(30)      | nein    | Belegnummer der Werkstatt (Rechnung oder Auftragsbestätigung); für freie Erfassung                 |
| `C_Invoice_ID`       | FK → C_Invoice  | nein    | Rechnungsverknüpfung in iDempiere (sobald Rechnung erfasst)                                        |
| `WorkOrderStatus`    | List            | ja      | Draft / Released / Completed / Cancelled                                                           |
| `Description`        | Text            | nein    |                                                                                                    |
| `Note`               | Text            | nein    |                                                                                                    |

Detail-Tab: `BXS_WorkOrder_Item` (siehe 2.6). Eine einzige gemischte Liste — Fehlerberichte und Wartungstermine erscheinen gemeinsam, sortiert nach `LineNo`.

**Buttons / Prozesse am Werkstattauftrag:**

1. *Offene Einträge übernehmen* (`AD_Process` mit Skript): Trägt automatisch alle `BXS_AssetItem` desselben Assets mit `Type ∈ {Defect, Schedule}` und `ItemStatus=Open` als Werkstattpositionen ein, die noch nicht als Position vorhanden sind. Default `IsResolved=Y`. Der Disponent kann anschließend einzelne Zeilen löschen oder `IsResolved=N` setzen.
2. *Auftrag abschließen* (`AD_Process` mit Skript): siehe unten.

**Abschluss-Skript:**

1. alle verknüpften Items mit `IsResolved=Y` auf `ItemStatus=Done` setzen, `CompletionDate=today`, `BXS_WorkOrder_ID` setzen.
2. Items mit `IsResolved=N` bleiben offen (stehen für nächsten Auftrag bereit).
3. Für jedes geschlossene Item mit `Type=Schedule`: einen neuen `BXS_AssetItem`-Datensatz mit denselben Stammdaten anlegen, `DueDate = ersterTagDesMonats(CompletionDate) + ScheduleType.DefaultIntervalMonths`, `ItemStatus=Open`, `NextItem_ID` der alten Zeile setzen.
4. `WorkOrderStatus=Completed` und `CompletionDate=today` am Werkstattauftrag setzen.

Dieselbe Schedule-Folgetermin-Logik gilt, wenn ein Schedule-Item *außerhalb* eines Werkstattauftrags geschlossen wird (eigener Schließen-Button am Item-Detail-Tab).

### 2.6 BXS_WorkOrder_Item

Werkstattposition (Verknüpfungstabelle), abgebildet als Detail-Tab am Werkstattauftrag.

| Spalte                  | Typ                | Pflicht | Bemerkung                                             |
| ----------------------- | ------------------ | ------- | ----------------------------------------------------- |
| `BXS_WorkOrder_Item_ID` | ID                 | ja      | PK                                                    |
| `BXS_WorkOrder_ID`      | FK → BXS_WorkOrder | ja      | Parent                                                |
| `BXS_AssetItem_ID`      | FK → BXS_AssetItem | ja      | nur Items mit Type ∈ {Defect, Schedule} sind sinnvoll |
| `IsResolved`            | Boolean            | ja      | Default `Y`                                           |
| `LineNo`                | Number             | nein    | Sortierung                                            |
| `Note`                  | Text               | nein    | Werkstatt-Anmerkung pro Position                      |

Unique-Constraint: `(BXS_WorkOrder_ID, BXS_AssetItem_ID)` — ein Item kann nicht zweimal in denselben Auftrag.

Validierung (Skript-Callout beim Hinzufügen): `BXS_AssetItem.BXS_Asset_ID` muss zu `BXS_WorkOrder.BXS_Asset_ID` passen, und `Type` darf nicht `Status` sein.

## 3. Listen (`AD_Reference`)

Wertelisten als iDempiere-Listen-Referenzen statt eigene Tabellen, weil reine Enumerationen ohne weitere Attribute:

| Liste                 | Werte                                 |
| --------------------- | ------------------------------------- |
| `BXS_AssetStatus`     | InService, OutOfService, Disposed     |
| `BXS_ItemType`        | Defect, Schedule, Status              |
| `BXS_ItemStatus`      | Open, Done, Cancelled, Skipped        |
| `BXS_WorkOrderStatus` | Draft, Released, Completed, Cancelled |
| `BXS_Priority`        | Low, Medium, High                     |

Zählerstand-Einheit (`C_UOM`) wird **nicht** als Liste gepflegt, sondern über die iDempiere-Standard-Tabelle `C_UOM` referenziert (in `BXS_AssetClass`).

## 4. Fenster

Das Modul liefert **vier** iDempiere-Fenster aus:

### 4.1 Fenster „Anlagenklasse" (`BXS_AssetClass`)

Einfaches Stammdaten-Fenster, ein Tab. Pflege selten — nur bei Einführung und bei Bedarf erweitern.

### 4.2 Fenster „Wartungstermin-Typ" (`BXS_ScheduleType`)

Einfaches Stammdaten-Fenster, ein Tab. Pflege selten.

### 4.3 Fenster „Anlage" (`BXS_Asset`)

Hauptfenster für die tägliche Arbeit. Tab-Struktur:

| Tab            | Tabelle / Filter                            | Zweck                                             |
| -------------- | ------------------------------------------- | ------------------------------------------------- |
| Anlage         | `BXS_Asset`                                 | Stammdaten                                        |
| Fehlerbericht  | `BXS_AssetItem` mit Default `Type=Defect`   | Mängel erfassen, schließen                        |
| Wartungstermin | `BXS_AssetItem` mit Default `Type=Schedule` | Termine erfassen, schließen, Folgetermin auslösen |
| Status         | `BXS_AssetItem` mit Default `Type=Status`   | Statusberichte erfassen (direkt erledigt)         |

Beim Anlegen wird `Type` aus dem Tab-Default gesetzt und ist anschließend Read-Only. Felder pro Tab werden über Display Logic auf den jeweiligen Type-Wert gefiltert.

### 4.4 Fenster „Werkstattauftrag" (`BXS_WorkOrder`)

Tab-Struktur:

| Tab               | Tabelle / Filter                                                                                                    | Zweck                                        |
| ----------------- | ------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| Werkstattauftrag  | `BXS_WorkOrder`                                                                                                     | Kopfdaten                                    |
| Werkstattposition | `BXS_WorkOrder_Item`                                                                                                | Items, die im Auftrag erledigt werden sollen |
| Offene Einträge   | `BXS_AssetItem` mit Filter `BXS_Asset_ID=@Header@` AND `ItemStatus=Open` AND `Type ∈ {Defect, Schedule}`, Read-Only | Übersicht — was ist am Asset gerade offen?   |

Buttons am Header-Tab: *Offene Einträge übernehmen*, *Auftrag abschließen* (siehe 2.5).

Der Read-Only-Tab „Offene Einträge" gibt der Disponentin den Überblick beim Anlegen eines Auftrags. Praxis: Button *Offene Einträge übernehmen* trägt alles ein, dann werden einzelne Zeilen gelöscht/markiert, was nicht mit zur Werkstatt soll.

**Field-Group-Aufteilung im Header-Tab** (über `AD_FieldGroup`):

| Field Group        | Felder                                                                                                            |
| ------------------ | ----------------------------------------------------------------------------------------------------------------- |
| Auftragserstellung | `BXS_Asset_ID`, `Workshop_ID`, `Driver_ID`, `InternalContact_ID`, `ScheduledDate`, `EstimatedCost`, `Description` |
| Nach Rückkehr      | `CompletionDate`, `ActualCost`, `ExternalDocumentNo`, `C_Invoice_ID`, `WorkOrderStatus`, `Note`                   |

Erleichtert das Ausfüllen — die Disponentin sieht beim Anlegen oben nur die relevanten Felder und füllt nach der Rückkehr unten aus.

## 5. Mapping zu Normen

| Norm-Konzept                        | Umsetzung                                                                              |
| ----------------------------------- | -------------------------------------------------------------------------------------- |
| ISO 14224 — Equipment Class         | `BXS_Asset.BXS_AssetClass_ID`                                                          |
| ISO 14224 — Equipment Hierarchy     | bewusst nicht abgebildet                                                               |
| ISO 14224 — Failure Mode / Severity | bewusst nicht abgebildet (zu kleine Flotte)                                            |
| DIN 31051                           | konzeptionell (Defect ↔ Instandsetzung, Schedule ↔ Wartung/Inspektion); nicht als Feld |
| VDI 2890 — Wartungsplanung          | `BXS_AssetItem` (Type=Schedule) + `BXS_ScheduleType`                                   |

## 6. Indizes (Empfehlung)

- `BXS_AssetItem (BXS_Asset_ID, Type, ItemStatus)` — der Brot-und-Butter-Index für Asset-Akte und Tab-Filter.
- `BXS_AssetItem (Type, DueDate, ItemStatus)` — globale Fälligkeitsliste der Wartungstermine.
- `BXS_AssetItem (Type, ItemStatus, ReportedDate)` — globale Liste offener Fehlerberichte.
- `BXS_WorkOrder (BXS_Asset_ID, WorkOrderStatus)` — für Asset-Akte.
- `BXS_WorkOrder_Item (BXS_AssetItem_ID)` — Reverse-Lookup „in welchen Aufträgen war dieses Item?".

## 7. Offene Punkte

### Sequence pro Type (FEH-…, TER-…, STA-…) — Implementierung

iDempiere kennt pro Tabelle genau **eine** `AD_Sequence`. Drei verschiedene Präfixe je nach `Type`-Wert sind mit Standard-Bordmitteln nicht direkt abbildbar.

**Lösung:** Drei separate `AD_Sequence`-Datensätze (`BEA`, `TER`, `STA`) und eine BeanShell-`AD_Rule`, die als **ModelValidator** auf `BXS_AssetItem` registriert wird (Rule Type = „Model Validator", Event Type = „Table Before New"). Das Skript zieht je nach `Type` die passende Sequence und setzt `DocumentNo`.

ModelValidator statt Callout, weil Callouts schon beim Feldwechsel im Tab feuern können — bricht der Anwender die Eingabe danach ab, ist die Sequence-Nummer verbraucht und es entsteht eine Lücke. ModelValidator-Events (`TYPE_BEFORE_NEW`) feuern erst beim echten `PO.save()`, also lückenlos.

`AD_Rule` mit Rule Type „Model Validator" funktioniert in iDempiere ohne eigenes OSGi-Plugin — BeanShell reicht. Skript-Aufwand: ~10 Zeilen.
