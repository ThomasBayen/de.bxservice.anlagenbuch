🇬🇧 [English](README.md) · 🇩🇪 Deutsch

# Anlagenbuch

Repository: <https://github.com/ThomasBayen/de.bxservice.anlagenbuch>

Zentrales Wartungs- und Fehlerberichts-System für Anlagen (Fahrzeuge,
Stapler, Gebäudeteile, Geräte) als iDempiere-Erweiterung. Entwickelt
für die Jakob Bayen KG, ausgeliefert als 2Pack — installierbar in jedes
iDempiere 11 ohne Server-Zugriff oder Plugin-Build.

**Was es löst:** Mängel, Wartungstermine und Werkstattbesuche werden zentral
erfasst, an die Anlage gebunden und bei jedem Werkstattauftrag automatisch
zusammengeführt. TÜV-, SP-, UVV- und Garantietermine landen nicht mehr in
Köpfen und Papierordnern, sondern in einer durchsuchbaren Akte mit
druckbarer Werkstattmappe.

**Status:** Datenmodell, die vier Fenster, Workflow-Buttons und
JasperReports sind verkabelt und gegen eine lokale iDempiere-11-
Installation verifiziert. Versionsnummern kommen, sobald das
Repository öffentlich ist.

## Schnelleinstieg

1. **Konzept verstehen:** [`docs/Concept_de.md`](docs/Concept_de.md) — Begriffe,
   Architekturentscheidungen, warum bestimmte Wege gewählt wurden.
2. **Bedienen:** [`docs/QuickReference_de.md`](docs/QuickReference_de.md) (PDF
   daneben) — was man wo eingibt, typische Abläufe.
3. **Installieren:** [`docs/Installation_de.md`](docs/Installation_de.md) —
   2Pack importieren, Sequenzen prüfen, Initial-CSV laden.

## Dokumentationsübersicht

| Datei | Rolle | Zielgruppe |
| --- | --- | --- |
| [`docs/QuickReference_de.md`](docs/QuickReference_de.md) (+ PDF) | Tägliche Bedienung | Endanwender |
| [`docs/Installation_de.md`](docs/Installation_de.md) | 2Pack-Install, Sequenzen, Rechte | Admin |
| [`docs/Concept_de.md`](docs/Concept_de.md) | Begriffe, Architekturentscheidungen | Architekt, Mitwirkende |
| [`docs/DataModel_de.md`](docs/DataModel_de.md) | Tabellen-/Spalten-Referenz | Entwickler, Report-Bauer |
| [`docs/Architecture_de.md`](docs/Architecture_de.md) | Wie ist das gebaut: Generator, UUIDs, Skripte | Mitwirkende |
| [`docs/CHANGELOG.md`](docs/CHANGELOG.md) | Was kam in welcher Version dazu | Alle |
| `docs/Praesentation_Mitarbeiter.pdf` | Schulungsmaterial | Multiplikator |

### Beispiel-Reports

Drei PDFs unter `docs/` zeigen das Layout der JasperReports, die im
2Pack mitgeliefert werden (aktuell nur deutscher Output):

- [`docs/Werkstattmappe_de.pdf`](docs/Werkstattmappe_de.pdf) —
  Werkstattmappe (Fehler + fällige Wartungen + Status für eine Anlage)
- [`docs/Anlagenakte_de.pdf`](docs/Anlagenakte_de.pdf) — vollständige
  Anlagenakte
- [`docs/Anlagenuebersicht_Status_de.pdf`](docs/Anlagenuebersicht_Status_de.pdf)
  — Anlagenübersicht mit aktuellem Status

Historische Arbeitsartefakte (frühes Brainstorming,
Implementierungs-Briefing) liegen in `docs/archiv/`.

## Repo-Struktur

```
.
├── docs/                  Anwender-, Admin- und Architektur-Doku
├── src/                   Quellen der PDF-Outputs
├── 2pack/                 2Pack-Quelle (YAML-Specs) + Build-Wrapper
├── scripts/               BeanShell-Skripte (als AD_Rule eingebettet)
├── reports/               JasperReports-Quellen (DE + EN)
├── import/                CSV-/ODS-Vorlagen für Erstbefüllung
├── setup/                 Bootstrap-Skripte (Rollen, REST-Helper)
├── tools/                 Mitgelieferte Fremd-Tools (ODS-Importer)
├── example/               Deployment-Beispiele (GardenWorld-Demo, JBKG-Init)
└── uuids.csv              fixierte UUIDs aller 2Pack-Objekte
```

Architektur-Details siehe `docs/Architecture_de.md`.

Englische Übersetzungen liegen jeweils neben den deutschen Dateien
unter den gleichen Namen ohne `_de`-Suffix (z.B. `docs/Concept.md`).

## Security

- `**/config.env` steht in `.gitignore` — **niemals committen.** Echte
  REST-Endpunkte und Passwörter bleiben ausschließlich in der lokalen
  Kopie.
- Die getrackten Vorlagen `setup/config.env.example`,
  `example/GardenWorld/config.env.example` und
  `example/JakobBayenKG/config.env.example` liefern **leere**
  Passwort-Felder. Lokal nach `config.env` daneben kopieren und mit den
  eigenen Credentials befüllen.
- Für Automatisierung lieber einen leichtgewichtigen REST-User mit der
  Master-Rolle aus `import/` einrichten, statt den persönlichen
  Admin-Login zu verwenden.

## Lizenz

GNU Affero General Public License v3.0 oder neuer (AGPL-3.0-or-later).
Vollständiger Lizenztext: `LICENSE`. SPDX-Kennung am Anfang aller
Skripte: `SPDX-License-Identifier: AGPL-3.0-or-later`.

## Ausrichtung

Tabellen-, Spalten- und UI-Default-Labels englisch (Community-Tauglichkeit),
deutsche Übersetzungen als iDempiere-`*_Trl`-Records mitgeliefert. Doku
zweisprachig (Englisch Default, Deutsch parallel mit `_de`-Suffix).
Tabellen-Präfix `BXS_` (BX-Service-Hauskonvention).
