# Anlagenbuch — Data Model

State: third draft (FailureMode/Severity removed, MeterUnit via
`C_UOM`, window structure revised). Table prefix `BXS_`. English
identifiers for tables and columns, German labels in the UI.

iDempiere standard columns (`AD_Client_ID`, `AD_Org_ID`, `IsActive`,
`Created`, `CreatedBy`, `Updated`, `UpdatedBy`, `<Tablename>_UU`) are
**omitted** from the column lists below and are assumed to be present
in every table.

## 1. Overview (ER sketch)

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
                                 └──▶ BXS_ScheduleType   (Type=Schedule only)

   Lists (AD_Reference): AssetStatus, ItemType, ItemStatus,
                         WorkOrderStatus, Priority
```

## 2. Tables

### 2.1 BXS_Asset

Master data of a managed object. One table for all classes.

| Column              | Type                | Required | Note                                                |
| ------------------- | ------------------- | -------- | --------------------------------------------------- |
| `BXS_Asset_ID`      | ID                  | yes      | PK                                                  |
| `Value`             | String(40)          | yes      | Search key, e.g. "TRK-MB-2078"                      |
| `Name`              | String(120)         | yes      | Display name                                        |
| `Description`       | Text                | no       |                                                     |
| `BXS_AssetClass_ID` | FK → BXS_AssetClass | yes      | Vehicle / Forklift / Equipment / IT / Building      |
| `AssetStatus`       | List                | yes      | InService / OutOfService / Disposed                 |
| `Manufacturer`      | String(60)          | no       |                                                     |
| `Model`             | String(60)          | no       |                                                     |
| `SerialNo`          | String(40)          | no       | VIN for vehicles                                    |
| `YearBuilt`         | Number(4)           | no       |                                                     |
| `CommissionDate`    | Date                | no       | Commissioning date                                  |
| `M_Resource_ID`     | FK → M_Resource     | no       | Optional, when dispatch-relevant                    |
| `AD_User_ID`        | FK → AD_User        | no       | Primary user (e.g. assigned driver)                 |
| `Location`          | String(120)         | no       | Location, free text                                 |
| `LastMeterReading`  | Number (virtual)    | no       | Calculated: most recent `MeterReading` across items |
| `LastMeterDate`     | Date (virtual)      | no       | Calculated: associated date                         |
| `Note`              | Text                | no       |                                                     |

UI: when `BXS_AssetClass.C_UOM_ID` is empty (e.g. for a building),
`LastMeterReading` / `LastMeterDate` are hidden (Display Logic). For
vehicles the license plate becomes part of `Name` or `Value` (e.g.
"KR-JB 2078 Mercedes Atego").

`LastMeterReading` and `LastMeterDate` are implemented as virtual
columns (iDempiere `IsVirtualColumn=Y` with an SQL sub-query over
`BXS_AssetItem.MeterReading`, `MAX` over
`MeterDate`/`CompletionDate`/`ReportedDate`).

### 2.2 BXS_AssetClass

Business-level asset class. Freely extensible per tenant (e.g. several
truck classes for different TÜV intervals). Behaviour / display logic
lives one level up in `Category`.

| Column              | Type       | Required | Note                                                            |
| ------------------- | ---------- | -------- | --------------------------------------------------------------- |
| `BXS_AssetClass_ID` | ID         | yes      | PK                                                              |
| `Value`             | String(40) | yes      |                                                                 |
| `Name`              | String(60) | yes      |                                                                 |
| `Description`       | Text       | no       |                                                                 |
| `Category`          | List       | yes      | `BXS_AssetCategory` — Vehicle / Equipment / Stationary / Building / IT / Other. Drives UI behaviour. |
| `C_UOM_ID`          | FK → C_UOM | no       | Unit for meter readings. Empty ⇒ the asset has no meter reading |

**Category behaviour** (list `BXS_AssetCategory`, fixed):

| Value        | Used for | UI / workflow |
|--------------|----------|---------------|
| `Vehicle`    | Vehicles and large machines with a meter (truck, car, forklift, sweeper) | Meter reading visible; driver on work order recommended; location can change |
| `Equipment`  | Mobile small equipment without a meter (hand truck, pallet truck, tools) | Meter reading optional; location can change |
| `Stationary` | Permanently installed equipment (roller door, fire extinguisher, heating) | Meter reading hidden; location fixed |
| `Building`   | Real estate / part of a building | Address instead of location; dedicated reports possible later |
| `IT`         | IT hardware with inventory character (server, switch, printer) | Optional operating hours |
| `Other`      | Catch-all | No special logic |

Initial records (shipped in the 2Pack). The `Value` follows a numeric
scheme in steps of ten: **1xx** road motor vehicles, **2xx** other
vehicles / equipment with vehicle character (forklifts, trailers,
pallet trucks), **3xx** equipment / stationary, **4xx** IT, **5xx**
real estate. This keeps the class list sortable when the user adds
finer subdivisions.

| Value | Name              | Category   | Note                                                                                |
| ----- | ----------------- | ---------- | ----------------------------------------------------------------------------------- |
| `100` | Vehicle           | Vehicle    | Road motor vehicles: trucks, cars; own 1xx subclasses derivable                     |
| `200` | Forklift          | Vehicle    | Other vehicles with equipment character (forklift, trailer, pallet truck); UVV      |
| `300` | Technical system  | Stationary | Other operational equipment: roller doors, fire extinguishers                       |
| `400` | IT hardware       | IT         | Server, switch, printer                                                             |
| `500` | Building          | Building   | Parts of buildings, trades                                                          |

`C_UOM_ID` (Kilometer / Hour) is assigned manually at the customer
because UOM IDs are tenant-specific.

### 2.3 BXS_AssetItem

**Central table.** Unifies three business-level concepts via the
discriminator field `Type`:

- `Defect` — defect report: someone observed a defect.
- `Schedule` — maintenance schedule: an appointment (TÜV, SP, UVV,
  warranty expiry, …) is due on a particular date.
- `Status` — status report: a point-in-time snapshot without any
  defect, often during initial intake or a routine sighting.

Per `Type` the UI shows / hides different fields (Display Logic).
Items are not maintained in their own main window but as detail tabs
on the asset (see section 4).

| Column                | Type                  | Required | Defect | Schedule | Status | Note                                                  |
| --------------------- | --------------------- | -------- |:------:|:--------:|:------:| ----------------------------------------------------- |
| `BXS_AssetItem_ID`    | ID                    | yes      | •      | •        | •      | PK                                                    |
| `DocumentNo`          | String(30)            | yes      | •      | •        | •      | iDempiere sequence per type                           |
| `BXS_Asset_ID`        | FK → BXS_Asset        | yes      | •      | •        | •      |                                                       |
| `Type`                | List                  | yes      | •      | •        | •      | Defect / Schedule / Status                            |
| `Name`                | String(60)            | yes      | •      | •        | •      | Short description for lists                           |
| `Description`         | Text                  | no       | •      | ○        | •      | Long text                                             |
| `ReportedDate`        | Date                  | yes      | •      | ○        | •      | Day of observation / capture                          |
| `DueDate`             | Date                  | –        | –      | •        | –      | Due date (Schedule only)                              |
| `AD_User_ID`          | FK → AD_User          | no       | •      | –        | •      | Reporter / observer                                   |
| `Priority`            | List                  | no       | •      | –        | –      | Low / Medium / High                                   |
| `BXS_ScheduleType_ID` | FK → BXS_ScheduleType | –        | –      | •        | –      | TÜV/SP/UVV/warranty/…                                 |
| `IsMandatory`         | Boolean (virtual)     | –        | –      | •        | –      | Derived from `BXS_ScheduleType.IsMandatoryDefault`    |
| `MeterReading`        | Number                | no       | •      | •        | •      | Meter reading at observation / completion             |
| `EstimatedCost`       | Amount                | no       | •      | •        | –      | Cost estimate                                         |
| `ItemStatus`          | List                  | yes      | •      | •        | •      | Open / Done / Cancelled / Skipped                     |
| `CompletionDate`      | Date                  | no       | •      | •        | –      | Set on Done (for Status: = `ReportedDate`)            |
| `BXS_WorkOrder_ID`    | FK → BXS_WorkOrder    | no       | •      | •        | –      | The work order that handled this item                 |
| `NextItem_ID`         | FK → BXS_AssetItem    | no       | –      | •        | –      | Follow-up schedule, if generated                      |
| `Note`                | Text                  | no       | •      | •        | •      |                                                       |

Legend: • mandatory or typically relevant, ○ optional, – hidden in
the UI for that type.

**Lifecycle:**

- **Defect:** created with `ItemStatus=Open`. Closed either manually
  (self-fix, then `Done` with `CompletionDate`) or via a work order
  (the script sets `Done`, `CompletionDate`, `BXS_WorkOrder_ID`).
  `Cancelled` for false reports.
- **Schedule:** created with `ItemStatus=Open`. Closed via the close
  button (script) to `Done`; at the same time the script creates a
  new schedule with default values and sets `NextItem_ID`.
  `Skipped` for dropped appointments (e.g. asset was sold before
  TÜV was due).
- **Status:** set to `Done` immediately on creation,
  `CompletionDate=ReportedDate`. Never `Open`.

**Follow-up date:** when the follow-up schedule is created
automatically, `DueDate` is pre-filled as:

```
DueDate_new = firstOfMonth(CompletionDate_old) + ScheduleType.DefaultIntervalMonths
```

Rationale: TÜV/SP/UVV intervals run from the inspection date in
practice, not from the previous target date. Rounded to the first of
the month because the TÜV sticker is precise only to the month.

### 2.4 BXS_ScheduleType

Schedule type master data.

| Column                  | Type                | Required | Note                                          |
| ----------------------- | ------------------- | -------- | --------------------------------------------- |
| `BXS_ScheduleType_ID`   | ID                  | yes      | PK                                            |
| `Value`                 | String(40)          | yes      | e.g. `TUV`, `SP`, `UVV`, `WARRANTY`           |
| `Name`                  | String(60)          | yes      | Display name                                  |
| `Description`           | Text                | no       |                                               |
| `DefaultIntervalMonths` | Number              | no       | Suggestion for the follow-up (e.g. 12, 24)    |
| `IsMandatoryDefault`    | Boolean             | yes      | Default for the mandatory flag on new items   |
| `BXS_AssetClass_ID`     | FK → BXS_AssetClass | no       | If only relevant for one class                |

Initial records: `TUV` (12 months, mandatory, vehicle), `SP` (12
months, mandatory, vehicle), `UVV` (12 months, mandatory, forklift),
`WARRANTY` (variable, optional), `INSPECTION` (free, optional).

### 2.5 BXS_WorkOrder

Work order.

| Column               | Type            | Required | Note                                                                                                |
| -------------------- | --------------- | -------- | --------------------------------------------------------------------------------------------------- |
| `BXS_WorkOrder_ID`   | ID              | yes      | PK                                                                                                  |
| `DocumentNo`         | String(30)      | yes      | iDempiere sequence                                                                                  |
| `BXS_Asset_ID`       | FK → BXS_Asset  | yes      |                                                                                                     |
| `Name`               | String(60)      | yes      | Short description for lists, e.g. "TÜV + flap + tyres"                                              |
| `Workshop_ID`        | FK → C_BPartner | yes      | Workshop                                                                                            |
| `Driver_ID`          | FK → AD_User    | no       | Driver (resource) that brings the vehicle to the workshop                                           |
| `InternalContact_ID` | FK → AD_User    | no       | Internal contact for follow-up questions by the workshop; phone comes from `AD_User.Phone`          |
| `ScheduledDate`      | Date            | no       | Planned workshop date                                                                               |
| `ActualDate`         | Date            | no       | Actual start                                                                                        |
| `CompletionDate`     | Date            | no       | Return date                                                                                         |
| `EstimatedCost`      | Amount          | no       | Sum of item estimates or manual                                                                     |
| `ActualCost`         | Amount          | no       | Final cost                                                                                          |
| `ExternalDocumentNo` | String(30)      | no       | Document number from the workshop (invoice or order confirmation); free text                        |
| `C_Invoice_ID`       | FK → C_Invoice  | no       | Invoice link in iDempiere (once the invoice is captured)                                            |
| `WorkOrderStatus`    | List            | yes      | Draft / Released / Completed / Cancelled                                                            |
| `Description`        | Text            | no       |                                                                                                     |
| `Note`               | Text            | no       |                                                                                                     |

Detail tab: `BXS_WorkOrder_Item` (see 2.6). A single mixed list —
defects and schedules appear together, sorted by `LineNo`.

**Buttons / processes on the work order:**

1. *Pull open items* (`AD_Process` with script): automatically adds
   every `BXS_AssetItem` of the same asset with
   `Type ∈ {Defect, Schedule}` and `ItemStatus=Open` as a work order
   line, unless already present. Default `IsResolved=Y`. The
   dispatcher can then delete or untick rows.
2. *Complete work order* (`AD_Process` with script): see below.

**Completion script:**

1. Set all linked items with `IsResolved=Y` to `ItemStatus=Done`,
   `CompletionDate=today`, `BXS_WorkOrder_ID`.
2. Items with `IsResolved=N` stay open (waiting for the next work
   order).
3. For each closed item with `Type=Schedule`: create a new
   `BXS_AssetItem` record with the same master data,
   `DueDate = firstOfMonth(CompletionDate) +
   ScheduleType.DefaultIntervalMonths`, `ItemStatus=Open`, and set
   `NextItem_ID` on the old row.
4. Set `WorkOrderStatus=Completed` and `CompletionDate=today` on the
   work order.

The same follow-up logic applies when a schedule item is closed
*outside* a work order (separate close button on the item detail
tab).

### 2.6 BXS_WorkOrder_Item

Work order line (link table), realised as a detail tab on the work
order.

| Column                  | Type                | Required | Note                                                |
| ----------------------- | ------------------- | -------- | --------------------------------------------------- |
| `BXS_WorkOrder_Item_ID` | ID                  | yes      | PK                                                  |
| `BXS_WorkOrder_ID`      | FK → BXS_WorkOrder  | yes      | Parent                                              |
| `BXS_AssetItem_ID`      | FK → BXS_AssetItem  | yes      | Only items with Type ∈ {Defect, Schedule} make sense |
| `IsResolved`            | Boolean             | yes      | Default `Y`                                         |
| `LineNo`                | Number              | no       | Ordering                                            |
| `Note`                  | Text                | no       | Workshop note per line                              |

Unique constraint: `(BXS_WorkOrder_ID, BXS_AssetItem_ID)` — an item
cannot appear twice in the same work order.

Validation (script callout on add): `BXS_AssetItem.BXS_Asset_ID` must
match `BXS_WorkOrder.BXS_Asset_ID`, and `Type` must not be `Status`.

## 3. Lists (`AD_Reference`)

Value lists as iDempiere list references instead of dedicated tables,
because they are plain enumerations without further attributes:

| List                  | Values                                |
| --------------------- | ------------------------------------- |
| `BXS_AssetStatus`     | InService, OutOfService, Disposed     |
| `BXS_ItemType`        | Defect, Schedule, Status              |
| `BXS_ItemStatus`      | Open, Done, Cancelled, Skipped        |
| `BXS_WorkOrderStatus` | Draft, Released, Completed, Cancelled |
| `BXS_Priority`        | Low, Medium, High                     |

The meter unit (`C_UOM`) is **not** kept as a list; it is referenced
through iDempiere's standard `C_UOM` table (in `BXS_AssetClass`).

## 4. Windows

The module ships **four** iDempiere windows:

### 4.1 Window "Asset Class" (`BXS_AssetClass`)

Simple master-data window, one tab. Rarely maintained — only on
introduction and when extending.

### 4.2 Window "Schedule Type" (`BXS_ScheduleType`)

Simple master-data window, one tab. Rarely maintained.

### 4.3 Window "Asset" (`BXS_Asset`)

Main window for daily work. Tab structure:

| Tab      | Table / filter                              | Purpose                                            |
| -------- | ------------------------------------------- | -------------------------------------------------- |
| Asset    | `BXS_Asset`                                 | Master data                                        |
| Defect   | `BXS_AssetItem` with default `Type=Defect`  | Capture and close defects                          |
| Schedule | `BXS_AssetItem` with default `Type=Schedule`| Capture, close and follow up maintenance schedules |
| Status   | `BXS_AssetItem` with default `Type=Status`  | Capture status reports (stored as Done immediately) |

On creation `Type` is set from the tab default and is read-only
afterwards. Fields per tab are filtered to the relevant Type value
via Display Logic.

### 4.4 Window "Work Order" (`BXS_WorkOrder`)

Tab structure:

| Tab             | Table / filter                                                                                                       | Purpose                                                |
| --------------- | -------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| Work Order      | `BXS_WorkOrder`                                                                                                      | Header                                                 |
| Work Order Item | `BXS_WorkOrder_Item`                                                                                                 | Items handled by this work order                       |
| Open Items      | `BXS_AssetItem` with filter `BXS_Asset_ID=@Header@` AND `ItemStatus=Open` AND `Type ∈ {Defect, Schedule}`, read-only | Overview — what is currently open on the asset?        |

Buttons on the header tab: *Pull open items*, *Complete work order*
(see 2.5).

The read-only tab "Open Items" gives the dispatcher an overview when
creating a work order. In practice the *Pull open items* button
brings everything in, then individual lines are deleted or unticked
if they should not go to the workshop.

**Field group split in the header tab** (via `AD_FieldGroup`):

| Field group       | Fields                                                                                                            |
| ----------------- | ----------------------------------------------------------------------------------------------------------------- |
| Order preparation | `BXS_Asset_ID`, `Workshop_ID`, `Driver_ID`, `InternalContact_ID`, `ScheduledDate`, `EstimatedCost`, `Description` |
| After return      | `CompletionDate`, `ActualCost`, `ExternalDocumentNo`, `C_Invoice_ID`, `WorkOrderStatus`, `Note`                   |

Eases data entry — when creating, the dispatcher sees only the
relevant fields at the top and fills in the bottom block after
return.

## 5. Mapping to standards

| Standard concept                    | Implementation                                                                              |
| ----------------------------------- | ------------------------------------------------------------------------------------------- |
| ISO 14224 — Equipment Class         | `BXS_Asset.BXS_AssetClass_ID`                                                               |
| ISO 14224 — Equipment Hierarchy     | Deliberately not modelled                                                                   |
| ISO 14224 — Failure Mode / Severity | Deliberately not modelled (fleet too small)                                                 |
| DIN 31051                           | Conceptually (Defect ↔ repair, Schedule ↔ maintenance/inspection); not encoded as a field   |
| VDI 2890 — Maintenance planning     | `BXS_AssetItem` (Type=Schedule) + `BXS_ScheduleType`                                        |

## 6. Indexes (recommendation)

- `BXS_AssetItem (BXS_Asset_ID, Type, ItemStatus)` — the
  bread-and-butter index for the asset dossier and tab filters.
- `BXS_AssetItem (Type, DueDate, ItemStatus)` — global due-date list
  of maintenance schedules.
- `BXS_AssetItem (Type, ItemStatus, ReportedDate)` — global list of
  open defects.
- `BXS_WorkOrder (BXS_Asset_ID, WorkOrderStatus)` — for the asset
  dossier.
- `BXS_WorkOrder_Item (BXS_AssetItem_ID)` — reverse lookup "in which
  work orders did this item appear?".

## 7. Open points

### Sequence per type (FEH-…, TER-…, STA-…) — implementation

iDempiere knows exactly **one** `AD_Sequence` per table. Three
different prefixes depending on the `Type` value cannot be
expressed with the standard means directly.

**Solution:** three separate `AD_Sequence` records (`FEH`, `TER`,
`STA`) and a BeanShell `AD_Rule` registered as a **model validator**
on `BXS_AssetItem` (Rule Type = "Model Validator", Event Type =
"Table Before New"). The script pulls the matching sequence for the
current `Type` and sets `DocumentNo`.

Model validator rather than callout, because callouts can fire when
fields change in the tab — if the user then cancels the entry, the
sequence number is consumed and a gap appears. Model validator
events (`TYPE_BEFORE_NEW`) fire only on the real `PO.save()`, i.e.
without gaps.

`AD_Rule` of type "Model Validator" works in iDempiere without a
dedicated OSGi plugin — BeanShell is enough. Script size: ~10 lines.
