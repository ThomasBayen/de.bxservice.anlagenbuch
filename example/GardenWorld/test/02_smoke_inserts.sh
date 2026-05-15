#!/bin/bash
# Verifiziert, dass der ODS-Import den GardenWorld-Demobestand
# in den Mandanten 11 geschrieben hat. Schlanker Schema-Check —
# nur „> 0 Records" pro Tabelle, keine exakten Zählerstände
# (die ODS-Inhalte ändern sich häufiger als der Test sich anpassen
# soll).

set -euo pipefail

PSQL="psql -h ${DBHOST:-localhost} -p ${DBPORT:-5432} -U ${DBUSER:-adempiere} -d ${DBNAME:-idempiere} -tAc"
export PGPASSWORD="${PGPASSWORD:-adempiere}"

GW_CLIENT_ID="${GARDENWORLD_CLIENT_ID:-11}"

errors=0
check_gt0() {
    local label="$1"; local sql="$2"
    actual=$($PSQL "$sql" | tr -d '[:space:]')
    if [[ "${actual:-0}" -gt 0 ]]; then
        echo "  ✓ $label = $actual"
    else
        echo "  ✗ $label: erwartet > 0, gefunden ${actual:-0}"
        errors=$((errors+1))
    fi
}

echo "GardenWorld-Demo (Client $GW_CLIENT_ID) — Smoke-Test:"
check_gt0 "AssetClass-Records"     "SELECT count(*) FROM bxs_assetclass  WHERE ad_client_id=$GW_CLIENT_ID"
check_gt0 "ScheduleType-Records"   "SELECT count(*) FROM bxs_scheduletype WHERE ad_client_id=$GW_CLIENT_ID"
check_gt0 "Asset-Records"          "SELECT count(*) FROM bxs_asset       WHERE ad_client_id=$GW_CLIENT_ID"
check_gt0 "AssetItem-Records"      "SELECT count(*) FROM bxs_assetitem   WHERE ad_client_id=$GW_CLIENT_ID"
check_gt0 "AssetCategory-Listenwerte" \
    "SELECT count(*) FROM ad_ref_list rl JOIN ad_reference r ON r.ad_reference_id=rl.ad_reference_id WHERE r.name='BXS Asset Category'"

if [[ $errors -gt 0 ]]; then
    echo "$errors Fehler"
    exit 1
fi
echo "GardenWorld-Demo-Datenbestand vorhanden."
