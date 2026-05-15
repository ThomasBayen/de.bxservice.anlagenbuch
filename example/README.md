# Anlagenbuch — example deployments

Two fully separated example deployments. Both load their data via
`tools/import-ods.py` (no psql seed).

## [`GardenWorld/`](GardenWorld/) — community demo

GardenWorld-themed demo data (lawn mower, irrigation pump, pickup,
trailer, shed, chainsaw) for the GardenWorld tenant of stock iDempiere.
Login: `GardenAdmin`, tenant 11. All data is fictional.

**Purpose:** try the plugin quickly without touching real data.

## [`JakobBayenKG/`](JakobBayenKG/) — Bayen init data

Real initial data for Jakob Bayen KG (real-life vehicles with license
plates, asset classes, schedule types). Plus operational demo defect
reports from the Steppert briefing on 2026-05-08. Login: Datalotte
(script user), tenant 1000000.

**Purpose:** productive Bayen install + template for other customer
deployments.

## Which one for me?

| I want to… | Example |
|---|---|
| test the plugin locally with sample data | GardenWorld |
| build a customer deployment | JakobBayenKG as a template |
| run Jakob Bayen KG in production | JakobBayenKG |
