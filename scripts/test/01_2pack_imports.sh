#!/bin/bash
# Akzeptanzkriterium: 2Pack importiert sauber, alle vier Fenster sind angelegt.
#
# Connection: das Skript sourct setup/config.env, falls vorhanden, damit der
# Test automatisch gegen dieselbe DB läuft wie install.sh. Ohne Config fällt
# es auf Vanilla-Defaults zurück (localhost:5432/idempiere) — in dem Fall
# typischerweise Fehlalarme, weil der Vanilla-Core einen anderen Plugin-Stand
# enthält. Wer gegen eine dritte DB testen will, kann PGHOST/PGPORT/PGUSER/
# PGPASSWORD/PGDATABASE vor dem Skript-Aufruf setzen — Env-Vars schlagen
# config.env.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CONFIG_ENV="$REPO_ROOT/setup/config.env"
if [ -f "$CONFIG_ENV" ]; then
    # Nur unbekannte Variablen aus der Datei ziehen — Aufrufer-Env hat Vorrang.
    set -a
    # shellcheck disable=SC1090
    while IFS='=' read -r k v; do
        [ -z "$k" ] && continue
        case "$k" in \#*) continue ;; esac
        if [ -z "${!k:-}" ]; then
            eval "$k=$v"
        fi
    done < <(grep -E '^(PG|DB)[A-Z]+=' "$CONFIG_ENV" || true)
    set +a
fi

DB_HOST="${PGHOST:-${DBHOST:-localhost}}"
DB_PORT="${PGPORT:-5432}"
DB_USER="${PGUSER:-${DBUSER:-adempiere}}"
DB_NAME="${PGDATABASE:-${DBNAME:-idempiere}}"
PSQL="psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -tAc"
export PGPASSWORD="${PGPASSWORD:-adempiere}"

echo "Smoke-Test gegen $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
echo

errors=0

check() {
    local label="$1"; local expected="$2"; local sql="$3"
    actual=$($PSQL "$sql" | tr -d '[:space:]')
    if [[ "$actual" == "$expected" ]]; then
        echo "  ✓ $label = $actual"
    else
        echo "  ✗ $label: erwartet $expected, gefunden $actual"
        errors=$((errors+1))
    fi
}

# Filter auf die exakte Anlagenbuch-Tabellen-Liste, weil im Bayen-Mandanten
# weitere bxservice-Plugins eigene BXS_*-Tabellen mitbringen (BXS_EDI*,
# BXS_DocValidation*, BXS_Georeferencing*). Tenant-Neutralität verlangt
# einen exakten Match auf die sechs vom Anlagenbuch gelieferten Tabellen.
ANLB_TABLES="'BXS_AssetClass','BXS_ScheduleType','BXS_Asset','BXS_AssetItem','BXS_WorkOrder','BXS_WorkOrder_Item'"

echo "Test 1 — 2Pack-Import vollständig:"
check "BXS-Tabellen"       6 "SELECT count(*) FROM ad_table WHERE tablename IN ($ANLB_TABLES)"
check "BXS-Fenster"        4 "SELECT count(*) FROM ad_window WHERE name LIKE 'BXS%'"
# Sieben Reference-Lists: Asset Category, Asset Class, Asset Status,
# Item Status, Item Type, Priority, Work Order Status.
check "BXS-Listen"         7 "SELECT count(*) FROM ad_reference WHERE name LIKE 'BXS%'"
# Asset-Window hat 5 Tabs: Asset + Defect + Schedule + Status + WorkOrders.
check "Asset-Window-Tabs"  5 "SELECT count(*) FROM ad_tab tb JOIN ad_window w ON w.ad_window_id=tb.ad_window_id WHERE w.name='BXS Asset'"
check "WorkOrder-Tabs"     3 "SELECT count(*) FROM ad_tab tb JOIN ad_window w ON w.ad_window_id=tb.ad_window_id WHERE w.name='BXS Work Order'"
check "DocumentNo-Sequenzen" 4 "SELECT count(*) FROM ad_sequence WHERE name LIKE 'BXS_AssetItem_%' OR name='BXS_WorkOrder_DocumentNo'"
# Sechs Community-Standardklassen (Vehicle/Equipment/Stationary/IT/Building/Other).
# AD_Client_ID=0-Filter, weil tenant-eigene Klassen (z.B. via ODS-Import in
# example/JakobBayenKG/) ebenfalls in der Tabelle landen — der Smoke-Test
# verifiziert hier nur den 2Pack-Stand, nicht den Tenant-Inhalt.
check "AssetClass-Initial" 6 "SELECT count(*) FROM bxs_assetclass WHERE ad_client_id=0"
# ScheduleType liefert KEINE Initial-Daten (siehe 30-scheduletype.yaml) —
# Termin-Typen sind tenant-spezifisch (z.B. Bayen: TÜV/SP/UVV).
check "ScheduleType-Initial" 0 "SELECT count(*) FROM bxs_scheduletype WHERE ad_client_id=0"
check "DE-Trls für Listen" 7 "SELECT count(*) FROM ad_reference_trl t JOIN ad_reference r ON r.ad_reference_id=t.ad_reference_id WHERE r.name LIKE 'BXS%' AND t.ad_language='de_DE'"

if [[ $errors -gt 0 ]]; then
    echo "$errors Fehler"
    exit 1
fi
echo "Alle Schemen-Checks grün."
