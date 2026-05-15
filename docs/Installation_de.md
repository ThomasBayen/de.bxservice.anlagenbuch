# Anlagenbuch — Installations-Anleitung

Voraussetzung: laufende iDempiere-11-Instanz mit PostgreSQL-Backend, Shell-Zugriff auf den Server bzw. das `idempiere-server/`-Verzeichnis.

## Inhalt der Auslieferung

| Datei                              | Zweck                                                                            |
| ---------------------------------- | -------------------------------------------------------------------------------- |
| `2pack/Anlagenbuch.zip`       | 2Pack-Archiv mit allen DB-Objekten, Fenstern, Listen, Sequenzen                  |
| `2pack/source/PackOut.xml`          | Quell-XML, im Repo zur Diff-Sicht                                                |
| `2pack/source/spec/*.yaml`          | Source-of-Truth-Specs für den Generator                                          |
| `2pack/source/assemble.py`         | YAML → PackOut.xml-Generator                                                     |
| `2pack/build.sh`                    | Wrapper, baut `2pack/Anlagenbuch.zip`                                       |
| `import/AssetImport_Template.csv`  | Vorlage für Erstbefüllung Anlagenstamm                                           |
| `import/AssetImport_Mapping.md`    | Spalten-Mapping-Doku                                                             |
| `example/JakobBayenKG/`            | Beispiel-Deployment mit Testdaten, Master-Rolle-Includes, Bootstrap-Skript       |
| `scripts/test/01_2pack_imports.sh`  | Schema-Smoke-Test (zählt Tabellen, Fenster usw.)                                 |
| `scripts/test/02_smoke_inserts.sh` | INSERT-Smoke-Test (legt Anlage + Fehlerbericht + Termin in GardenWorld an)       |
| `reports/README.md`                | Layout-/SQL-Skizze für Anlagenakte und Werkstattmappe                            |
| `docs/CHANGELOG.md`                | Versionsverlauf, inkl. was in welcher Version dazukam                            |

## Vorbereitung

1. **Backup der Ziel-Datenbank.** `pg_dump` reicht. PackIn ist transactional, aber bei Fehlern entsteht Halb-Importzustand auf AD-Ebene (Sequenzen, Auto-Trls). Backup erspart Stress.
2. **2Pack bauen** (falls nicht in Auslieferung enthalten):
   
   ```bash
   ./2pack/build.sh
   ```
   
   Erzeugt `2pack/Anlagenbuch.zip`.

## Import

### Variante A — über `migration/zip_2pack/` mit Server-Restart

Standard-Pfad bei iDempiere für Auto-Import beim Server-Start:

1. ZIP umbenennen in das vorgeschriebene Format `yyyymmddHHMM_<Client>_Anlagenbuch.zip`. Für die system-level Records ist `<Client>=SYSTEM` (das ist `AD_Client.Value` für `AD_Client_ID=0`):
   
   ```bash
   cp 2pack/Anlagenbuch.zip $IDEMPIERE_HOME/migration/zip_2pack/$(date +%Y%m%d%H%M)_SYSTEM_Anlagenbuch.zip
   ```
2. iDempiere neu starten. Beim Start läuft `PackInApplicationActivator` und installiert das 2Pack.
3. Server-Log prüfen:
   
   ```bash
   grep -E 'Successful|Failed' $IDEMPIERE_HOME/log/idempiere.YYYY-MM-DD_*.log | tail -5
   ```

### Variante B — ohne Server-Restart, Standalone-Java

Schneller bei Tests:

1. ZIP in einen Ordner legen (gleiches Naming):
   
   ```bash
   mkdir -p /tmp/anlagenbuch_2pack
   cp 2pack/Anlagenbuch.zip /tmp/anlagenbuch_2pack/$(date +%Y%m%d%H%M)_SYSTEM_Anlagenbuch.zip
   ```

2. Apply via Standalone-Java (startet einen kompletten OSGi-Stack temporär):
   
   ```bash
   bash $IDEMPIERE_HOME/utils/RUN_ApplyPackInFromFolder.sh /tmp/anlagenbuch_pack2
   ```
   
   Dauert ~30 Sekunden. Setzt voraus, dass der iDempiere-Server **nicht** läuft (sonst Port-/DB-Konflikt). Alternativ Variante A.

3. Erfolg prüfen:
   
   ```bash
   ./scripts/test/01_2pack_imports.sh
   ```

## Sequence-Bereiche

Das 2Pack legt 4 DocumentNo-Sequenzen (`BXS_AssetItem_Defect`, `_Schedule`, `_Status`, `BXS_WorkOrder_DocumentNo`) sowie für jede der 6 BXS-Tabellen automatisch eine TableID-Sequenz an. Alle starten bei `1` (DocumentNo) bzw. `1_000_000` (TableID, User-Range).

## Berechtigungen

Das 2Pack liefert **keine** eigene Anlagenbuch-Rolle aus (`AD_Role` ist tenant-spezifisch). Das Rollenkonzept ist eine **Master-Rolle** `anlagenbuch` (Konvention: Master-Rollen kleingeschrieben, halten alle Rechte; Login-Rollen wie `GF`/`Disposition` inkludieren sie). Anlegen mit Schreibrechten auf die vier Hauptfenster:

| Fenster           | Tabellen-Zugriff                                                       |
| ----------------- | ---------------------------------------------------------------------- |
| BXS Asset Class   | `BXS_AssetClass`                                                       |
| BXS Schedule Type | `BXS_ScheduleType`                                                     |
| BXS Asset         | `BXS_Asset` (R/W), `BXS_AssetItem` (R/W)                               |
| BXS Work Order    | `BXS_WorkOrder` (R/W), `BXS_WorkOrder_Item` (R/W), `BXS_AssetItem` (R) |

Window-Access vergeben über das Fenster *Role* → Tab *Window Access*. Anschließend Cache-Reset (Login neu) damit die Rolle die Fenster sieht.

## Initial-Daten beim Kunden

`BXS_AssetClass`-Datensätze (`100`=Fahrzeug, `200`=Stapler, `300`=Technische Anlage, `400`=IT, `500`=Immobilie) und `BXS_ScheduleType`-Datensätze (TUV/SP/UVV/WARRANTY/INSPECTION) sind im 2Pack enthalten.

C_UOM-Verknüpfung an `BXS_AssetClass` (Kilometer für Klasse `100`, Hour für Klasse `200`) ist nicht im 2Pack, weil die UOM-IDs pro Tenant variieren — manuell setzen:

```sql
UPDATE BXS_AssetClass SET C_UOM_ID =
    (SELECT C_UOM_ID FROM C_UOM WHERE Name='Kilometer' AND AD_Client_ID IN (0, <client>) LIMIT 1)
WHERE Value='100';

UPDATE BXS_AssetClass SET C_UOM_ID =
    (SELECT C_UOM_ID FROM C_UOM WHERE Name='Hour' AND AD_Client_ID IN (0, <client>) LIMIT 1)
WHERE Value='200';
```

Der Anlagenbestand wird über die CSV-Vorlage geladen (siehe `import/AssetImport_Mapping.md`).

## Bekannte Einschränkungen

Versionsverlauf siehe `docs/CHANGELOG.md`. Aktuell offen:

- **Rolle `anlagenbuch`** wird vom Admin manuell angelegt — `AD_Role` ist tenant-spezifisch und passt nicht in ein System-2Pack. Bootstrap-Hilfe in `setup/bootstrap_roles.py`.
- **Reports (JRXML)** liegen in `reports/` und müssen einmalig nach `$IDEMPIERE_HOME/reports/` kopiert werden — 2Pack-Install kopiert sie nicht mit (s.u. „Reports — Sprache umstellen").

## Reports — Sprache umstellen

Im 2Pack ist pro Report genau ein sprachneutraler `AD_Process` enthalten
(`BXS_Print_WorkshopDossier`, `BXS_Print_AssetDossier`,
`BXS_Print_AssetStatusOverview`). Das Feld `JasperReport` zeigt
auf die englische Default-Datei (z.B. `WorkshopDossier.jrxml`). Für eine
deutsche Installation muss das Suffix `_de` vor `.jrxml` eingefügt
werden (also `WorkshopDossier_de.jrxml`).

Die jrxml-Dateien müssen einmalig in `$IDEMPIERE_HOME/reports/`
auf dem Zielserver liegen (2Pack-Install kopiert sie nicht mit; 2pack
befüllt nur `AD_Process`).

**Varianten:**

1. **Mit direktem DB-Zugriff** (Dev-/Test-Setup): SQL-Skript ausführen.

   ```bash
   psql -h <host> -U <user> -d <db> -f setup/install_de_reports.sql
   ```

   Das Skript ist idempotent (`NOT LIKE '%_de.jrxml'`-Guard) und
   deaktiviert in einem Aufwasch die verwaisten alten
   `_DE`/`_EN`-Records aus früheren 2Pack-Ständen.
   `install.sh --with-de` macht das im einen Rutsch.

2. **Ohne DB-Zugriff** (Produktiv-Installation): Umstellung **manuell
   im UI** im System-Mandanten unter *Anwendung → Bericht & Prozess*.
   Pro Eintrag (`BXS_Print_WorkshopDossier`, `BXS_Print_AssetDossier`,
   `BXS_Print_AssetStatusOverview`) das Feld `JasperReport`
   editieren und `_de` vor `.jrxml` einfügen. Änderung erscheint im
   Audit-Trail.

3. **Englische Installation**: nichts tun, Defaults bleiben aktiv.

## De-Installation / Reset

Im Test-Modus (GardenWorld) die Daten löschen:

```bash
./example/GardenWorld/cleanup.sh
```

Die DB-Schemata (Tabellen) bleiben erhalten. Die AD-Records (Tabellen-Definitionen, Fenster) lassen sich nicht sauber rückgängig machen — bei Neuanfang DB aus Backup wiederherstellen.
