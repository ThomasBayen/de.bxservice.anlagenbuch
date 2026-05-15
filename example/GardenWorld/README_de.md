# GardenWorld-Demo

Community-Demo des Anlagenbuchs für den **GardenWorld**-Mandanten der
iDempiere-Standardinstallation (Landschaftsbau-Universum: Rasenmäher,
Bewässerungspumpen, Pickup, Anhänger, Gartenhäuschen, Kettensäge).

Zielgruppe: Implementoren, die das Plugin ausprobieren möchten, ohne
echte Stamm- oder Personendaten anzulegen. Alle Daten sind frei
erfunden und passen zum GardenWorld-Thema.

## Verzeichnis

- `data/` — Source-of-Truth-CSVs (Klassen, Anlagen, Wartungstermine,
  Demo-Einträge). Hier pflegen, dann ODS neu bauen.
- `build_ods.py` — baut `anlagenbuch_demo.ods` aus den CSVs.
- `anlagenbuch_demo.ods` — gebaute ODS, mitcommittet.
- `bootstrap_roles.py` — legt Master-Rolle `anlagenbuch` an und
  hängt sie in `GardenAdmin` ein.
- `masterrolle_includes.csv` — Login-Rollen, die `anlagenbuch`
  einbinden sollen (hier nur `GardenAdmin`).
- `config.env.example` — Vorlage; nach `config.env` kopieren und
  Passwort einsetzen.
- `build.sh` — End-to-End: bootstrap + build_ods + ODS-Import + Smoke-Test.
- `cleanup.sh` — räumt den Demobestand aus Mandant 11 wieder ab.
- `test/02_smoke_inserts.sh` — schlanker DB-Schema-Check.

## Schnellstart

```bash
cp config.env.example config.env   # ggf. anpassen
./build.sh
```

`build.sh` ruft hintereinander:
1. `bootstrap_roles.py` — Master-Rolle + GardenAdmin-Include
2. `build_ods.py` — CSVs → anlagenbuch_demo.ods
3. `../../tools/import-ods.py --profile gardenadmin` — ODS einspielen
4. `test/02_smoke_inserts.sh` — DB-Sanity-Check

## Demobestand

- 6 Anlagenklassen (Rasenmäher, Bewässerungspumpe, Pickup, Anhänger,
  Gartenhäuschen, Motorgerät)
- 7 konkrete Anlagen
- 3 Wartungstermin-Typen (TÜV, Jahresinspektion, UVV)
- 5 Demo-Einträge (2 offene Fehlerberichte, 1 anstehender Wartungstermin,
  1 erledigte Erstaufnahme, 1 erledigte Jahresinspektion)
