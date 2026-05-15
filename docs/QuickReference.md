# Anlagenbuch — Quick Reference

This guide targets daily use. It describes **what to enter where** and
**how the typical workflows run** — not every single field.
Self-explanatory fields are skipped; only fields that influence
sorting, filters, downstream processes or reports are explained.

For readers in a hurry, two menu entries under **"Anlagenbuch"** are
enough — everything else is reachable from there:

- **Asset** — the record of a single asset. This is where defects
  are reported, sightings logged and schedules planned.
- **Work Order** — what we let a workshop handle.

---

## 1. Terminology (the essentials in one paragraph)

An **asset** is anything that should have a record — truck, car,
forklift, roller door, fire extinguisher, hand truck. Every asset
belongs to an **asset class** (e.g. "Truck 12 t+"), and every class
has a **category** (Vehicle, Equipment, Stationary, Building, IT,
Other) — the category determines which fields the form displays.

Three kinds of **items** are kept against an asset:

| Item         | When                                       | Document No |
| ------------ | ------------------------------------------ | ----------- |
| Defect       | A defect has been observed                 | `FEH-...`   |
| Schedule     | An appointment is planned or due (TÜV…)    | `TER-...`   |
| Status       | A sighting without any defect              | `STA-...`   |

Multiple items are bundled into a **work order** (`WAU-...`) when the
asset goes to a workshop.

---

## 2. Daily workflows

### 2.1 A defect is reported

Inbound: a driver or colleague calls or stops by.

1. Open menu **Anlagenbuch → Asset**, find the reported asset.
2. Tab **Defect**, new record.
3. **Required:** short description, date, priority.
4. Useful as soon as known: reporter, meter reading, cost estimate,
   long description.
5. Save. Status stays **Open** until the defect is resolved or pulled
   into a work order.

**Important only for reports and filters:**

- **Priority** controls the sort order in the asset dossier and the
  workshop dossier. High = top.
- **Reported date** is the sort key in the history. If the defect is
  older than the data entry, use the real date.

### 2.2 An asset goes to the workshop

1. Menu **Anlagenbuch → Work Order**, new record.
2. In the upper block **"Order preparation"** fill in: asset,
   workshop, driver, internal contact, scheduled date.
3. **Save** (otherwise the system doesn't yet know which asset this is
   about).
4. Press the button **"Pull open items"** — the open defects and
   overdue schedules of the asset are entered automatically.
5. In the detail tab **Items** delete or untick (`IsResolved=N`) what
   should **not** go to the workshop this time.
6. Use the print button in the work order's toolbar to print the
   **workshop dossier** — that's the paper that physically travels
   with the asset.

### 2.3 Return from the workshop

1. Open the matching work order.
2. Fill in the lower block **"After return"**: return date, actual
   cost, document number (invoice).
3. In tab **Items** check what was actually done — untick
   (`IsResolved=N`) the items that were not completed.
4. **Set status to "Completed"**. This triggers:
   - all ticked defects are set to **Done**;
   - for every completed schedule a **follow-up schedule** is
     automatically proposed;
   - unchecked items stay open and reappear next time you "Pull open
     items".

### 2.4 Completing a maintenance schedule individually

Some schedules don't need a work order (e.g. an internal visual
check). In that case:

1. Open the asset, tab **Schedule**, pick the item.
2. Enter a **completion date**, set status to **Done**, save.
3. The system creates the **follow-up schedule** automatically, dated
   to the first of the month of the completion date plus the
   default interval of the schedule type. **Adjust the date if the
   workshop or authority sets a different one** — TÜV is rarely
   exactly 12 months in practice.

### 2.5 Logging a sighting (status report)

Purpose: a gapless history, even when nothing is wrong. Use it for
the **initial intake of a new asset**, for **handovers between
drivers**, and for **regular sightings**.

1. Open the asset, tab **Status**, new record.
2. Date, short description ("Visual check, dispatcher"), meter
   reading. Save — the entry is stored as Done immediately.

### 2.6 Creating a new asset

1. Menu **Anlagenbuch → Asset**, new record.
2. Pick the **asset class** — it controls UI behaviour, the standard
   schedule types and the unit of measure for meter readings.
3. At minimum, fill **Value** (short identifier, e.g. license plate)
   and **Name**. The rest of the master data can come later.
4. In tab **Schedule** enter the first mandatory schedules (TÜV,
   UVV…). Follow-up schedules will be created automatically from the
   first completion.
5. In tab **Status** record the current state at intake (meter
   reading, general impression).

### 2.7 Decommissioning an asset

Sold, scrapped, retired — the asset should no longer appear in
reports, but the record should be preserved.

1. Open the asset.
2. Untick **Active** (`IsActive=N`).
3. Save. The asset no longer shows up in the standard filters; the
   record is still reachable via the "Show all" search.

---

## 3. Reports — when to use what

Three standard reports, all reachable via the print icon in the
respective window's toolbar or via the menu:

| Report                | Invoked from … | Purpose                                                                  |
| --------------------- | -------------- | ------------------------------------------------------------------------ |
| **Workshop Dossier**  | Work Order     | Physically travels to the workshop; receipt on return.                   |
| **Asset Dossier**     | Asset          | Master data, upcoming schedules, open defects, history.                  |
| **Asset Status List** | Anlagenbuch menu | Fleet-wide list, filtered by class, only assets with open items.       |

The overview is the tool for the weekly review in dispatch.

---

## 4. Small things people ask repeatedly

- **Who is "Reporter" and who is the "creator"?** Reporter = the
  person who reported the defect. Whoever fills in the form (usually
  the dispatcher) is recorded by iDempiere as the creator
  automatically — don't enter that separately.
- **Meter reading on every item?** Yes, if you can read it without
  effort. Even the status report benefits — it provides the only
  reliable meter readings between workshop visits.
- **Picked the wrong asset?** Deleting and re-creating the item is
  usually easier than moving it to a different asset.
- **"Mandatory" vs "Optional"?** It is set on the **schedule type**,
  not on the individual schedule — TÜV is always mandatory, a
  warranty reminder is always optional.

---

## 5. What the system does **not** (yet) do

- No driver app: defects continue to arrive verbally or by phone,
  the dispatcher types them in.
- No automatic pre-generation of recurring schedules — the follow-up
  schedule is only created once the current one is saved as Done.
- No KPIs / statistics in the first version. They will follow once
  there is enough data.
