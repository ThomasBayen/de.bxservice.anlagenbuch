#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Erzeugt `anlagenbuch_init.ods` aus den Bayen-Master-CSVs unter `data/`.

Single-Source-of-Truth:
  * data/classes.csv    — Bayen-Anlagenklassen
  * data/assets.csv     — konkrete Bayen-Anlagen
  * data/schedules.csv  — Wartungstermin-Typen

Demo-Fehlerberichte (aus Steppert-Gespräch 8.5.26) bleiben hardcodiert in
diesem Skript, weil sie operative Test-Szenarien sind, keine reinen Init-
Stammdaten.

Importieren via:
  python3 ../../tools/import-ods.py --profile <bayen-profil> anlagenbuch_init.ods
"""
from __future__ import annotations

import csv
from pathlib import Path

from odf.opendocument import OpenDocumentSpreadsheet
from odf.table import Table, TableCell, TableColumn, TableRow
from odf.text import P


HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"
OUT = HERE / "anlagenbuch_init.ods"


# ── Demo-Fehlerberichte (Steppert-Gespräch 2026-05-08) ────────────────────

REPORTED_DATE = "2026-05-08"
REPORTER_NOTE = " (laut Herrn Steppert)"
# Melder aller Demo-Einträge. Muss in AD_User existieren mit IsEmployee='Y'
# (sonst greift Reference 286 "AD_User - Internal" nicht).
REPORTER_NAME = "Michael Steppert"

_RESOURCE_ALIASES: dict[str, str] = {
    "1359":  "KR JB-1359",
    "1005":  "KR JB-1005",
    "160":   "KR JB-160",
    "567":   "KR JB-567",
    "J-98E": "KR-J 98E",
}

ITEMS: list[tuple[str, str, str, str]] = [
    ("1359",  "Status", "Getriebe undicht",
     "Sollte nur vorsichtig gefahren werden. Kann irgendwann spontan stehen"
     "bleiben. Chef sollte nochmal mit der Werkstatt reden." + REPORTER_NOTE),
    ("1005",  "Defect", "Seil gerissen",
     "Rechte Klappe darf nicht mehr geöffnet werden, fällt womöglich raus. "
     "Muss bei Etz Bierewirtz gemacht werden — kann Doc Brummi nicht." + REPORTER_NOTE),
    ("160",   "Defect", "Fahrerseite Schloss defekt",
     "Tür muss am Fensterrahmen nachgezogen werden, um sie zu öffnen oder zu "
     "schließen. Türschloss wahrscheinlich ausgeschlagen oder Tür verzogen." + REPORTER_NOTE),
    ("567",   "Defect", "Ölstandsensor",
     "Ölstandsensor kaputt oder vielleicht starker Ölverlust. Ölwechsel und "
     "Reinigung oder Austausch des Sensors nötig." + REPORTER_NOTE),
    ("567",   "Defect", "Digitaler Tacho",
     "Gerät schmeißt oft die Karte raus, auch unterwegs. Bisher nur Meldung "
     "von Herrn Steppert. Könnte das auch an der Karte liegen?"),
    ("J-98E", "Defect", "fährt nicht",
     "Fahrzeug blieb während der Fahrt stehen und springt nicht mehr an. "
     "Steht seit 28.3.26 bei Dittmar & Stachowiak GmbH zur Reparatur "
     "(Elsa-Brändström-Str. 23-27, 44795 Bochum, +49 234 5798990)."),
]

ASSET_STATUS_OVERRIDES = {
    "KR-J 98E": "OutOfService",
}


def items_for_asset(asset_value: str) -> list[tuple[str, str, str]]:
    return [(t, n, d) for alias, t, n, d in ITEMS
            if _RESOURCE_ALIASES.get(alias) == asset_value]


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


ASSET_HEADER = [
    "Value/K", "Name",
    "BXS_AssetClass_ID[Value]",
    "Manufacturer", "Model",
    "AssetStatus",
    "Location",
    "Description",
    "BXS_AssetItem>Type/K",
    "BXS_AssetItem>Name/K",
    "BXS_AssetItem>Description",
    "BXS_AssetItem>ReportedDate",
    "BXS_AssetItem>ItemStatus",
    "BXS_AssetItem>AD_User_ID[Name]",
]
_EMPTY_MASTER = ["", "", "", "", "", "", "", ""]


def build_asset_sheet(anlagen: list[dict[str, str]]) -> list[list[str]]:
    rows: list[list[str]] = [ASSET_HEADER]
    for a in anlagen:
        value = a["Value"]
        name = a["Name"]
        klasse = a["KlassenValue"]
        manuf = a.get("Hersteller", "") or ""
        modl = a.get("Modell", "") or ""
        location = a.get("Standort", "") or ""
        desc = a.get("Anmerkung", "") or ""
        status = ASSET_STATUS_OVERRIDES.get(value, "InService")
        items = items_for_asset(value)

        if items:
            t, iname, idesc = items[0]
            rows.append([value, name, klasse, manuf, modl, status, location, desc,
                         t, iname, idesc, REPORTED_DATE, "Open", REPORTER_NAME])
            for t, iname, idesc in items[1:]:
                rows.append(_EMPTY_MASTER + [t, iname, idesc, REPORTED_DATE,
                                             "Open", REPORTER_NAME])
        else:
            rows.append([value, name, klasse, manuf, modl, status, location, desc,
                         "", "", "", "", "", ""])
    return rows


# ── Hauptlauf ─────────────────────────────────────────────────────────────


def main() -> None:
    klassen = load_csv("classes.csv")
    anlagen = load_csv("assets.csv")
    termine = load_csv("schedules.csv")

    print(f"Geladen aus {DATA_DIR}:")
    print(f"  {len(klassen)} Klassen, {len(anlagen)} Anlagen, "
          f"{len(termine)} Wartungstermin-Typen")

    config = [
        ["Sheet",        "Window",            "Tab",               "ImportMode", "Skip"],
        ["AssetClass",   "BXS Asset Class",   "BXS Asset Class",   "M",          ""],
        ["ScheduleType", "BXS Schedule Type", "BXS Schedule Type", "M",          ""],
        ["Asset",        "BXS Asset",         "Asset",             "M",          ""],
    ]

    sheets = [
        ("_config",      config),
        ("AssetClass",   build_assetclass_sheet(klassen)),
        ("ScheduleType", build_scheduletype_sheet(termine)),
        ("Asset",        build_asset_sheet(anlagen)),
    ]

    doc = OpenDocumentSpreadsheet()
    for sheet_name, rows in sheets:
        doc.spreadsheet.addElement(make_sheet(sheet_name, rows))
    doc.save(str(OUT))

    asset_rows = build_asset_sheet(anlagen)
    n_assets = sum(1 for r in asset_rows[1:] if r[0])
    n_items = sum(1 for r in asset_rows[1:] if r[8])
    print(f"Geschrieben: {OUT}")
    print(f"  {n_assets} Anlagen, {n_items} Fehlerberichte/Status")


if __name__ == "__main__":
    main()
