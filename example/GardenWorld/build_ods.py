#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Erzeugt `anlagenbuch_demo.ods` für den ODS-Multi-Sheet-Importer aus
den GardenWorld-Demo-CSVs unter `data/`.

Single-Source-of-Truth:
  * data/bpartner_employee_fix.csv — Update für TBB008 (BPartner-Flags)
  * data/classes.csv               — Anlagenklassen (numerische Values)
  * data/schedules.csv             — Wartungstermin-Typen
  * data/assets.csv                — konkrete Anlagen
  * data/items.csv                 — Demo-Einträge (Defects, Schedules,
                                     Status). `Name` wird beim Bau mit
                                     `<AssetValue>: …` präfixt, damit
                                     er allein als Lookup-Key reicht
                                     (siehe WorkOrder-Item-Sheet).
  * data/workorders.csv            — Werkstattaufträge
  * data/workorder_items.csv       — WAU-Positionen (referenzieren
                                     AssetItem über den präfixierten
                                     Namen)

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


# ── Namens-Konvention für AssetItems ──────────────────────────────────────

def prefixed_item_name(asset_value: str, raw_name: str) -> str:
    """Macht den AssetItem-Namen ohne weiteren Kontext eindeutig. Das ist
    Voraussetzung dafür, dass das WorkOrder-Item-Sheet einen Eintrag
    über `BXS_AssetItem_ID[Name]` referenzieren kann."""
    return f"{asset_value}: {raw_name}"


# ── Sheet: BusinessPartner (TBB008-Workaround) ────────────────────────────


def build_bpartner_sheet(bps: list[dict[str, str]]) -> list[list[str]]:
    """Setzt `IsEmployee=Y` bei den drei BPartners, an deren AD_User unsere
    Demo-Einträge als Reporter referenzieren. Ohne diesen Schritt filtert
    Reference 286 („AD_User – Internal") sie aus der Auswahlliste — der
    `BXS_AssetItem>AD_User_ID[Name]`-Lookup im Asset-Sheet schlägt fehl.

    Siehe `idempiere-core/bugreports/TBB008-gardenworld-employees-missing-flags/`."""
    header = ["Value/K", "Name", "IsEmployee"]
    rows = [header]
    for bp in bps:
        rows.append([bp["Value"], bp["Name"], bp["IsEmployee"]])
    return rows


# ── Sheet: AssetClass ─────────────────────────────────────────────────────


def build_assetclass_sheet(klassen: list[dict[str, str]]) -> list[list[str]]:
    header = ["Value/K", "Name", "Category", "Description"]
    rows = [header]
    for k in klassen:
        rows.append([k["Value"], k["Name"], k["Kategorie"], k.get("Description", "")])
    return rows


# ── Sheet: ScheduleType ───────────────────────────────────────────────────


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


# ── Sheet: Asset (Master mit BXS_AssetItem als Detail-Tab) ────────────────

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


def _item_cols(asset_value: str, item: dict[str, str]) -> list[str]:
    return [
        item.get("Type", ""),
        prefixed_item_name(asset_value, item.get("Name", "")),
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
        rows.append(master + _item_cols(value, asset_items[0]))
        for it in asset_items[1:]:
            rows.append(_EMPTY_MASTER + _item_cols(value, it))
    return rows


# ── Sheet: WorkOrder (Master mit WorkOrder_Item als Detail-Tab) ──────────

WORKORDER_HEADER = [
    "DocumentNo/K", "Name",
    "BXS_Asset_ID[Value]",
    "Workshop_ID[Name]",
    "Driver_ID[Name]",
    "InternalContact_ID[Name]",
    "ScheduledDate",
    "ActualDate",
    "CompletionDate",
    "EstimatedCost",
    "ActualCost",
    "ExternalDocumentNo",
    "WorkOrderStatus",
    "Description",
    "Note",
    "BXS_WorkOrder_Item>LineNo/K",
    "BXS_WorkOrder_Item>BXS_AssetItem_ID[Name]",
    "BXS_WorkOrder_Item>IsResolved",
    "BXS_WorkOrder_Item>Note",
]
_WO_MASTER_COLS = 15
_WO_EMPTY_MASTER = [""] * _WO_MASTER_COLS


def _wo_item_cols(wi: dict[str, str]) -> list[str]:
    item_lookup = prefixed_item_name(wi["AssetValue"], wi["ItemName"])
    return [
        wi.get("LineNo", ""),
        item_lookup,
        wi.get("IsResolved", "Y"),
        wi.get("Note", ""),
    ]


def build_workorder_sheet(workorders: list[dict[str, str]],
                          wo_items: list[dict[str, str]]) -> list[list[str]]:
    by_wo: dict[str, list[dict[str, str]]] = {}
    for it in wo_items:
        by_wo.setdefault(it["WorkOrderValue"], []).append(it)

    rows: list[list[str]] = [WORKORDER_HEADER]
    for wo in workorders:
        docno = wo["Value"]  # CSV-Spalte heißt „Value", landet in DocumentNo
        master = [
            docno,
            wo["Name"],
            wo["AssetValue"],
            wo.get("WorkshopBPartner", "") or "",
            wo.get("DriverUser", "") or "",
            wo.get("InternalContactUser", "") or "",
            wo.get("ScheduledDate", "") or "",
            wo.get("ActualDate", "") or "",
            wo.get("CompletionDate", "") or "",
            wo.get("EstimatedCost", "") or "",
            wo.get("ActualCost", "") or "",
            wo.get("ExternalDocumentNo", "") or "",
            wo.get("WorkOrderStatus", "Draft"),
            wo.get("Description", "") or "",
            wo.get("Note", "") or "",
        ]
        wo_lines = by_wo.get(docno, [])
        if not wo_lines:
            rows.append(master + [""] * (len(WORKORDER_HEADER) - _WO_MASTER_COLS))
            continue
        rows.append(master + _wo_item_cols(wo_lines[0]))
        for line in wo_lines[1:]:
            rows.append(_WO_EMPTY_MASTER + _wo_item_cols(line))
    return rows


# ── Hauptlauf ─────────────────────────────────────────────────────────────


def main() -> None:
    bps = load_csv("bpartner_employee_fix.csv")
    klassen = load_csv("classes.csv")
    termine = load_csv("schedules.csv")
    anlagen = load_csv("assets.csv")
    items = load_csv("items.csv")
    workorders = load_csv("workorders.csv")
    wo_items = load_csv("workorder_items.csv")

    print(f"Geladen aus {DATA_DIR}:")
    print(f"  {len(bps)} BPartner-Fix, {len(klassen)} Klassen, "
          f"{len(termine)} Wartungstermin-Typen, {len(anlagen)} Anlagen, "
          f"{len(items)} Demo-Einträge, {len(workorders)} Werkstattaufträge "
          f"({len(wo_items)} Positionen)")

    # Reihenfolge:
    #   1. BusinessPartner   — TBB008-Workaround vor allem anderen
    #   2. AssetClass        — Tenant-Klassen-Stammdaten
    #   3. ScheduleType      — Wartungstermin-Typen
    #   4. Asset             — Anlagen + AssetItems (Subtab)
    #   5. WorkOrder         — Werkstattaufträge + Positionen (Subtab),
    #                          referenziert AssetItems aus Schritt 4 per
    #                          (prefixed) Name.
    config = [
        ["Sheet",           "Window",            "Tab",               "ImportMode", "Skip"],
        ["BusinessPartner", "Business Partner",  "Business Partner",  "U",          ""],
        ["AssetClass",      "BXS Asset Class",   "BXS Asset Class",   "M",          ""],
        ["ScheduleType",    "BXS Schedule Type", "BXS Schedule Type", "M",          ""],
        ["Asset",           "BXS Asset",         "Asset",             "M",          ""],
        ["WorkOrder",       "BXS Work Order",    "WorkOrder",         "M",          ""],
    ]

    asset_rows = build_asset_sheet(anlagen, items)
    wo_rows = build_workorder_sheet(workorders, wo_items)

    sheets = [
        ("_config",         config),
        ("BusinessPartner", build_bpartner_sheet(bps)),
        ("AssetClass",      build_assetclass_sheet(klassen)),
        ("ScheduleType",    build_scheduletype_sheet(termine)),
        ("Asset",           asset_rows),
        ("WorkOrder",       wo_rows),
    ]

    doc = OpenDocumentSpreadsheet()
    for name, rows in sheets:
        doc.spreadsheet.addElement(make_sheet(name, rows))
    doc.save(str(OUT))

    n_assets = sum(1 for r in asset_rows[1:] if r[0])
    n_items = sum(1 for r in asset_rows[1:] if r[_MASTER_COLS])
    n_wos = sum(1 for r in wo_rows[1:] if r[0])
    n_wo_lines = sum(1 for r in wo_rows[1:] if r[_WO_MASTER_COLS])
    print(f"Geschrieben: {OUT}")
    print(f"  {n_assets} Anlagen, {n_items} Einträge, "
          f"{n_wos} Werkstattaufträge, {n_wo_lines} Positionen")


if __name__ == "__main__":
    main()
