# Anlagenbuch — Installation

Prerequisite: a running iDempiere 11 instance with a PostgreSQL
backend, plus shell access to the server (or the `idempiere-server/`
directory).

## Contents of the delivery

| File                              | Purpose                                                                          |
| --------------------------------- | -------------------------------------------------------------------------------- |
| `2pack/Anlagenbuch.zip`           | 2Pack archive containing all DB objects, windows, lists and sequences            |
| `2pack/source/PackOut.xml`        | Source XML, kept in the repo for diff-review                                     |
| `2pack/source/spec/*.yaml`        | Source-of-truth specs for the generator                                          |
| `2pack/source/assemble.py`        | YAML → PackOut.xml generator                                                     |
| `2pack/build.sh`                  | Wrapper that builds `2pack/Anlagenbuch.zip`                                      |
| `import/AssetImport_Template.csv` | Template for initial loading of the asset master data                            |
| `import/AssetImport_Mapping.md`   | Column mapping documentation                                                     |
| `example/JakobBayenKG/`           | Example deployment with test data, master role includes and bootstrap script    |
| `scripts/test/01_2pack_imports.sh` | Schema smoke test (counts tables, windows etc.)                                  |
| `scripts/test/02_smoke_inserts.sh`| INSERT smoke test (creates asset + defect + schedule in GardenWorld)             |
| `reports/README.md`               | Layout / SQL sketch for the asset dossier and workshop dossier                   |
| `docs/CHANGELOG.md`               | Version history, including what was added in which version                      |

## Preparation

1. **Back up the target database.** `pg_dump` is enough. PackIn is
   transactional, but on failure a half-imported state on the AD level
   (sequences, auto-translations) is possible. A backup saves stress.
2. **Build the 2Pack** (if not already delivered):

   ```bash
   ./2pack/build.sh
   ```

   Produces `2pack/Anlagenbuch.zip`.

## Import

### Option A — via `migration/zip_2pack/` with a server restart

The standard iDempiere path for auto-import on server start:

1. Rename the ZIP into the required format
   `yyyymmddHHMM_<Client>_Anlagenbuch.zip`. For system-level records
   `<Client>=SYSTEM` (this is `AD_Client.Value` for `AD_Client_ID=0`):

   ```bash
   cp 2pack/Anlagenbuch.zip $IDEMPIERE_HOME/migration/zip_2pack/$(date +%Y%m%d%H%M)_SYSTEM_Anlagenbuch.zip
   ```
2. Restart iDempiere. On startup `PackInApplicationActivator` runs and
   installs the 2Pack.
3. Check the server log:

   ```bash
   grep -E 'Successful|Failed' $IDEMPIERE_HOME/log/idempiere.YYYY-MM-DD_*.log | tail -5
   ```

### Option B — without a server restart, standalone Java

Faster for testing:

1. Put the ZIP into a folder (same naming):

   ```bash
   mkdir -p /tmp/anlagenbuch_2pack
   cp 2pack/Anlagenbuch.zip /tmp/anlagenbuch_2pack/$(date +%Y%m%d%H%M)_SYSTEM_Anlagenbuch.zip
   ```

2. Apply via the standalone Java runner (which spins up a full OSGi
   stack temporarily):

   ```bash
   bash $IDEMPIERE_HOME/utils/RUN_ApplyPackInFromFolder.sh /tmp/anlagenbuch_2pack
   ```

   Takes around 30 seconds. The iDempiere server must **not** be
   running (otherwise the port / DB will clash). Use option A
   instead in that case.

3. Verify success:

   ```bash
   ./scripts/test/01_2pack_imports.sh
   ```

## Sequence ranges

The 2Pack creates 4 document-number sequences
(`BXS_AssetItem_Defect`, `_Schedule`, `_Status`,
`BXS_WorkOrder_DocumentNo`) and, for each of the 6 BXS tables,
automatically one table-ID sequence. They all start at `1`
(document number) or `1_000_000` (table ID, user range).

## Permissions

The 2Pack ships **no** Anlagenbuch role of its own (`AD_Role` is
tenant-specific). The role concept is a **master role**
`anlagenbuch` (convention: master roles in lower case, hold all
permissions; login roles such as `GF` / `Dispatch` include them).
Create it with write access to the four main windows:

| Window            | Table access                                                           |
| ----------------- | ---------------------------------------------------------------------- |
| BXS Asset Class   | `BXS_AssetClass`                                                       |
| BXS Schedule Type | `BXS_ScheduleType`                                                     |
| BXS Asset         | `BXS_Asset` (R/W), `BXS_AssetItem` (R/W)                               |
| BXS Work Order    | `BXS_WorkOrder` (R/W), `BXS_WorkOrder_Item` (R/W), `BXS_AssetItem` (R) |

Grant window access through the *Role* window → tab *Window Access*.
Afterwards reset the cache (log out and back in) so the role sees the
new windows.

## Initial data at the customer

`BXS_AssetClass` records (`100`=Vehicle, `200`=Forklift,
`300`=Stationary equipment, `400`=IT, `500`=Building) and
`BXS_ScheduleType` records (TUV/SP/UVV/WARRANTY/INSPECTION) ship with
the 2Pack.

The `C_UOM` link on `BXS_AssetClass` (Kilometer for class `100`, Hour
for class `200`) is **not** in the 2Pack because the UOM IDs vary per
tenant — set them manually:

```sql
UPDATE BXS_AssetClass SET C_UOM_ID =
    (SELECT C_UOM_ID FROM C_UOM WHERE Name='Kilometer' AND AD_Client_ID IN (0, <client>) LIMIT 1)
WHERE Value='100';

UPDATE BXS_AssetClass SET C_UOM_ID =
    (SELECT C_UOM_ID FROM C_UOM WHERE Name='Hour' AND AD_Client_ID IN (0, <client>) LIMIT 1)
WHERE Value='200';
```

The asset inventory is loaded via the CSV template (see
`import/AssetImport_Mapping.md`).

## Known limitations

See `docs/CHANGELOG.md` for the version history. Currently open:

- **Role `anlagenbuch`** is created manually by the admin — `AD_Role`
  is tenant-specific and does not fit into a system-level 2Pack.
  Bootstrap helper in `setup/bootstrap_roles.py`.
- **Reports (JRXML)** live in `reports/` and must be copied once to
  `$IDEMPIERE_HOME/reports/`; the 2Pack install does not copy them
  along (see "Reports — switching language" below).

## Reports — switching language

For each report the 2Pack ships exactly one language-neutral
`AD_Process` (`BXS_Print_WorkshopDossier`, `BXS_Print_AssetDossier`,
`BXS_Print_AssetStatusOverview`). Its `JasperReport` field points
to the English default file (e.g. `WorkshopDossier.jrxml`). For a
German installation the suffix `_de` must be inserted before `.jrxml`
(i.e. `WorkshopDossier_de.jrxml`).

The jrxml files must be present once in `$IDEMPIERE_HOME/reports/` on
the target server (the 2Pack install does not copy them; the 2Pack
only populates `AD_Process`).

**Variants:**

1. **With direct DB access** (dev/test setup): run the SQL script.

   ```bash
   psql -h <host> -U <user> -d <db> -f setup/install_de_reports.sql
   ```

   The script is idempotent (`NOT LIKE '%_de.jrxml'` guard) and at
   the same time deactivates the orphaned old `_DE` / `_EN` records
   from earlier 2Pack revisions.
   `install.sh --with-de` does this in one go.

2. **Without DB access** (production install): switch over **manually
   in the UI** in the System tenant under *Application → Report &
   Process*. For each entry (`BXS_Print_WorkshopDossier`,
   `BXS_Print_AssetDossier`, `BXS_Print_AssetStatusOverview`)
   edit the `JasperReport` field and insert `_de` before `.jrxml`.
   The change appears in the audit trail.

3. **English installation**: do nothing, the defaults stay active.

## Uninstall / reset

In test mode (GardenWorld) wipe the data:

```bash
./example/GardenWorld/cleanup.sh
```

The DB schemas (tables) stay in place. The AD records (table
definitions, windows) cannot be reverted cleanly — for a clean
restart restore the DB from a backup.
