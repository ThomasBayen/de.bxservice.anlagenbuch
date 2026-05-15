# GardenWorld demo

Community demo of the Anlagenbuch plugin for the **GardenWorld** tenant
shipped with iDempiere standard (landscaping universe: lawn mowers,
irrigation pumps, pickup truck, trailer, garden shed, chainsaw).

Audience: implementors who want to try the plugin without touching real
master/personal data. All data is fictional and themed around GardenWorld.

## Layout

- `data/` — source-of-truth CSVs (classes, assets, schedule types,
  demo items). Edit here, then rebuild the ODS.
- `build_ods.py` — builds `anlagenbuch_demo.ods` from the CSVs.
- `anlagenbuch_demo.ods` — pre-built ODS, committed.
- `bootstrap_roles.py` — creates the `anlagenbuch` master role and
  includes it in `GardenAdmin`.
- `masterrolle_includes.csv` — login roles to wire `anlagenbuch` into
  (`GardenAdmin` only).
- `config.env.example` — template; copy to `config.env` and adjust.
- `build.sh` — end-to-end: bootstrap + build_ods + ODS import + smoke test.
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
4. `test/02_smoke_inserts.sh` — DB sanity check

## Demo content

- 6 asset classes (mower, irrigation pump, pickup, trailer, shed,
  power tool)
- 7 concrete assets
- 3 schedule types (TÜV, annual service, safety check)
- 5 demo items (2 open defects, 1 upcoming schedule, 1 done status,
  1 completed annual service)
