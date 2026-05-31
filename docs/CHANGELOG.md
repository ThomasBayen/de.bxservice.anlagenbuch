# Changelog

A log of notable changes to Anlagenbuch.

## Unreleased

- 2Pack now ships a **system-tenant master role** `anlagenbuch`
  (`AD_Client_ID=0`, `IsMasterRole=Y`, `IsManual=Y`) carrying all
  window and process access for the plugin. New third package
  `Anlagenbuch_03_role.zip` imported after schema + data. Tenants
  bind it into one of their login roles via `AD_Role_Included` once
  and get future plugin updates automatically.
- `example/JakobBayenKG/bootstrap_roles.py` reduced to a single
  `AD_Role_Included` POST — role creation, process-access and
  window-access maintenance are no longer needed (the 2Pack handles
  them).
- New spec file `2pack/source/spec/05-roles.yaml` and generator
  helper `emit_role` in `2pack/gen/assemble.py`.
- The generator is now **vendored** into `2pack/gen/assemble.py` (a copy
  of a shared canonical generator) instead of living in
  `2pack/source/`. `2pack/build.sh` calls the vendored copy; the repo
  still builds standalone. Drift marker: `2pack/gen/.generator-md5`.
  Output is byte-identical to the previous in-tree generator (verified
  against the schema/data/role baseline).

## v1.0 — initial public release

### Data model

- 6 tables with DDL, columns, German translations:
  `BXS_AssetCategory` (list, meta category), `BXS_AssetClass`,
  `BXS_ScheduleType`, `BXS_Asset`, `BXS_AssetItem`, `BXS_WorkOrder`,
  `BXS_WorkOrder_Item`.
- `BXS_AssetItem.NextItem_ID` (self-reference) for chaining closed
  maintenance schedules to their successor.
- Virtual columns `BXS_Asset.LastMeterReading` and
  `BXS_Asset.LastMeterDate` (`ColumnSQL` over the most recent status
  item).
- Optional resource FK `BXS_Asset.S_Resource_ID` to `S_Resource`.

### Reference lists

- `BXS_AssetCategory`, `BXS_AssetStatus`, `BXS_ItemType`,
  `BXS_ItemStatus`, `BXS_WorkOrderStatus`, `BXS_Priority`.

### Windows

- "BXS Asset Class" and "BXS Schedule Type" master-data windows.
- "BXS Asset" 4-tab window (master data + three type-filtered detail
  tabs: Defect / Schedule / Status).
- "BXS Work Order" 3-tab window with a read-only overview of open
  items.

### Document numbers

- Automatic document numbers (`FEH-` / `TER-` / `STA-` / `WAU-`)
  assigned via `AD_Rule` `TableEventValidator` (`EventType='T'`,
  BeanShell, `RuleType=S`).

### Workflow buttons (BeanShell rules)

- "Close item" (`assetitem_close.bsh`)
- "Pull open items" (`workorder_pull_open_items.bsh`)
- "Complete work order" (`workorder_complete.bsh`)
- "Work order from asset" (`asset_create_workorder.bsh`)

### Reports (JasperReports)

- Asset Dossier (`AssetDossier.jrxml` / `AssetDossier_de.jrxml`)
- Workshop Dossier (`WorkshopDossier.jrxml` /
  `WorkshopDossier_de.jrxml`)
- Asset Status Overview (`AssetStatusOverview.jrxml` /
  `AssetStatusOverview_de.jrxml`)
- One language-neutral `AD_Process` per report; the `_de` variant is
  activated per installation by editing the `JasperReport` filename.

### Initial data shipped in the 2Pack

- 6 generic `BXS_AssetClass` records (Vehicle / Equipment / Stationary
  / Building / IT / Other).
- 5 `BXS_ScheduleType` records (TUV / SP / UVV / WARRANTY /
  INSPECTION).
- UOM defaults on the shipped classes (Vehicle→Kilometer — a new
  system UOM ships with the 2Pack — others→Hour where applicable).

### Tooling and repository layout

- `2pack/` directory with YAML specs and the `assemble.py` generator;
  build via `2pack/build.sh` → `Anlagenbuch.zip`.
- Generic plugin parts at the repository root; customer-specific
  deployments in `example/<Tenant>/`.
- `install.sh` (repo root) builds the 2Pack, deploys it into
  `$IDEMPIERE_HOME`, copies the JRXML reports, repairs the menu tree
  and runs the smoke test.
- `setup/fix_menu_tree.py` fixes the `AD_TreeNodeMM` workaround after
  each 2Pack reimport.
- Credentials are loaded exclusively from `**/config.env` files; the
  `*.example` templates are tracked, the real `config.env` files are
  gitignored.
- Vendored ODS importer under `tools/import-ods.py` (AGPL-3.0).

### Documentation

- Bilingual: English defaults in `docs/`, German next to them with the
  `_de` suffix.
- `LICENSE` (AGPL-3.0-or-later), SPDX headers in every script.

### Metrics

- Generator: ~720 lines of Python in one file
  (`2pack/gen/assemble.py`).
- YAML specs: ~270 lines across 6 files.
- Generated `PackOut.xml`: ~3000 lines, ~485 records.
- Build time: < 2 s. 2Pack import against iDempiere 11: ~30 s.
