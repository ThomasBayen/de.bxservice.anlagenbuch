# GardenWorld demo

Community demo of the Anlagenbuch plugin for the **GardenWorld** tenant
shipped with iDempiere standard (landscaping universe: lawn mowers,
irrigation pumps, pickup trucks, trailers, garden sheds, chainsaws,
hedge trimmer, leaf blower, tiller, welder, pressure washer).

Audience: implementors who want to try the plugin without touching real
master/personal data. All data is fictional and themed around GardenWorld.

## Layout

- `data/` — source-of-truth CSVs (classes, assets, schedule types,
  demo items, work orders, work-order positions). Edit here, then
  rebuild the ODS / re-run the seed.
- `build_ods.py` — builds `anlagenbuch_demo.ods` from the CSVs.
- `anlagenbuch_demo.ods` — pre-built ODS, committed.
- `seed_workorders.py` — psql-seed for work orders + positions
  (cannot go through the ODS importer because BXS_AssetItem.DocumentNo
  is server-assigned by a TBN rule; the seed looks AssetItems up via
  (BXS_Asset.Value, BXS_AssetItem.Name) instead).
- `bootstrap_roles.py` — creates the `anlagenbuch` master role and
  includes it in `GardenAdmin`.
- `masterrolle_includes.csv` — login roles to wire `anlagenbuch` into
  (`GardenAdmin` only).
- `config.env.example` — template; copy to `config.env` and adjust.
- `build.sh` — end-to-end: bootstrap + build_ods + ODS import +
  work-order seed + smoke test.
- `cleanup.sh` — wipes the demo data from tenant 11.
- `test/02_smoke_inserts.sh` — light DB schema check.

## Quick start

```bash
cp config.env.example config.env   # adjust if needed
./build.sh
```

`build.sh` runs:
1. `bootstrap_roles.py` — master role + GardenAdmin include
2. `build_ods.py` — CSVs → anlagenbuch_demo.ods
3. `../../tools/import-ods.py --profile gardenadmin` — import the ODS
   (one file, one importer run — Business-Partner fix, asset classes,
   schedule types, assets+items, work orders+positions all in one go)
4. `test/02_smoke_inserts.sh` — DB sanity check

## Demo content (English by default)

- **7 tenant asset classes** with numeric `Value`s (`1100` Pickup, `1200`
  Trailer, `2100` Lawn Mower, `2200` Power Tool, `2300` Workshop Tool,
  `3100` Irrigation Pump, `5100` Shed). Numeric `Value`s leave gaps for
  customer-specific subclasses (the same scheme JBKG uses).
- **21 concrete assets**:
  - 4 lawn mowers (3 ride-on, 1 walk-behind)
  - 3 irrigation pumps (one out of service)
  - 2 pickups (Ford Ranger, Toyota Hilux)
  - 2 trailers (3.5 t / 1.5 t)
  - 3 sheds
  - 5 power tools (chainsaws, hedge trimmer, leaf blower, rotary tiller)
  - 2 workshop devices (welder, pressure washer)
- **4 tenant schedule types** (annual service, safety check, fire-safety
  check, pump service) on top of the system-shipped types (statutory
  vehicle inspection, warranty end, …).
- **~45 demo items** across all assets:
  - lots of **open defect reports** (pickup brakes, dull hedge blades,
    low pump pressure, warped trailer ramp, …)
  - **scheduled** safety / pump-service / fire-safety dates
  - **status** entries (intake reports, seasonal inspections)
  - a handful of **done** items so the history is non-empty
- **3 work orders**, one of them (`WAU-DEMO-001`) bundling **four**
  positions on the pickup (safety inspection + tailgate + trailer plug
  + brakes); the others demonstrate a `Released` and a `Completed`
  state.

## Notes

- AssetItem names are asset-code-prefixed in the CSVs that the ODS
  builder consumes (e.g. `PICKUP-01: Tailgate does not close cleanly`).
  This lets the WorkOrder-positions sheet reference each item through
  `BXS_AssetItem_ID[Name]` alone — no composite-key lookup, no separate
  SQL seed.
- The `BusinessPartner` sheet that runs first sets
  `IsEmployee=Y` on the three demo BPartners that back `Joe Sales`,
  `Carl Boss` and `Henry Seed`. Without that, reference 286
  (*„AD_User – Internal"*) filters them out of the reporter picker —
  see [`TBB008`](../../../../idempiere-core/bugreports/TBB008-gardenworld-employees-missing-flags/)
  for the upstream report.
