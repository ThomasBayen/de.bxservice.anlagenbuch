#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# JBKG-Beispiel-Deployment: nachdem das Plugin via install.sh installiert
# ist, baut dieses Skript die JBKG-Master-Rolle, hängt sie an die
# Datalotte-Login-Rolle und spielt den Bayen-Init-Datenbestand per
# ODS-Importer ein.
#
# Voraussetzung:
#   1. install.sh wurde vorher gegen den Ziel-iDempiere gefahren.
#   2. example/JakobBayenKG/config.env existiert (cp .example und ausfüllen).
#   3. tools/profiles.local.yaml enthält ein Profil mit den Bayen-Login-
#      Daten (Datalotte). config.env.ODS_PROFILE zeigt darauf.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONFIG_ENV="$SCRIPT_DIR/config.env"

if [ ! -f "$CONFIG_ENV" ]; then
    echo "FEHLER: $CONFIG_ENV fehlt." >&2
    echo "Erst: cp $SCRIPT_DIR/config.env.example $CONFIG_ENV" >&2
    echo "und Werte (Login-Rolle, Passwort, …) ausfüllen." >&2
    exit 2
fi

# shellcheck disable=SC1090
set -a; . "$CONFIG_ENV"; set +a

step() { printf '\n[jbkg-build] %s\n' "$*"; }

# ── 1. Master-Rolle anlagenbuch + Datalotte-Include ──────────────────────
step "Bootstrap Master-Rolle + Datalotte-Include"
python3 "$SCRIPT_DIR/bootstrap_roles.py"

# ── 2. ODS bauen ─────────────────────────────────────────────────────────
step "Baue anlagenbuch_init.ods aus data/*.csv"
python3 "$SCRIPT_DIR/build_ods.py"

# ── 3. ODS in den Bayen-Mandant einspielen ───────────────────────────────
# Für den Live-Mandanten: KEIN automatischer cleanup vorgeschaltet — die
# Init-Daten sollen idempotent re-importiert werden können (ImportMode=M
# updated, nicht überschreiben).
step "Importiere anlagenbuch_init.ods (Profil: ${ODS_PROFILE:-bayen})"
python3 "$REPO_ROOT/tools/import-ods.py" \
    --profile "${ODS_PROFILE:-bayen}" \
    "$SCRIPT_DIR/anlagenbuch_init.ods"

# ── 4. Reports auf deutsche JRXML-Variante umstellen ─────────────────────
# Im Bayen-Mandant sollen die mitgelieferten Reports deutsch drucken.
# install_de_reports.sql ist idempotent (NOT LIKE '%_de.jrxml'-Guard).
# Voraussetzung: setup/config.env enthält die PG-Connection (PGHOST/
# PGPORT/PGUSER/PGPASSWORD/PGDATABASE) — die liest install.sh ohnehin.
SETUP_CONFIG="$REPO_ROOT/setup/config.env"
if [ -f "$SETUP_CONFIG" ]; then
    # shellcheck disable=SC1090
    set -a; . "$SETUP_CONFIG"; set +a
    step "Stelle Reports auf deutsche JRXML-Variante um (install_de_reports.sql)"
    PGPASSWORD="${PGPASSWORD:-}" psql \
        -h "${PGHOST:-localhost}" -p "${PGPORT:-5432}" \
        -U "${PGUSER:-adempiere}" -d "${PGDATABASE:-idempiere}" \
        -f "$REPO_ROOT/setup/install_de_reports.sql"
else
    echo "[jbkg-build] Warnung: $SETUP_CONFIG fehlt — Reports bleiben englisch." >&2
    echo "                       Anlegen via cp setup/config.env.example setup/config.env" >&2
fi

echo "[jbkg-build] fertig."
