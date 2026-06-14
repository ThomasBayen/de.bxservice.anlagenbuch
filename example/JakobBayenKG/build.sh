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

# ── 4. Reports auf deutsche JRXML-Variante: bewusster System-Admin-Schritt ─
# KEIN automatisches schreibendes SQL mehr. Das JasperReport-Feld der drei
# Print-Prozesse (AD_Process, System-Mandant) auf das `_de.jrxml`-Suffix zu
# stellen ist eine System-Level-Konfigurationsänderung — sie gehört in
# System-Administrator-Hände, nicht in die Tenant-Import-Identität Datalotte
# (die darf AD_Process korrekterweise nicht ändern: REST liefert dort 403).
#
# SQL-frei umstellen (eine der beiden Varianten):
#   • UI als System-Administrator: Anwendung → Bericht & Prozess →
#     BXS_Print_WorkshopDossier / _AssetDossier / _AssetStatusOverview →
#     Feld JasperReport: `_de` vor `.jrxml` einfügen.
#   • REST-PUT auf /api/v1/models/ad_process/{id} mit einer System-Rolle.
# (Nur als Dev/Test-Abkürzung mit direktem DB-Zugriff existiert weiterhin
#  setup/install_de_reports.sql — bewusst NICHT mehr aus build.sh aufgerufen.)
step "Reports-Sprache: SQL-frei als System-Admin umstellen (siehe docs/Installation.md)"

echo "[jbkg-build] fertig."
