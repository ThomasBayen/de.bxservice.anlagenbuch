#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Baut 2pack/source/ + scripts/*.bsh + reports/*.jrxml zu DREI ZIPs:
#   2pack/Anlagenbuch_01_schema.zip — alle AD-Records (Tabellen, Spalten,
#                                     Fenster, Prozesse, Rules, PrintFormats)
#   2pack/Anlagenbuch_02_data.zip   — nur initial_data
#   2pack/Anlagenbuch_03_role.zip   — System-Master-Rolle „anlagenbuch"
#                                     (AD_Client_ID=0, IsMasterRole=Y) plus
#                                     Window-/Process-/Form-Access auf alle
#                                     vom Pack ausgelieferten Records.
#
# Drei Pakete, weil iDempiere-PIPO im selben Lauf eine frisch angelegte
# Custom-Tabelle nicht zuverlässig mit Initial-Daten füllen kann
# (PO.checkRecordIDCrossTenant sieht die noch uncommitteten AD_Column-
# Zeilen nicht und liefert leere keyColumns → ArrayIndexOutOfBounds).
# Lösung: Schema-ZIP committed, Daten-ZIP läuft danach gegen die nun
# committeten Tabellen, Rolle-ZIP läuft zuletzt gegen die committeten
# AD_Window/AD_Process-Records. RUN_ApplyPackInFromFolder.sh appliziert
# ZIPs in alphabetischer Reihenfolge — die Präfixe `_01_` / `_02_` /
# `_03_` ordnen das.
#
# Layout je ZIP (iDempiere-2Pack-Konvention):
#   de.bxservice.anlagenbuch.<part>/dict/PackOut.xml
#   de.bxservice.anlagenbuch.<part>/doc/de.bxservice.anlagenbuch.<part>Doc.xml

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$REPO_ROOT/2pack/.build"

rm -rf "$BUILD_DIR"

build_part() {
    local part="$1" suffix="$2"
    local pkg_name="de.bxservice.anlagenbuch.${part}"
    local out_zip="$REPO_ROOT/2pack/Anlagenbuch_${suffix}.zip"
    local pkg_dir="$BUILD_DIR/$pkg_name"

    mkdir -p "$pkg_dir/dict" "$pkg_dir/doc"

    python3 "$REPO_ROOT/2pack/source/assemble.py" \
        --source  "$REPO_ROOT/2pack/source" \
        --scripts "$REPO_ROOT/scripts" \
        --reports "$REPO_ROOT/reports" \
        --part    "$part" \
        --out     "$pkg_dir/dict/PackOut.xml"

    # Pro Teil eigener PackageDoc — sichert eindeutige AD_Package_Imp-Zeilen
    # und ein lesbares Description-Feld in der iDempiere-Verwaltung.
    sed -e "s|<packagename>.*</packagename>|<packagename>${pkg_name}</packagename>|" \
        -e "s|<description>\\(.*\\)</description>|<description>\\1 — Part: ${part}</description>|" \
        "$REPO_ROOT/2pack/source/PackageDoc.xml" \
        > "$pkg_dir/doc/${pkg_name}Doc.xml"

    rm -f "$out_zip"
    (cd "$BUILD_DIR" && zip -qr "$out_zip" "$pkg_name")
    echo "Built: $out_zip"
}

build_part schema 01_schema
build_part data   02_data
build_part role   03_role
