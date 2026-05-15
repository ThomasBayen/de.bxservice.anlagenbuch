# Jakob Bayen KG — init data

Customer-deployment example of the Anlagenbuch plugin for **Jakob
Bayen KG** (FreiBier iDempiere, tenant 1000000, script login
Datalotte). Contains the real JBKG asset inventory — vehicles, asset
classes, schedule types — plus a handful of operational defect reports
from the Steppert briefing on 2026-05-08.

Audience: the productive Bayen install, plus implementors looking for a
template for a real customer deployment.

## Layout

- `data/` — source-of-truth CSVs (classes, assets, schedule types).
- `build_ods.py` — builds `anlagenbuch_init.ods` from the CSVs. Hard-
  codes the operational demo defect reports from the Steppert briefing.
- `anlagenbuch_init.ods` — pre-built ODS, committed.
- `bootstrap_roles.py` — creates the `anlagenbuch` master role with
  process/window access and includes it in `Datalotte` (uses a psql
  fallback for window lookups since Datalotte has no REST access to
  `AD_Window`).
- `masterrolle_includes.csv` — list of human login roles (GF,
  Disposition, …) the iDempiere admin manually wires to `anlagenbuch`.
- `config.env.example` / `config.env` — credentials and Postgres
  settings (Bayen test instance, port 8444).
- `build.sh` — end-to-end: bootstrap + build_ods + ODS import.
- `Erfassungsvorlage_Anlagenbuch.ods` + `build_erfassungsvorlage_ods.py`
  — separate operational Bayen tool (data-entry form for defect/
  schedule items outside the regular init flow). Not part of init.

## Quick start

```bash
cp config.env.example config.env   # fill in password
./build.sh
```

`tools/profiles.local.yaml` must contain a `bayen` profile — see
`tools/profiles.yaml.example`.

## No anonymisation

Real Bayen license plates and asset names are in the repo. Deliberate
decision even with the repo being public.
