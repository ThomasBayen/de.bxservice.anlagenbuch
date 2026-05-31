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
| `2pack/gen/assemble.py`           | YAML → PackOut.xml generator (vendored)                                          |
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

The 2Pack ships a **system-tenant master role** `anlagenbuch` that
already carries:

- Window access to the four main windows
  (`BXS Asset`, `BXS Asset Class`, `BXS Schedule Type`, `BXS Work Order`).
- Process access to all workflow buttons and reports
  (`BXS_AssetItem_CloseItem`, `BXS_WorkOrder_CompleteOrder`,
  `BXS_WorkOrder_PullOpenItems`, `BXS_Asset_CreateWorkOrder`,
  `BXS_Print_WorkshopDossier`, `BXS_Print_AssetDossier`,
  `BXS_Print_AssetStatusOverview`) plus the core processes
  `Import CSV Process` and `Cache Reset`.

The role lives in the **system tenant** (`AD_Client_ID=0`) and is
flagged as a master role (`IsMasterRole=Y`, `IsManual=Y`). Tenants
bind it into one of their own login roles through `AD_Role_Included`
— new processes / windows introduced by future 2Pack updates therefore
propagate to every installation automatically.

**Admin step per tenant** (once after `./install.sh`):

1. Log in as system administrator.
2. Open the *Role* window → select the tenant's login role
   (e.g. `GF`, `Dispatch`).
3. Tab *Included Role* → new entry, *Included Role* = `anlagenbuch`
   (in the system tenant), *Seq No* e.g. `20`, *Active* = ✓.
4. Reset the cache (log out and back in) so the login role sees the
   inherited window/process access records.

The master role itself never gets a user assignment — it is only
included. UserLevel and OrgAccess come from the tenant's login role;
the system role only grants "may see this window / may run this
process".

> Background: iDempiere core allows cross-tenant inclusion
> (`MRoleIncluded.beforeSave` only checks for loops, not the client;
> `MRole.mergeIncludedAccess` merges unfiltered). As long as the
> master role holds access exclusively to system records
> (Client=0) — which is automatic for a pure 2Pack delivery — the
> pattern is stable.

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
