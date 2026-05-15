#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Räumt alle Anlagenbuch-Demodaten aus GardenWorld auf, ohne die
# AD-Records (Tabellen, Spalten, Fenster) anzufassen. Idempotent.
#
# Reihenfolge wichtig: erst FK-Children, dann Parents.

set -euo pipefail

DBHOST="${DBHOST:-localhost}"
DBPORT="${DBPORT:-5432}"
DBNAME="${DBNAME:-idempiere}"
DBUSER="${DBUSER:-adempiere}"
PGPASSWORD="${PGPASSWORD:-adempiere}"
export PGPASSWORD

GARDENWORLD_CLIENT_ID="${GARDENWORLD_CLIENT_ID:-11}"

psql -h "$DBHOST" -p "$DBPORT" -U "$DBUSER" -d "$DBNAME" <<SQL
BEGIN;
DELETE FROM BXS_WorkOrder_Item wi
USING BXS_WorkOrder w
WHERE wi.BXS_WorkOrder_ID = w.BXS_WorkOrder_ID
  AND w.AD_Client_ID = $GARDENWORLD_CLIENT_ID;

DELETE FROM BXS_WorkOrder
WHERE AD_Client_ID = $GARDENWORLD_CLIENT_ID;

DELETE FROM BXS_AssetItem
WHERE AD_Client_ID = $GARDENWORLD_CLIENT_ID;

DELETE FROM BXS_Asset
WHERE AD_Client_ID = $GARDENWORLD_CLIENT_ID;
COMMIT;
SQL

echo "Anlagenbuch-Demodaten in GardenWorld (Client $GARDENWORLD_CLIENT_ID) entfernt."
