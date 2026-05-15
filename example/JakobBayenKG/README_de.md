# Jakob Bayen KG — Init-Daten

Customer-Deployment-Beispiel des Anlagenbuchs für die **Jakob Bayen KG**
(FreiBier-iDempiere, Mandant 1000000, Skript-Login Datalotte). Enthält
die echten Anfangsdaten der JBKG-Anlagenbestände — Fahrzeuge,
Anlagenklassen, Wartungstermin-Typen — sowie ein paar operative
Fehlerberichte aus dem Steppert-Briefing 8.5.2026.

Zielgruppe: produktive Bayen-Installation und Implementoren, die ein
echtes Customer-Deployment als Vorlage suchen.

## Verzeichnis

- `data/` — Source-of-Truth-CSVs (Klassen, Anlagen, Wartungstermine).
- `build_ods.py` — baut `anlagenbuch_init.ods` aus den CSVs. Enthält
  hardcodiert die operativen Demo-Fehlerberichte aus dem Steppert-
  Gespräch.
- `anlagenbuch_init.ods` — gebaute ODS, mitcommittet.
- `bootstrap_roles.py` — legt Master-Rolle `anlagenbuch` an, gibt ihr
  Process-/Window-Access und hängt sie in `Datalotte` (per psql-Fallback
  für die Window-Lookups) ein.
- `masterrolle_includes.csv` — Liste der menschlichen Login-Rollen
  (GF, Disposition, …), in die der iDempiere-Admin manuell die
  `anlagenbuch`-Master-Rolle einhängt.
- `config.env.example` / `config.env` — Login-Daten + Postgres-Settings
  (Bayen-Test-Instanz, Port 8444).
- `build.sh` — End-to-End: bootstrap + build_ods + ODS-Import.
- `Erfassungsvorlage_Anlagenbuch.ods` + `build_erfassungsvorlage_ods.py`
  — separates operatives Bayen-Tool (Eingabeformular für Fehlerberichte/
  Wartungstermine außerhalb des regulären Init-Flows). Kein Init-Bestand.

## Schnellstart

```bash
cp config.env.example config.env   # Passwort einsetzen
./build.sh
```

`build.sh` ruft hintereinander:
1. `bootstrap_roles.py` — Master-Rolle + Datalotte-Include
2. `build_ods.py` — CSVs → anlagenbuch_init.ods
3. `../../tools/import-ods.py --profile bayen` — ODS einspielen

`tools/profiles.local.yaml` muss ein Profil `bayen` enthalten — siehe
`tools/profiles.yaml.example`.

## Keine Anonymisierung

Die echten Bayen-Kennzeichen und Anlagen-Namen sind im Repo enthalten.
Bewusste Entscheidung, auch wenn das Repo öffentlich wird.
