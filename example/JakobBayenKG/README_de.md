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
- `bootstrap_roles.py` — hängt die (vom 2Pack gelieferte) System-Master-
  Rolle `anlagenbuch` per REST `AD_Role_Included` in die Skript-Login-Rolle
  `Datalotte` ein, damit der ODS-Import die BXS-Fenster sieht. Mehr nicht
  (legt die Rolle **nicht** an — die kommt aus `Anlagenbuch_03_role.zip`).
- `masterrolle_includes.csv.example` — **Beispiel**liste menschlicher
  Login-Rollen (GF, Disposition, …). Wird **nicht** automatisch angewendet:
  in welche Anwender-Rollen die `anlagenbuch`-Rolle eingehängt wird, ist eine
  bewusste **manuelle** Admin-Entscheidung (UI: Role → Tab *Included Role*).
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

## Voraussetzungen an die Login-Rolle (Datalotte)

Der REST-Ablauf läuft **ausschließlich** über den Application Server (kein
direktes SQL). Damit `build.sh` ohne Handgriffe durchläuft, muss die
Skript-Login-Rolle (`Datalotte`, `LOGIN_ROLE_NAME`/`role_id`) **zwei**
Eigenschaften haben — vom Admin einmalig im UI gesetzt:

1. **Window-Access auf das Fenster „Role"** — sonst kann
   `bootstrap_roles.py` den `AD_Role_Included` nicht per REST anlegen
   (REST liefert sonst leere/`403`-Antworten auf `ad_role`).
2. **Voller Tabellenzugriff — keine aktive *exklusive* Whitelist.** Trägt
   die Rolle (oder eine von ihr aktiv inkludierte Rolle) `AD_Table_Access`-
   Einträge mit `AccessTypeRule='A'`/`IsExclude='N'`, ist der Zugriff auf
   **nur** diese Tabellen beschränkt. Dann filtert `GET /api/v1/windows`
   die BXS-Fenster (System-Dictionary) vor der eigentlichen Access-Prüfung
   weg → der ODS-Import findet seine Zielfenster nicht. Die Rolle braucht
   daher **keine** exklusive Whitelist (Standard-iDempiere: keine
   `AD_Table_Access`-Zeilen = Zugriff auf alle Tabellen).

Prüfen (lesend): in der DB hat `Datalotte` 0 `AD_Table_Access`-Zeilen und
keine **aktive** Whitelist-Rolle inkludiert. Nach einem DB-Refresh aus Prod
ist das automatisch gegeben, solange die Prod-Datalotte-Rolle so bleibt.

## Keine Anonymisierung

Die echten Bayen-Kennzeichen und Anlagen-Namen sind im Repo enthalten.
Bewusste Entscheidung, auch wenn das Repo öffentlich wird.
