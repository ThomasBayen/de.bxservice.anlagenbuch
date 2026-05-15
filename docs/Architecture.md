# Anlagenbuch — Architecture

This file describes **how** Anlagenbuch is built: delivery form,
generator, UUID strategy, BeanShell scripts. The audience is
contributors (developers, forks, community contributions). For the
business background see `Concept.md`; for the table and column
reference see `DataModel.md`.

## Delivery as a 2Pack

Initial installation runs entirely through the standard 2Pack window
of an existing iDempiere — **no server access, no plugin build
needed**. The ZIP contains:

- DB objects (tables, columns, sequences, lists, windows, tabs,
  fields, processes, rules)
- BeanShell scripts from `scripts/*.bsh` embedded as `AD_Rule.Script`
- JasperReport templates from `reports/*.jrxml`, embedded
- Initial data for asset classes and schedule types
- German translations (`AD_Element_Trl`, `AD_Field_Trl`,
  `AD_Window_Trl`, `AD_Tab_Trl`, `AD_Process_Trl`, `AD_Ref_List_Trl`)

Table names, column names and UI default labels are in English
(community suitability). Documentation is bilingual (English
default, German parallel).

**Prerequisite for a clean migration to a later OSGi plugin:** all
UUIDs are fixed once and tracked in the repo (see below).

## Repository layout

```
Anlagenbuch/
├── docs/                  User, admin and architecture documentation
├── src/                   Sources of the PDF outputs (workshop dossier, training deck, quick reference)
├── 2pack/                 2Pack source and build wrapper
│   ├── source/spec/       YAML specs (one file per domain)
│   ├── source/assemble.py YAML → PackOut.xml generator
│   └── build.sh           Runs assemble.py + zips into Anlagenbuch.zip
├── scripts/               BeanShell scripts (embedded as AD_Rule.Script)
├── reports/               JasperReports sources (jrxml, DE + EN)
├── import/                CSV / ODS templates + mapping documentation
├── setup/                 Bootstrap scripts (roles, REST helpers)
└── uuids.csv              fixed UUIDs of all objects
```

## UUID strategy

All objects (tables, columns, windows, tabs, fields, lists, list
values, sequences, processes, rules, reports, initial records)
receive a **UUID generated once and pinned in the repository**.
`uuids.csv` is the central source of truth:

```
ObjectType,Name,UUID
AD_Table,BXS_Asset,a7b3c1d4-...
AD_Column,BXS_Asset.Value,...
AD_Window,BXS_Asset_Window,...
AD_Reference,BXS_AssetStatus,...
```

The generator fills missing entries on first run with `uuid4` values
and writes the file back. Repeated 2Pack imports are idempotent —
the same logical key produces the same UUID, iDempiere recognises
the existing record and updates it instead of duplicating.

## Generator (`2pack/source/assemble.py`)

Python generator that turns the YAML specs in `2pack/source/spec/`
into `2pack/source/PackOut.xml`. Top-level blocks and their job:

| YAML block            | Produces                                                                                                                 |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `package:`            | `<idempiere>` header attributes                                                                                          |
| `references:`         | `AD_Reference` (list type) + `AD_Ref_List`s, each with nested `_Trl(de_DE)`                                              |
| `tables:`             | `AD_Element`s (except core columns from the `CORE_ELEMENTS` map), `AD_Table` with a row of `AD_Column`s                  |
| `additional_columns:` | Standalone `AD_Column` records (for `ALTER TABLE` on existing tables, e.g. a forward FK added later)                     |
| `sequences:`          | DocumentNo sequences (the table-ID sequence is created by iDempiere itself via `MTable.afterSave`)                       |
| `windows:`            | `AD_Window` + `AD_Tab`s with display logic / where clause / read-only flag, `AD_Field` per column (auto), `AD_Menu`      |
| `rules:`              | `AD_Rule` (BeanShell source embedded from `scripts/*.bsh`), `AD_Table_ScriptValidator` links                             |
| `processes:`          | `AD_Process` + `AD_Process_Para` + toolbar-button link (`AD_Tab.AD_Process_ID`)                                          |
| `reports:`            | `AD_Process` with `IsReport=Y`, embedded `.jrxml`, `AD_PrintFormat`                                                      |
| `initial_data:`       | `<SQLStatement>` with an explicit ID range `1_000_000+` and `ON CONFLICT DO NOTHING` (idempotent)                        |

Build time is under 2 s; 2Pack import time against iDempiere 11 is
around 30 s including OSGi stack startup.

## DocumentNo sequences

Document-number scheme: `{prefix}-{year}-{5-digits}`. Year from
`ReportedDate` or `Created`.

| Type             | Prefix example   | AD_Sequence name           |
| ---------------- | ---------------- | -------------------------- |
| Defect           | `FEH-2026-00184` | `BXS_AssetItem_Defect`     |
| Schedule         | `TER-2026-00412` | `BXS_AssetItem_Schedule`   |
| Status           | `STA-2026-00033` | `BXS_AssetItem_Status`     |
| Work Order       | `WAU-2026-00031` | `BXS_WorkOrder_DocumentNo` |

Assignment is done by `AD_Rule` (BeanShell, `EventType='T'`) used as a
`TableEventValidator` — see `CLAUDE.md` for the three pitfalls
(EventType constant, vararg bridging, default table sequence).

## BeanShell scripts (`AD_Rule`)

Every piece of logic lives in its own `.bsh` file under `scripts/`;
the 2Pack embeds it through the `Script` field of the rule.

| Script                            | Trigger                                          | Job                                                                                            |
| --------------------------------- | ------------------------------------------------ | ---------------------------------------------------------------------------------------------- |
| `assetitem_documentno.bsh`        | TableEvent `TYPE_BEFORE_NEW` on `BXS_AssetItem`  | Sets `DocumentNo` from the matching sequence depending on `Type`                               |
| `workorder_documentno.bsh`        | TableEvent `TYPE_BEFORE_NEW` on `BXS_WorkOrder`  | Sets `DocumentNo` from `BXS_WorkOrder_DocumentNo`                                              |
| `assetitem_close.bsh`             | Process "Close item"                             | Closes the item; for `Schedule` creates the follow-up and sets `NextItem_ID`                   |
| `workorder_pull_open_items.bsh`   | Process "Pull open items"                        | Adds open `Defect`/`Schedule` items of the asset as `BXS_WorkOrder_Item` with `IsResolved=Y`   |
| `workorder_complete.bsh`          | Process "Complete work order"                    | Sets items with `IsResolved=Y` to `Done`, creates follow-up schedules, `WorkOrderStatus=Completed` |
| `asset_create_workorder.bsh`      | Process "Work order from asset"                  | Creates a `BXS_WorkOrder` and pulls the open items automatically                               |

Conventions: idempotent where possible, errors via
`org.compiere.process.ProcessInfo.addLog()`, no direct DB access
without PO models.

## Reports (JasperReports)

Two jrxml files per report — one German (default for JBKG), one
English variant. Rationale: resource bundles (`$R{key}`) would be
the standard Jasper route, but they do not solve the actual
consistency problem — if an admin changes a UI label in iDempiere,
the report property stays the same. The extra effort for two jrxml
files does not pay off in light of that uncertainty.

**Future variant:** pull column labels via JOIN to `AD_Element_Trl`
straight from iDempiere — the only variant that automatically
reflects UI changes in the report. Static headings would then come
from `AD_Message`.

Cross-cutting conventions for JasperReports (multi-selection
parameters, `$P{}` vs `$P!{}`, "Page X of Y", `positionType=Float`,
sub-datasets) are documented iDempiere-wide in
`~/iDempiere-development/docs/jasperreports-knowhow.md`.

## Menu convention "Anlagenbuch"

All Anlagenbuch menu entries (windows and reports) live under a
summary node "Anlagenbuch" attached at the very end of the menu
tree (Parent=Root, SeqNo=999). The wiring is fully handled by the
generator — details in `CLAUDE.md` (including the workaround for the
`MWindow.afterSave` tree wiring).

## Permissions

The Jakob Bayen KG master/login role concept: one domain-specific
**master role** `anlagenbuch` (lower case) holds the window and
process permissions for all four main windows. **Login roles**
(`GF`, `Dispatch`, …) include the master role via
`AD_Role_Included`. Creation and maintenance through
`setup/bootstrap_roles.py` (REST-driven, idempotent).

Background concept: `../Datalotte.md` in the parent repository
directory.

## Most important lessons from building the 2Pack

Detail in `~/iDempiere-development/2packtool/docs/11-lessons-handcoded-2pack.md`.
The points with the highest pitfall potential:

1. **Trl records nested** as `type="translation"` rather than as a
   sibling `type="table"`.
2. **Standard columns** (`Value` / `Name` / `IsActive` / …) reference
   core `AD_Element` IDs; do not create a new `AD_Element`.
3. **Initial data for newly created tables as generic PO records**
   (`<TableName type="table">`) with the `_UU` column set — PackIn
   defers them automatically until the table and FK references are
   resolved. `<SQLStatement>` runs synchronously and fails on first
   install against tables that do not yet exist.
4. **`_AccessLevel` mismatches** produce subtle mandatory-field
   violations — system master data = 6, tenant transactional = 3.
5. **ZIP filename `…_SYSTEM_…`** for a system-level 2Pack (value
   `AD_Client.Value` for `AD_Client_ID=0`, not the string `System`).
6. **`AD_Field` for *every* table column** (also system / audit /
   parent columns with `IsDisplayed=N`). Without them
   `GridTab.setCurrentRow` does not populate the tab context — the
   consequence is greyed-out fields, save failing with
   `AD_Client_ID=-1`, empty detail tabs.
7. **`TableDir` on core tables without `AD_Window`** (e.g.
   `M_Resource` in a standard installation) is a UI killer: NPE in
   `MLookupFactory.getLookup_TableDir` during tab init.
8. **`AD_Rule.EventType='T'`** for table event validators. `M`
   (Measure for Performance Analysis) does not trigger — the
   validator stays silent.
9. **BeanShell + `DB.getSQLValue(...)` with parameters**: the
   varargs overload is not dispatchable — fill a
   `java.util.List<Object>` and call the matching overload.
10. **The default table sequence** (`DocumentNo_<Table>`) must be
    deactivated; otherwise `PO.saveNew()` pulls from it — before our
    TBN rule ever gets a chance.

When `AD_Rule` records are modified via `psql`: **restart the
iDempiere server**, otherwise the MRule / MTableScriptValidator
cache serves the old version (or a cached "no validator found").

## Migration to an OSGi plugin (open)

Becomes relevant once the logic grows beyond what can be expressed
maintainably in `AD_Rule` scripts, once Java tests / ModelValidator
hooks are required, or once the module is published as a community
contribution.

OSGi bundle `de.bxservice.anlagenbuch` with the 2Pack as a resource.
Thanks to the stable UUIDs, existing records are not duplicated on
plugin import.
