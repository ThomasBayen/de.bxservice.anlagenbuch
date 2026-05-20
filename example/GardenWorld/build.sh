#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# GardenWorld-Community-Demo: nachdem das Plugin via install.sh
# installiert ist, baut dieses Skript die Master-Rolle, hängt sie an die
# GardenAdmin-Login-Rolle und spielt den Demo-Datenbestand per
# ODS-Importer ein.
#
# Voraussetzung:
#   1. install.sh wurde vorher gegen den Ziel-iDempiere gefahren.
#   2. example/GardenWorld/config.env existiert (cp .example und anpassen).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONFIG_ENV="$SCRIPT_DIR/config.env"

if [ ! -f "$CONFIG_ENV" ]; then
    echo "FEHLER: $CONFIG_ENV fehlt." >&2
    echo "Erst: cp $SCRIPT_DIR/config.env.example $CONFIG_ENV" >&2
    exit 2
fi

# shellcheck disable=SC1090
set -a; . "$CONFIG_ENV"; set +a

step() { printf '\n[gw-build] %s\n' "$*"; }

# ── 1. Master-Rolle anlagenbuch + GardenAdmin-Include ────────────────────
step "Bootstrap Master-Rolle + GardenAdmin-Include"
python3 "$SCRIPT_DIR/bootstrap_roles.py"

# ── 2. ODS bauen ────────────────────────────────────────────────────────
step "Baue anlagenbuch_demo.ods aus data/*.csv"
python3 "$SCRIPT_DIR/build_ods.py"

# ── 3. ODS importieren ──────────────────────────────────────────────────
step "Importiere anlagenbuch_demo.ods (Profil: ${ODS_PROFILE:-gardenadmin})"
python3 "$REPO_ROOT/tools/import-ods.py" \
    --profile "${ODS_PROFILE:-gardenadmin}" \
    "$SCRIPT_DIR/anlagenbuch_demo.ods"

# ── 4. Smoke-Test ───────────────────────────────────────────────────────
# Werkstattaufträge + Positionen sind seit Punkt 5 (siehe TODO/Plan) Teil
# derselben ODS — kein separater SQL-Seed mehr nötig.
if [ -x "$SCRIPT_DIR/test/02_smoke_inserts.sh" ]; then
    step "Smoke-Test"
    bash "$SCRIPT_DIR/test/02_smoke_inserts.sh"
fi

echo "[gw-build] fertig."
