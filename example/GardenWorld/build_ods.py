#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Erzeugt `anlagenbuch_demo.ods` für den ODS-Multi-Sheet-Importer aus
den GardenWorld-Demo-CSVs unter `data/`.

Single-Source-of-Truth:
  * data/classes.csv     — Anlagenklassen (GardenWorld-Universum)
  * data/assets.csv      — konkrete Anlagen
  * data/schedules.csv   — Wartungstermin-Typen
  * data/items.csv       — Demo-Einträge (Defects, Schedules, Status)

Importieren via:
  python3 ../../tools/import-ods.py --profile gardenadmin anlagenbuch_demo.ods
"""
from __future__ import annotations

import csv
from pathlib import Path

from odf.opendocument import OpenDocumentSpreadsheet
from odf.table import Table, TableCell, TableColumn, TableRow
from odf.text import P


HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"
OUT = HERE / "anlagenbuch_demo.ods"


# ── CSV laden ──────────────────────────────────────────────────────────────


def load_csv(name: str) -> list[dict[str, str]]:
    """Lädt eine CSV (Semikolon-getrennt, UTF-8)."""
    with (DATA_DIR / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


# ── ODS-Hilfsroutinen ──────────────────────────────────────────────────────


def make_sheet(name: str, rows: list[list[str]]) -> Table:
    t = Table(name=name)
    if rows:
        TableColumn(numbercolumnsrepeated=str(len(rows[0])), parent=t)
    for r in rows:
        tr = TableRow()
        for v in r:
            c = TableCell(valuetype="string")
            c.addElement(P(text=str(v)))
            tr.addElement(c)
        t.addElement(tr)
    return t


# ── Sheet-Aufbau ──────────────────────────────────────────────────────────


def build_assetclass_sheet(klassen: list[dict[str, str]]) -> list[list[str]]:
    header = ["Value/K", "Name", "Category", "Description"]
    rows = [header]
    for k in klassen:
        rows.append([k["Value"], k["Name"], k["Kategorie"], k.get("Description", "")])
    return rows


def build_scheduletype_sheet(termine: list[dict[str, str]]) -> list[list[str]]:
    header = ["Value/K", "Name", "BXS_AssetClass_ID[Value]",
              "DefaultIntervalMonths", "IsMandatoryDefault", "Description"]
    rows = [header]
    for t in termine:
        rows.append([
            t["Value"], t["Name"], t.get("KlassenValue", "") or "",
            t["IntervallMonate"], t["PflichtDefault"], t.get("Description", ""),
        ])
    return rows


# Asset-Sheet mit Subtab-Detail-Spalten: erste Zeile pro Anlage = Master +
# ggf. erstes Item, Folgezeilen = leerer Master + weitere Items.
ASSET_HEADER = [
    "Value/K", "Name",
    "BXS_AssetClass_ID[Value]",
    "Manufacturer", "Model", "SerialNo",
    "AssetStatus",
    "Location",
    "Description",
    "BXS_AssetItem>Type/K",
    "BXS_AssetItem>Name/K",
    "BXS_AssetItem>Description",
    "BXS_AssetItem>Priority",
    "BXS_AssetItem>ReportedDate",
    "BXS_AssetItem>DueDate",
    "BXS_AssetItem>CompletionDate",
    "BXS_AssetItem>ItemStatus",
    "BXS_AssetItem>BXS_ScheduleType_ID[Value]",
    "BXS_AssetItem>MeterReading",
    "BXS_AssetItem>AD_User_ID[Name]",
]
_MASTER_COLS = 9
_EMPTY_MASTER = [""] * _MASTER_COLS


def _item_cols(item: dict[str, str]) -> list[str]:
    return [
        item.get("Type", ""),
        item.get("Name", ""),
        item.get("Description", ""),
        item.get("Priority", ""),
        item.get("ReportedDate", ""),
        item.get("DueDate", ""),
        item.get("CompletionDate", ""),
        item.get("ItemStatus", ""),
        item.get("ScheduleTypeValue", ""),
        item.get("MeterReading", ""),
        item.get("Reporter", "") or "GardenAdmin",
    ]


def build_asset_sheet(anlagen: list[dict[str, str]],
                       items: list[dict[str, str]]) -> list[list[str]]:
    by_asset: dict[str, list[dict[str, str]]] = {}
    for it in items:
        by_asset.setdefault(it["AssetValue"], []).append(it)

    rows: list[list[str]] = [ASSET_HEADER]
    for a in anlagen:
        value = a["Value"]
        master = [
            value, a["Name"], a["KlassenValue"],
            a.get("Hersteller", "") or "",
            a.get("Modell", "") or "",
            a.get("SerialNo", "") or "",
            a.get("AssetStatus", "") or "InService",
            a.get("Standort", "") or "",
            a.get("Anmerkung", "") or "",
        ]
        asset_items = by_asset.get(value, [])
        if not asset_items:
            rows.append(master + [""] * (len(ASSET_HEADER) - _MASTER_COLS))
            continue
        rows.append(master + _item_cols(asset_items[0]))
        for it in asset_items[1:]:
            rows.append(_EMPTY_MASTER + _item_cols(it))
    return rows


# ── Hauptlauf ─────────────────────────────────────────────────────────────


def main() -> None:
    klassen = load_csv("classes.csv")
    anlagen = load_csv("assets.csv")
    termine = load_csv("schedules.csv")
    items = load_csv("items.csv")

    print(f"Geladen aus {DATA_DIR}:")
    print(f"  {len(klassen)} Klassen, {len(anlagen)} Anlagen, "
          f"{len(termine)} Wartungstermin-Typen, {len(items)} Demo-Einträge")

    # Reihenfolge wichtig: AssetClass + ScheduleType vor Asset (FK-Targets).
    config = [
        ["Sheet",        "Window",            "Tab",               "ImportMode", "Skip"],
        ["AssetClass",   "BXS Asset Class",   "BXS Asset Class",   "M",          ""],
        ["ScheduleType", "BXS Schedule Type", "BXS Schedule Type", "M",          ""],
        ["Asset",        "BXS Asset",         "Asset",             "M",          ""],
    ]

    asset_rows = build_asset_sheet(anlagen, items)

    sheets = [
        ("_config",      config),
        ("AssetClass",   build_assetclass_sheet(klassen)),
        ("ScheduleType", build_scheduletype_sheet(termine)),
        ("Asset",        asset_rows),
    ]

    doc = OpenDocumentSpreadsheet()
    for name, rows in sheets:
        doc.spreadsheet.addElement(make_sheet(name, rows))
    doc.save(str(OUT))

    n_assets = sum(1 for r in asset_rows[1:] if r[0])
    n_items = sum(1 for r in asset_rows[1:] if r[_MASTER_COLS])
    print(f"Geschrieben: {OUT}")
    print(f"  {n_assets} Anlagen, {n_items} Einträge")


if __name__ == "__main__":
    main()
