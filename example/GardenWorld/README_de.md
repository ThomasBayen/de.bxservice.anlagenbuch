# GardenWorld-Demo (Community)

Community-Demo des Anlagenbuchs für den **GardenWorld**-Mandanten der
iDempiere-Standardinstallation. **Inhaltlich englisch** — passt zum
englischen GardenWorld-Standard-Setup. Diese deutsche README beschreibt
nur Aufbau und Workflow; die Demo-Datensätze selbst sind in Englisch.

Zielgruppe: Implementoren, die das Plugin ausprobieren möchten, ohne
echte Stamm- oder Personendaten anzulegen. Alle Daten sind frei
erfunden und passen zum GardenWorld-Thema (Landschaftsbau:
Rasenmäher, Bewässerungspumpen, Pickups, Anhänger, Schuppen,
Kettensägen, Heckenschere, Laubbläser, Motorhacke, Schweißgerät,
Hochdruckreiniger).

## Verzeichnis

- `data/` — Source-of-Truth-CSVs (englisch):
  - `bpartner_employee_fix.csv` — TBB008-Workaround (siehe unten)
  - `classes.csv` — Anlagenklassen mit numerischen Werten
  - `schedules.csv` — Wartungstermin-Typen
  - `assets.csv` — Anlagen
  - `items.csv` — Demo-Einträge (Defects/Schedule/Status)
  - `workorders.csv` + `workorder_items.csv` — Werkstattaufträge
- `build_ods.py` — baut **eine** `anlagenbuch_demo.ods` aus allen CSVs.
- `anlagenbuch_demo.ods` — gebaute ODS, mitcommittet.
- `bootstrap_roles.py` — hängt die System-Master-Rolle `anlagenbuch`
  (kommt aus `Anlagenbuch_03_role.zip`) per `AD_Role_Included` in die
  Login-Rolle `GardenWorld Admin` ein. Sonst nichts. Identisch in
  Struktur zu `example/JakobBayenKG/bootstrap_roles.py`.
- `masterrolle_includes.csv` — Liste der Login-Rollen, in die die
  Master-Rolle eingehängt werden soll (hier nur `GardenWorld Admin`).
- `config.env.example` — Vorlage; nach `config.env` kopieren.
- `build.sh` — End-to-End: bootstrap + build_ods + ODS-Import +
  Smoke-Test. **Kein** separater SQL-Seed mehr — Werkstattaufträge
  laufen im gleichen ODS-Import wie die anderen Sheets.
- `cleanup.sh` — räumt den Demobestand (Tenant-Klassen, -Termine,
  -Anlagen, -Einträge, -WAU) aus Mandant 11. System-Records des
  2Packs (Client=0) bleiben unangetastet.

## Schnellstart

```bash
cp config.env.example config.env   # ggf. anpassen
./build.sh
```

`build.sh` ruft hintereinander:

1. `bootstrap_roles.py` — Master-Rolle in `GardenWorld Admin` einhängen
2. `build_ods.py` — alle CSVs → `anlagenbuch_demo.ods`
3. `../../tools/import-ods.py --profile gardenadmin` — ein Lauf, alle
   Sheets (BusinessPartner-Fix → Asset Classes → Schedule Types →
   Assets+Items → Work Orders+Positions)
4. `test/02_smoke_inserts.sh` — DB-Sanity-Check

## Demobestand

- **7 Tenant-Anlagenklassen** mit numerischen `Value`-Codes
  (`1100` Pickup, `1200` Trailer, `2100` Lawn Mower, `2200` Power Tool,
  `2300` Workshop Tool, `3100` Irrigation Pump, `5100` Shed).
  Zusammen mit den 6 System-Klassen aus dem 2Pack (`1000` Vehicle,
  `2000` Equipment, …) eine vollständige Hierarchie.
- **21 Anlagen** — 4 Mäher, 3 Pumpen, 2 Pickups, 2 Anhänger,
  3 Schuppen, 5 Motorgeräte, 2 Werkstattgeräte.
- **4 Tenant-Wartungstermin-Typen** (Annual Service, Safety Check,
  Fire-Safety Inspection, Pump Service) zusätzlich zu den vom 2Pack
  ausgelieferten System-Typen.
- **~45 Demo-Einträge** quer durch alle Anlagen: viele offene
  Fehlerberichte, anstehende Wartungstermine, Statusberichte, ein
  paar erledigte Einträge.
- **3 Werkstattaufträge** — `WAU-DEMO-001` (Pickup, `Draft`) bündelt
  vier Positionen; `WAU-DEMO-002` (`Released`); `WAU-DEMO-003`
  (`Completed`).

## Notizen für Mitwirkende

- AssetItem-Namen werden im Build mit dem Asset-Code präfixt
  (`PICKUP-01: Tailgate does not close cleanly`). Erst dadurch reicht
  `BXS_AssetItem_ID[Name]` als FK-Auflösung im WO-Item-Sheet — kein
  zusammengesetzter Schlüssel, kein separater Seed.
- Das `BusinessPartner`-Sheet, das als erstes läuft, setzt
  `IsEmployee=Y` an den drei BPartnern hinter den AD_Usern `Joe Sales`,
  `Carl Boss` und `Henry Seed`. Ohne diesen Fix filtert Reference 286
  („AD_User – Internal") sie aus der Reporter-Auswahl. Upstream-Bug:
  [`TBB008`](../../../../idempiere-core/bugreports/TBB008-gardenworld-employees-missing-flags/).
