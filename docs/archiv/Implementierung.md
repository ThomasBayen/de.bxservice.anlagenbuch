# Anlagenbuch — Implementierungs-Briefing

Adressat: Programmier-KI, die das Anlagenbuch (2Pack + JRXML + Skripte) umsetzt. Voraussetzung: `Konzept.md` und `Datenmodell.md` gelesen.

## 1. Auftrag

Anlagenbuch als auslieferbares Paket erstellen. Installation läuft über das Standard-2Pack-Fenster eines bestehenden iDempiere — kein Server-Zugriff, kein Plugin-Build nötig.

## 2. Lieferumfang

| Artefakt                              | Beschreibung                                                                        | Status |
| ------------------------------------- | ----------------------------------------------------------------------------------- | ------ |
| `pack/Anlagenbuch.zip`                | 2Pack-Paket mit allen DB-Objekten, Fenstern, Listen, Sequenzen, Prozessen, Rules    | offen  |
| `scripts/*.bsh`                       | BeanShell-Quellen der `AD_Rule`-Datensätze (versioniert, im 2Pack referenziert)     | offen  |
| `reports/Anlagenakte_de.jrxml`        | JasperReport Asset-Akte, deutsch                                                    | offen  |
| `reports/Anlagenakte_en.jrxml`        | JasperReport Asset-Akte, englisch                                                   | offen  |
| `reports/Werkstattmappe_de.jrxml`     | JasperReport Werkstattmappe, deutsch (Vorlage: `docs/Werkstattmappe_Beispiel.pdf`)  | offen  |
| `reports/Werkstattmappe_en.jrxml`     | JasperReport Werkstattmappe, englisch                                               | offen  |
| `import/AssetImport_Template.csv`     | CSV-Vorlage für Erstbefüllung aus `M_Resource`                                      | offen  |
| `import/AssetImport_Mapping.md`       | Beschreibung der Spalten und der Übernahme-Logik aus `M_Resource`                   | offen  |
| `docs/Installations_Anleitung.md`     | Schritt-für-Schritt: 2Pack importieren, Sequence-Bereiche prüfen, CSV importieren   | offen  |

## 3. Zielumgebung

- **iDempiere-Version: iDempiere 11.** Tabellen-DDL der 2Pack-XML muss zu dieser Version passen. Der lokal verfügbare Standard-Entwicklungsserver läuft auf 11.
- **Datenbank:** PostgreSQL (iDempiere-Standard). Oracle wird nicht unterstützt.
- **Java:** das von iDempiere 11 vorgegebene JDK.
- **Mandant:** Multi-Tenant-fähig — kein Hardcoding einer `AD_Client_ID`. **Für Beispiele und Tests den vorhandenen GardenWorld-Mandanten verwenden** (vorhandene Datensätze wo sinnvoll einbinden, ergänzende Datensätze ruhig hinzufügen).
- **Test-Einspielung autonom:** Die Programmier-KI soll das fertige 2Pack selbst gegen den lokalen Standard-Server einspielen und die Akzeptanzkriterien dort durchprüfen. Login- und Endpunkt-Daten stehen im Profil von `csv-import-ods` (siehe §10).

## 4. Repo-Struktur (zu erstellen)

```
Anlagenbuch/
├── docs/                  (vorhanden)
├── src/                   (vorhanden — PDF-Quellen, nicht Plugin-Code)
├── pack/                  (NEU — 2Pack-XML und gebauter ZIP)
│   ├── source/            (XML-Quelle, versioniert)
│   └── build.sh           (zippt source/ → Anlagenbuch.zip)
├── scripts/               (NEU — BeanShell-Skripte als eigene Dateien, im 2Pack referenziert)
├── reports/               (NEU — jrxml-Quellen)
├── import/                (NEU — CSV-Vorlagen + Mapping-Doku)
└── uuids.csv              (NEU — fixierte UUIDs aller Objekte; siehe §5)
```

## 5. UUID-Strategie

Alle Objekte (Tabellen, Spalten, Fenster, Tabs, Felder, Listen, List-Werte, Sequenzen, Prozesse, Rules, Berichte, Initialdatensätze) erhalten **einmalig generierte, im Repo fixierte UUIDs**. `uuids.csv` ist die zentrale Wahrheit:

```
ObjectType,Name,UUID
AD_Table,BXS_Asset,a7b3c1d4-...
AD_Column,BXS_Asset.Value,...
AD_Window,BXS_Asset_Window,...
AD_Reference,BXS_AssetStatus,...
...
```

Begründung: Bei einem späteren Migrationspfad zu einem OSGi-Plugin sorgen stabile UUIDs dafür, dass das Plugin-`2Pack` die bereits angelegten Datensätze **erkennt und ergänzt**, statt zu duplizieren.

## 6. Sequence-Konventionen

Belegnummern in den Mockups:

| Type            | Präfix-Beispiel     | AD_Sequence-Name      | Startwert |
| --------------- | ------------------- | --------------------- | --------- |
| Fehlerbericht   | `FEH-2026-00184`    | `BXS_AssetItem_Defect`   | 1         |
| Wartungstermin  | `TER-2026-00412`    | `BXS_AssetItem_Schedule` | 1         |
| Statusbericht   | `STA-2026-00033`    | `BXS_AssetItem_Status`   | 1         |
| Werkstattauftrag| `WAU-2026-00031`    | `BXS_WorkOrder`          | 1         |

Format: `{Präfix}-{Jahr}-{5-stellig}`. Jahr aus `ReportedDate` bzw. `Created`. ModelValidator-`AD_Rule` (siehe Datenmodell §7) zieht die richtige Sequence anhand `Type`.

## 7. Initialdaten (im 2Pack enthalten)

### `BXS_AssetClass`
Siehe Datenmodell §2.2. Fünf Datensätze mit nummerischem `Value`-Schema: `100` (Fahrzeug/KfZ), `200` (Stapler/andere Fahrzeuge), `300` (Technische Anlage), `400` (IT-Gerät), `500` (Immobilie). `Value` ist kein Identifier mehr — in FK-Anzeigen erscheint nur der `Name`.

### `BXS_ScheduleType`
Siehe Datenmodell §2.4. Fünf Datensätze: `TUV`, `SP`, `UVV`, `WARRANTY`, `INSPECTION`.

### `AD_Reference` (Listen)
Siehe Datenmodell §3. Fünf Listen mit Werten: `BXS_AssetStatus`, `BXS_ItemType`, `BXS_ItemStatus`, `BXS_WorkOrderStatus`, `BXS_Priority`. Pro Wert: technischer `Value` und sprachneutrales `Name`-Feld; deutsche Übersetzung der `Name`-Felder über `AD_Ref_List_Trl`.

### Übersetzungen
Für alle `AD_Element`-, `AD_Field`-, `AD_Window`-, `AD_Tab`-, `AD_Process`-, `AD_Process_Para`- und `AD_Ref_List`-Datensätze deutsche Übersetzung über die jeweilige `*_Trl`-Tabelle (`AD_Language='de_DE'`). Default-`Name` und `PrintName` bleiben englisch.

## 8. Skripte (BeanShell, als `AD_Rule`)

Jede Logik als eigene `.bsh`-Datei im `scripts/`-Ordner; im 2Pack mit `Script` aus der Datei eingebettet.

| Skript                            | Trigger                              | Aufgabe                                                              |
| --------------------------------- | ------------------------------------ | -------------------------------------------------------------------- |
| `assetitem_documentno.bsh`        | ModelValidator `TYPE_BEFORE_NEW` auf `BXS_AssetItem` | Setzt `DocumentNo` aus passender Sequence je nach `Type` |
| `assetitem_close.bsh`             | Prozess „Eintrag schließen" am Item  | Schließt Item; bei `Schedule` Folgetermin anlegen, `NextItem_ID` setzen |
| `workorder_pull_open_items.bsh`   | Prozess „Offene Einträge übernehmen" | Trägt offene `Defect`/`Schedule`-Items des Assets als `BXS_WorkOrder_Item` ein, Default `IsResolved=Y` |
| `workorder_complete.bsh`          | Prozess „Auftrag abschließen"        | Items mit `IsResolved=Y` auf `Done` setzen, Folgetermine anlegen, `WorkOrderStatus=Completed` |
| `workorder_item_validate.bsh`     | Callout beim Hinzufügen einer Position | Asset-Match prüfen, `Type=Status` ausschließen                       |

Alle Skripte: idempotent wo möglich, Fehler über `org.compiere.process.ProcessInfo.addLog()` zurückmelden, keine direkten DB-Zugriffe ohne PO-Modelle.

## 9. Reports (JRXML)

### Asset-Akte (`Anlagenakte_de.jrxml`)
- Kopf: Anlage (Value/Name), Klasse, Hersteller/Modell, Bj., FIN/SerialNo, Inbetriebnahme, Standort, aktueller Zählerstand
- Abschnitt „Anstehende Termine": offene `Schedule`-Items, sortiert nach `DueDate`
- Abschnitt „Offene Fehlerberichte": offene `Defect`-Items, sortiert nach `Priority` desc, dann `ReportedDate`
- Abschnitt „Historie": erledigte Items + Werkstattaufträge der letzten 12 Monate, chronologisch
- Auszuliefern: `_de` (Default für JBKG) und `_en` (Community)

### Werkstattmappe (`Werkstattmappe_de.jrxml`)
- Vorlage: `docs/Werkstattmappe_Beispiel.pdf` (Layout 1:1 nachbauen)
- Datenquelle: `BXS_WorkOrder` + `BXS_WorkOrder_Item` + Items
- Header: Auftragsnummer, Datum, Anlage, Werkstatt, interne Ansprechpartnerin (Name + Telefon aus `AD_User.Phone`), Bringer
- Positionsliste: pro Item Belegnr., Typ, Kurzbeschreibung, Langtext, ggf. Priorität, Kostenschätzung
- Footer: Unterschrifts-Felder Werkstatt + Rückgabe-Disponentin
- Auszuliefern: `_de` und `_en`

## 10. CSV-Import (Erstbefüllung) und Beispieldaten

### Erstbefüllung beim Kunden
Quelle: vorhandene `M_Resource`-Datensätze (Fahrzeuge, Stapler etc., die heute in iDempiere als Ressourcen geführt werden). Zielmenge: ~30–80 Anlagen.

`AssetImport_Template.csv` mit Spalten:
- `Value` (Pflicht, eindeutig)
- `Name` (Pflicht)
- `BXS_AssetClass.Value` (`100`/`200`/`300`/`400`/`500`)
- `Manufacturer`, `Model`, `SerialNo`, `YearBuilt`, `CommissionDate`, `Location`
- `M_Resource.Value` (optional, FK-Lookup)
- `AD_User.Name` (Stammnutzer, optional)

### Beispieldaten für GardenWorld (Test- und Demo-Stand)
Beispiel-Datensatz mit ~5–10 Anlagen, einer Handvoll Fehlerberichten und Wartungsterminen, einem laufenden und einem abgeschlossenen Werkstattauftrag. **Bevorzugt vorhandene GardenWorld-Datensätze referenzieren** (z.B. `C_BPartner` für Werkstätten und `AD_User` für Bringer/interne Ansprechpartner). Wo nichts Passendes existiert, eigene Datensätze ergänzen — diese werden Teil des Beispiel-Pakets.

**Werkzeug:** `../../iDempiere-development/rest/csv-import-ods/` (ODS-Multi-Sheet-Importer, läuft auf demselben Host wie der iDempiere-Server, nutzt REST-API + `ImportCSVProcess`). Eine ODS-Datei `import/Beispiel_GardenWorld.ods` mit Konfig-Sheet und Datensheets pro Tabelle erstellen, Importreihenfolge im Konfig-Sheet hinterlegen. Cleanup-Skript analog zu `csv-import-ods/beispiel/cleanup.sh` mitliefern.

**Ablieferungs-Test:** Programmier-KI spielt 2Pack ein, importiert die ODS, durchläuft die Akzeptanzkriterien (§12) gegen den lokalen Standard-Server.

## 11. Berechtigungen

Eine Rolle `anlagenbuch` mit Schreibrechten auf alle vier Hauptfenster, im 2Pack mitgeliefert. Verfeinerte Rechtemodelle (Disponentin vs. Fahrer vs. Buchhaltung) bleiben einer späteren Iteration vorbehalten.

## 12. Akzeptanzkriterien (Mindest-Test)

Die Programmier-KI muss folgende Szenarien manuell oder als Skript-Test nachweisen:

1. 2Pack importiert sauber in eine leere iDempiere-Instanz; alle Fenster öffnen sich.
2. Anlage anlegen → Fehlerbericht am Detail-Tab erfassen → `DocumentNo=FEH-2026-00001`.
3. Wartungstermin anlegen, Type-Default aus Tab; mit „Erledigt"-Button schließen → Folgetermin entsteht mit korrektem `DueDate` (erster des Folgemonats + Intervall).
4. Werkstattauftrag anlegen, „Offene Einträge übernehmen" → Items erscheinen, `IsResolved=Y`.
5. Werkstattauftrag „Abschließen" → Items auf `Done`, ein Schedule-Folgetermin angelegt, `WorkOrderStatus=Completed`.
6. Anlagenakte druckt mit deutschen Labels und enthält die anstehenden Termine.

## 13. Offene Punkte / zu klärende Entscheidungen

- **CSV-Loader-Variante (Kunden-Erstbefüllung):** Standard-`AD_ImpFormat` oder eigener BeanShell-Importer? Hängt davon ab, wie viel FK-Auflösung in CSV nötig ist. Für die Beispiel-Daten in GardenWorld ist `csv-import-ods` gesetzt (§10).
- **Mehrfach-Sprachen am Asset-Stamm:** Aktuell nicht vorgesehen. Falls künftig Lieferanten-/Werkstatt-Reports auf Englisch laufen, ist `Name`-Feld in mehrere Sprachen zu erweitern — momentan nicht im Scope.
- **Mobile/Touch-tauglichkeit der Eingabemasken:** noch nicht getestet. Die Auslieferung ist Desktop-only.
- **Backup vor 2Pack-Import:** Hinweis in Installations-Anleitung; kein technischer Mechanismus.

## 14. Was ausdrücklich NICHT umgesetzt wird

- Kein OSGi-Plugin (siehe Konzept §4, Plugin-Option)
- Keine `ModelValidator`-Java-Klassen jenseits der BeanShell-Rules
- Keine eigene Fahrer-App / kein REST-Endpoint
- Keine automatische Vorgenerierung wiederkehrender Termine über das nächste hinaus
- Keine Kennzahlen-Reports (MTBF, MTTR, Verfügbarkeit, TCO)
