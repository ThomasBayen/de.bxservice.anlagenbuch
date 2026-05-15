# tools/ — bundled third-party tools

Files in this directory are **vendored** from external repositories.
They are included verbatim (with at most a license header added) to
keep the install path simple — no extra `git clone` for the user.

## `import-ods.py`

ODS multi-sheet importer for iDempiere. Reads an ODS file with a config
sheet and one or more data sheets, then drives `ImportCSVProcess`
through the iDempiere REST API to load each data sheet into a target
table.

- **Upstream:** <https://github.com/tbayen/idempiere-ods-import>
- **License:** AGPL-3.0-or-later (compatible with this project's
  AGPL-3.0-or-later).
- **Sync state:** commit `71cdac3` (2026-05-09).
- **Re-syncing on upstream fix:** overwrite `tools/import-ods.py`
  with the upstream version and update the *Sync state* line at the
  top of this file and at the top of `import-ods.py`.

### Setup

```bash
pip install -r tools/requirements.txt
```

Profiles live in `tools/profiles.yaml` (checked in — neutral
GardenWorld profile only) and `tools/profiles.local.yaml`
(gitignored — your own credentials). Copy
`tools/profiles.yaml.example` to `tools/profiles.local.yaml` and fill
in.

### Usage

```bash
python3 tools/import-ods.py --profile <name> path/to/data.ods
```

See `python3 tools/import-ods.py --help` for the full option set.

The Anlagenbuch example deployments call this tool from their
`build.sh` to load the demo / init data; see
`example/GardenWorld/build.sh` and `example/JakobBayenKG/build.sh`.
