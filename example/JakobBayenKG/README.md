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
- `bootstrap_roles.py` — wires the (2Pack-delivered) system master role
  `anlagenbuch` into the script login role `Datalotte` via a REST
  `AD_Role_Included`, so the ODS import can see the BXS windows. Nothing
  more (it does **not** create the role — that comes from
  `Anlagenbuch_03_role.zip`).
- `masterrolle_includes.csv.example` — **example** list of human login
  roles (GF, Disposition, …). It is **not** applied automatically: which
  user login roles receive the `anlagenbuch` role is a deliberate **manual**
  admin decision (UI: Role → *Included Role* tab).
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
