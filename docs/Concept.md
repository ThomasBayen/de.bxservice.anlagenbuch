# Anlagenbuch — Concept

## 1. Problem statement

In the company, defects on vehicles, equipment and other assets have
so far been reported verbally or by shouting across the yard. Reports
get lost, are not linked to upcoming workshop visits, and dates
(TÜV, SP, UVV, warranty) are scattered across people's heads,
calendars and paper folders. Example incident: a truck comes back from
its TÜV appointment; the broken loading flap, known about for days,
was not handled because nobody in the office had the information.
Consequence: two additional 25 km trips with two people each.

The goal is a central, electronic asset and maintenance log
(Anlagenbuch):

- Every defect report is captured promptly, from anywhere, in one
  place.
- For every asset (truck, car, forklift, roller door, fire
  extinguisher, …) it is visible at a glance what is open and which
  dates are upcoming.
- Workshop visits are bundled as a work order — when the car goes for
  TÜV, the open defect reports automatically come back into view.
- A printable dossier per asset accompanies the asset to the
  workshop.

## 2. Scope

### Asset classes covered

- Vehicles (trucks, cars)
- Industrial trucks (forklifts)
- Technical equipment (roller doors, fire extinguishers, sweepers,
  hand trucks, …)
- Real estate (parts of buildings, trades such as roof, heating,
  electrics)
- IT hardware (servers, switches) — more inventory-like, secondary

The data model is asset-type agnostic; depending on class, certain
fields are shown or hidden in the UI.

### Functional scope of the first version

- **Asset master data** with all type-spanning fields.
- **Defect reports** captured, prioritised, closed.
- **Work orders** as a bundle of multiple defect reports, with the
  workshop business partner, meter reading, cost, invoice link.
- **Maintenance schedules** for TÜV, SP, UVV, warranty etc.;
  mandatory/optional flag.
- **Print reports** (asset dossier, workshop dossier) via Jasper.
- **Initial CSV loading** from existing `M_Resource` records.

### Deliberate non-goals of this version

- No driver app (later project).
- No equipment hierarchy / component modelling.
- No automatic pre-generation of recurring schedules.
- No KPIs (MTBF, MTTR, availability) — coming once enough data is
  collected.
- No TCO reporting.
- No link to fixed-asset accounting (`A_Asset`).

## 3. Decisions made

### Terminology and language

- Main term for a defect report: **Defect** (German user-facing
  label: *Fehlerbericht*).
- Table names, column names and UI default labels are in English (for
  community suitability). German labels are shipped as iDempiere
  translations (`AD_Element_Trl` / `AD_Field_Trl` with language
  `de_DE`). Documentation is bilingual.
- Table prefix: `BXS_` (BX Service in-house convention, consistent
  with other BXS plugins).
- **JasperReports localisation:** two jrxml files per
  report — one with English wording (default), one `_de` variant.
  Rationale: Jasper resource bundles (`$R{key}` +
  `report_de.properties`) would be the standard Jasper route, but
  they do not solve the actual consistency problem — if an admin
  changes a UI label in iDempiere, the report property stays the
  same. The extra effort is not worth it. A future option is to
  pull column labels via JOIN to `AD_Element_Trl` straight from
  iDempiere — the only variant that automatically reflects UI
  changes in the report. Static headings would then come from
  `AD_Message`.

### Asset model

- One table for all asset classes, with type-dependent show/hide in
  the UI.
- No coupling to iDempiere's `A_Asset`. Rationale: `A_Asset` is
  tightly coupled to fixed-asset accounting and automatic
  depreciation postings; we do not want that around our neck.

### Asset Category and Asset Class

Above the `BXS_AssetClass` level sits a **meta category**
(`BXS_AssetCategory`, list with 6 fixed values: `Vehicle`,
`Equipment`, `Stationary`, `Building`, `IT`, `Other`). It controls
UI behaviour and workflow logic, while the class is the
business-level subdivision.

Rationale: users want to be able to create their own classes (e.g.
"Truck <7.5 t" with a different TÜV interval than "Truck 12 t+")
without code or display logic having to track those classes. The
split allows any number of classes per category; the system knows
through the category how the asset "behaves" (meter reading visible?
Driver required on the work order? Fixed or mobile location?).
`BXS_ScheduleType` primarily attaches to the class — TÜV applies to
a particular truck class, not to all vehicles, because the interval
can be class-specific.

### Items (Defect, Schedule, Status)

In data terms these three concepts are **one table** (`BXS_AssetItem`)
with a discriminator field `Type`. Collective term in user-facing
documentation: **item**. In developer documentation and DB table
names, `AssetItem` remains as the technical term. This greatly
simplifies the work order (one mixed detail list instead of two) and
the asset dossier. In the UI the three appear as separate detail
tabs on the asset window, each with its own filter and field
visibility — the user sees three clearly separated views.

- **Defect (`Type=Defect`):** someone has observed a defect. Fields:
  short description (Name), long description, reported date,
  reporter, priority (low/medium/high), meter reading, cost
  estimate. Closed manually or via a work order.
- **Schedule (`Type=Schedule`):** an appointment (TÜV/SP/UVV/warranty
  /…) is due on a particular date. Fields: schedule type
  (`ScheduleType`), due date, meter reading at completion,
  follow-up reference. Mandatory/optional comes from the schedule
  type. On completion a script automatically creates the follow-up:
  `DueDate = first day of the month of the completion date +
  default interval`. Rationale: TÜV/SP/UVV intervals run from the
  inspection date, not from the previous target date. Can also be
  attached to a work order.
- **Status (`Type=Status`):** a point-in-time snapshot without any
  defect — e.g. on initial intake ("Vehicle handed over, mileage
  324 850, visibly in order") or as a regular sighting. Stored as
  Done immediately, no work order. Provides a gap-free history,
  including meter readings.

**Work order detail tab:** a single list in which defects and
schedules appear mixed — typically a TÜV visit handles the TÜV
schedule itself plus a couple of open defects. When the work order
is closed, all ticked items are set to Done; for schedules the
follow-up schedule is additionally created.

### Work order

- An independent document, bundling N items (defects + schedules,
  mixed) through the detail tab `BXS_WorkOrder_Item`.
- Fields before the workshop visit: asset, workshop (`C_BPartner`),
  driver (`Driver_ID` → `AD_User`), internal contact
  (`InternalContact_ID` → `AD_User`; phone number comes from
  `AD_User.Phone`).
- Fields after return: return date, final cost, document number
  (invoice or order confirmation) or invoice link (`C_Invoice`).
- **iDempiere form:** split fields into two regions via
  `AD_FieldGroup` — *Order preparation* at the top (workshop,
  driver, contact, dates), *After return* below (return date, cost,
  document number, status). Eases data entry for the dispatcher.
- The link record has the flag `IsResolved` (default `Y`).
- **Button "Pull open items":** automatically adds every open defect
  and schedule of the asset as a work order line. The dispatcher
  then deletes or unticks anything that should not go to the
  workshop.
- **Completion workflow** (script process `AD_Rule`, BeanShell/Groovy):
  - Sets the status of all linked items with `IsResolved=Y` to
    `Done`, with `CompletionDate=today`.
  - Items with `IsResolved=N` stay open (waiting for the next work
    order).
  - For each completed schedule item: automatically creates a new
    schedule record with default values (asset, ScheduleType
    inherited; `DueDate = firstOfMonth(CompletionDate) +
    ScheduleType.DefaultIntervalMonths`; `ItemStatus=Open`). Sets
    `NextItem_ID` on the old row.
  - Sets the work order status to `Completed`.
- TÜV intervals are rarely exactly 12 months in practice — the
  proposed follow-up date can be adjusted before saving.

### Misc

- **Decommissioning** = the record is set inactive (`IsActive=N`,
  iDempiere standard). History is preserved.
- **Documents on an asset** use the iDempiere built-in
  (`AD_Attachment`); not modelled separately.
- **Cost fields:** the estimate on the defect; final cost and
  invoice link on the work order.

## 4. Delivery

### 2Pack + JRXML + scripts

Initial installation runs entirely through the standard 2Pack window,
**without server or plugin access**. Contains:

- 2Pack XML with tables, columns, windows, tabs, lists, workflows,
  processes.
- Scripts (`AD_Rule`) for the schedule follow-up proposal and the
  work order completion.
- JRXML reports for asset dossier and workshop dossier.
- CSV import template for inventory data from `M_Resource`.

All UUIDs (tables, columns, windows, tabs, lists, reports, rules)
are fixed once and version-tracked, so any future migration into an
OSGi plugin can pick up existing records instead of duplicating them.

### Possible future plugin (optional)

Wrapping the deliverable as an OSGi bundle
`de.bxservice.anlagenbuch` becomes relevant once

- the logic grows beyond what can be maintainably expressed in
  `AD_Rule` scripts,
- Java tests, IDE comfort or ModelValidator hooks are required,
- the module is published as a community contribution.

The plugin would ship the same 2Pack as a resource. Thanks to the
stable UUIDs, existing records are not duplicated on plugin import.

## 5. Glossary

| English / Table                 | German                | Meaning                                                                                                |
| ------------------------------- | --------------------- | ------------------------------------------------------------------------------------------------------ |
| `BXS_Asset`                     | Anlage                | Managed object: vehicle, equipment, system, part of a building.                                        |
| `BXS_AssetCategory` (list)      | Anlagen-Kategorie     | Meta level: Vehicle, Equipment, Stationary, Building, IT, Other. Controls UI behaviour.                |
| `BXS_AssetClass`                | Anlagenklasse         | Business-level subdivision (e.g. several truck classes with different intervals). References category. |
| `BXS_AssetItem`                 | Eintrag               | Collective term for defect, schedule or status report (one table, discriminator `Type`).               |
| `BXS_AssetItem` (Type=Defect)   | Fehlerbericht         | Observed defect on an asset. Has priority and status.                                                  |
| `BXS_AssetItem` (Type=Schedule) | Wartungstermin        | Planned or due appointment (TÜV, SP, UVV, warranty, …).                                                |
| `BXS_AssetItem` (Type=Status)   | Statusbericht         | Point-in-time snapshot without any defect, e.g. on initial intake. Stored as Done immediately.         |
| `BXS_WorkOrder`                 | Werkstattauftrag      | Bundle of several items for one workshop visit.                                                        |
| `BXS_ScheduleType`              | Wartungstermin-Typ    | Class of the schedule, with default interval and mandatory/optional default.                           |
| Mandatory / Optional            | Pflicht / Kür         | Statutory (TÜV, UVV) vs recommended. Default is on the schedule type.                                  |
| `C_BPartner` (Workshop)         | Werkstatt             | The business partner that executes the work order.                                                     |

## 6. Norm references (informative)

The concept is informed by the relevant standards without claiming
certification:

- **DIN 31051** — pillars of maintenance / inspection / repair /
  improvement; conceptual separation between planned activity
  (Schedule) and reactive remediation (Defect), not encoded as a
  field.
- **ISO 14224** — Equipment Class implemented as `BXS_AssetClass`.
  Deliberately omitted: equipment hierarchy, failure mode and
  severity (no analytical value at our fleet size that would justify
  the data-entry effort).
- **VDI 2890** — inspiration source for maintenance planning.
- **ISO 55000** — strategic level, out of scope.
