#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Anlagenbuch — Installations-Skript für die generischen Community-Teile.
#
# Baut das 2Pack (falls fehlt/veraltet), spielt es in $IDEMPIERE_HOME ein,
# kopiert JRXML-Reports nach $IDEMPIERE_HOME/reports/, korrigiert den
# Menü-Tree und führt den Schema-Smoke-Test aus.
#
# Voraussetzung: setup/config.env (Kopie von setup/config.env.example,
# Werte gefüllt).
#
# Optionen:
#   --standalone     Standalone-Java-Apply statt Server-Restart (Server muss
#                    in dem Fall NICHT laufen).
#   --skip-build     Vorhandenes 2pack/Anlagenbuch.zip nutzen.
#   --with-de        Report-Suffix-Switch auf _de.jrxml mitziehen
#                    (führt setup/install_de_reports.sql aus).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
CONFIG_ENV="$REPO_ROOT/setup/config.env"
# Zwei ZIPs: Schema-2Pack zuerst, Daten-2Pack danach (alphabetisch sortiert
# vom iDempiere-Folder-Apply). Siehe 2pack/build.sh für die Begründung.
ZIP_SCHEMA="$REPO_ROOT/2pack/Anlagenbuch_01_schema.zip"
ZIP_DATA="$REPO_ROOT/2pack/Anlagenbuch_02_data.zip"

STANDALONE=0
SKIP_BUILD=0
WITH_DE=0
for arg in "$@"; do
    case "$arg" in
        --standalone)     STANDALONE=1 ;;
        --skip-build)     SKIP_BUILD=1 ;;
        --with-de)        WITH_DE=1 ;;
        -h|--help)
            grep '^# ' "$0" | sed 's/^# \?//'
            exit 0 ;;
        *) echo "Unbekanntes Flag: $arg" >&2; exit 2 ;;
    esac
done

if [ ! -f "$CONFIG_ENV" ]; then
    echo "FEHLER: $CONFIG_ENV fehlt." >&2
    echo "Erst kopieren: cp setup/config.env.example setup/config.env" >&2
    echo "und Werte ausfüllen (IDEMPIERE_HOME, PG*, …)." >&2
    exit 2
fi

# shellcheck disable=SC1090
set -a; . "$CONFIG_ENV"; set +a

: "${IDEMPIERE_HOME:?IDEMPIERE_HOME muss in config.env gesetzt sein}"

if [ ! -d "$IDEMPIERE_HOME" ]; then
    echo "FEHLER: IDEMPIERE_HOME='$IDEMPIERE_HOME' existiert nicht." >&2
    exit 2
fi

step() { printf '\n[install] %s\n' "$*"; }

# ── 1. 2Pack bauen, wenn nötig ────────────────────────────────────────────
needs_build() {
    [ "$SKIP_BUILD" -eq 1 ] && return 1
    [ ! -f "$ZIP_SCHEMA" ] && return 0
    [ ! -f "$ZIP_DATA" ]   && return 0
    # Source-Dateien neuer als die ältere der beiden ZIPs?
    local older_zip="$ZIP_SCHEMA"
    [ "$ZIP_DATA" -ot "$ZIP_SCHEMA" ] && older_zip="$ZIP_DATA"
    if find "$REPO_ROOT/2pack/source" "$REPO_ROOT/scripts" "$REPO_ROOT/reports" \
            -type f \( -name '*.yaml' -o -name '*.bsh' -o -name '*.jrxml' \
                    -o -name '*.py' -o -name 'PackageDoc.xml' \) \
            -newer "$older_zip" 2>/dev/null | grep -q .; then
        return 0
    fi
    return 1
}

if needs_build; then
    step "Baue 2Packs..."
    bash "$REPO_ROOT/2pack/build.sh"
else
    step "2Packs sind aktuell — nutze $ZIP_SCHEMA + $ZIP_DATA"
fi

# ── 2. ZIPs nach migration/zip_2pack/ ─────────────────────────────────────
# Beide ZIPs bekommen denselben Timestamp-Präfix; das `_01_` / `_02_` im
# Dateinamen sorgt für die korrekte Apply-Reihenfolge (PIPO sortiert
# alphabetisch). Schema-ZIP committed bevor Daten-ZIP startet — siehe
# Begründung in 2pack/build.sh.
STAMP="$(date +%Y%m%d%H%M)"
DROP_SCHEMA="${STAMP}_SYSTEM_Anlagenbuch_01_schema.zip"
DROP_DATA="${STAMP}_SYSTEM_Anlagenbuch_02_data.zip"

if [ "$STANDALONE" -eq 1 ]; then
    DROP_DIR="$(mktemp -d -t anlagenbuch_install.XXXXXX)"
    step "Standalone-Apply via $DROP_DIR"
    cp "$ZIP_SCHEMA" "$DROP_DIR/$DROP_SCHEMA"
    cp "$ZIP_DATA"   "$DROP_DIR/$DROP_DATA"
    if [ ! -x "$IDEMPIERE_HOME/utils/RUN_ApplyPackInFromFolder.sh" ]; then
        echo "FEHLER: $IDEMPIERE_HOME/utils/RUN_ApplyPackInFromFolder.sh nicht ausführbar." >&2
        exit 1
    fi
    bash "$IDEMPIERE_HOME/utils/RUN_ApplyPackInFromFolder.sh" "$DROP_DIR"
    rm -rf "$DROP_DIR"
else
    DROP_DIR="$IDEMPIERE_HOME/migration/zip_2pack"
    mkdir -p "$DROP_DIR"
    cp "$ZIP_SCHEMA" "$DROP_DIR/$DROP_SCHEMA"
    cp "$ZIP_DATA"   "$DROP_DIR/$DROP_DATA"
    step "2Packs abgelegt: $DROP_DIR/$DROP_SCHEMA + $DROP_DATA"
    echo "         Server (neu)starten — Auto-PackIn läuft beim Start."
    echo "         Log-Marker: grep 'installed\$' \$IDEMPIERE_HOME/log/idempiere.*.log"
fi

# ── 3. JRXML-Reports nach $IDEMPIERE_HOME/reports/ ────────────────────────
step "Kopiere JRXML-Reports nach $IDEMPIERE_HOME/reports/"
mkdir -p "$IDEMPIERE_HOME/reports"
# -n = no-clobber: vorhandene Reports werden nicht überschrieben.
cp -n "$REPO_ROOT/reports/"*.jrxml "$IDEMPIERE_HOME/reports/" 2>/dev/null || true

# ── 4. Optional: DE-Report-Suffix aktivieren ─────────────────────────────
if [ "$WITH_DE" -eq 1 ]; then
    step "Aktiviere deutsche Report-Variante via install_de_reports.sql"
    PGPASSWORD="${PGPASSWORD:-}" \
        psql -h "${PGHOST:-localhost}" -p "${PGPORT:-5432}" \
             -U "${PGUSER:-adempiere}" -d "${PGDATABASE:-idempiere}" \
             -f "$REPO_ROOT/setup/install_de_reports.sql"
fi

# ── 5. Smoke-Test ─────────────────────────────────────────────────────────
if [ -x "$REPO_ROOT/scripts/test/01_2pack_imports.sh" ]; then
    if [ "$STANDALONE" -eq 1 ]; then
        step "Smoke-Test"
        bash "$REPO_ROOT/scripts/test/01_2pack_imports.sh"
    else
        echo "[install] Smoke-Test nach Server-Restart manuell laufen lassen:"
        echo "          bash scripts/test/01_2pack_imports.sh"
    fi
fi

echo "[install] fertig."
