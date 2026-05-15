🇬🇧 English · 🇩🇪 [Deutsch](README_de.md)

# Anlagenbuch

Anlagenbuch (German for *asset and maintenance log*) is a central
maintenance and defect-tracking system for assets (vehicles, forklifts,
parts of buildings, equipment), packaged as an iDempiere extension.
It was developed for Jakob Bayen KG and is delivered as a 2Pack —
installable into any iDempiere 11 without server access or a plugin
build.

**What it solves:** Defects, maintenance schedules and workshop visits
are recorded centrally, bound to the asset, and automatically pulled
together on every work order. TÜV, SP, UVV and warranty dates no
longer live in people's heads and paper folders, but in a searchable
record with a printable workshop dossier.

**Status:** The data model, the four windows, the workflow buttons
and the JasperReports are wired up and have been verified against a
local iDempiere 11 installation. Versioning will start once the
repository goes public.

## Quick start

1. **Understand the concept:** [`docs/Concept.md`](docs/Concept.md) —
   terminology, architectural decisions, and why specific paths were
   chosen.
2. **Use it:** [`docs/QuickReference.md`](docs/QuickReference.md)
   (PDF next to it) — what goes where, the typical workflows.
3. **Install it:** [`docs/Installation.md`](docs/Installation.md) —
   import the 2Pack, check sequences, load the initial CSV.

## Documentation overview

| File | Role | Audience |
| --- | --- | --- |
| [`docs/QuickReference.md`](docs/QuickReference.md) (+ PDF) | Daily use | End users |
| [`docs/Installation.md`](docs/Installation.md) | 2Pack install, sequences, permissions | Admins |
| [`docs/Concept.md`](docs/Concept.md) | Terminology, architectural decisions | Architects, contributors |
| [`docs/DataModel.md`](docs/DataModel.md) | Table and column reference | Developers, report authors |
| [`docs/Architecture.md`](docs/Architecture.md) | How it is built: generator, UUIDs, scripts | Contributors |
| [`docs/CHANGELOG.md`](docs/CHANGELOG.md) | What changed in which version | Everyone |
| `docs/Praesentation_Mitarbeiter.pdf` | Training material (German) | Trainers |

German translations of every documentation file live next to the
English ones with a `_de` suffix (e.g. `docs/Concept_de.md`).

### Example reports

Three PDFs shipped under `docs/` show the layout of the JasperReports
included in the 2Pack (currently German output):

- [`docs/Werkstattmappe_de.pdf`](docs/Werkstattmappe_de.pdf) — workshop
  dossier (defects + due maintenance + status, one asset)
- [`docs/Anlagenakte_de.pdf`](docs/Anlagenakte_de.pdf) — full asset record
- [`docs/Anlagenuebersicht_Status_de.pdf`](docs/Anlagenuebersicht_Status_de.pdf)
  — asset overview with current status

Historical working artefacts (early brainstorming,
implementation briefings) live in `docs/archiv/`.

## Repository layout

```
.
├── docs/                  User, admin and architecture documentation
├── src/                   Sources of the PDF outputs
├── 2pack/                 2Pack source (YAML specs) + build wrapper
├── scripts/               BeanShell scripts (embedded as AD_Rule)
├── reports/               JasperReports sources (DE + EN)
├── import/                CSV / ODS templates for initial loading
├── setup/                 Bootstrap scripts (roles, REST helpers)
├── tools/                 Vendored third-party tools (ODS importer)
├── example/               Deployment examples (GardenWorld demo, JBKG init)
└── uuids.csv              fixed UUIDs of all 2Pack objects
```

Architecture details: see `docs/Architecture.md`.

## Security

- `**/config.env` is listed in `.gitignore` — **never commit it.** Real
  REST endpoints and passwords stay in the local copy only.
- The tracked templates `setup/config.env.example`,
  `example/GardenWorld/config.env.example` and
  `example/JakobBayenKG/config.env.example` ship with **empty** password
  fields. Copy them to `config.env` next to the original and fill in
  your local credentials.
- For automation, prefer a dedicated lightweight REST user with the
  master role under `import/` rather than your personal admin login.

## License

GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later).
Full license text: `LICENSE`. SPDX identifier in every script header:
`SPDX-License-Identifier: AGPL-3.0-or-later`.

## Conventions

Tables, columns and UI default labels are in English (for community
suitability); German translations ship as iDempiere `*_Trl` records.
Documentation is bilingual (English is the default, German is parallel
with a `_de` suffix). Table prefix `BXS_` (BX Service in-house
convention).
