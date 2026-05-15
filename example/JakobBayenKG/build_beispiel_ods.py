#!/usr/bin/env python3
"""Erzeugt import/Beispiel_GardenWorld.ods aus generierten Beispiel-Daten.

Format kompatibel zum idempiere-ods-import (Multi-Sheet-ODS, _config-Sheet).
Importiert wird als GardenAdmin (CreatedBy=101), so dass die Datensätze
dem Mandanten gehören und in der UI änderbar sind.

Datenbestand (~realistisch für die Jakob Bayen KG):
- ~15 Anlagen (LKW, PKW, Stapler, Rolltore, Feuerlöscher, Kehrmaschinen, Sackkarren)
- ~5 Statusberichte (Erstaufnahmen)
- ~10 Wartungstermine (TÜV, SP, UVV, Garantie)
- ~8 Beanstandungen (Mix aus offen + erledigt)
- ~3 Werkstattaufträge (1 abgeschlossen, 1 laufend, 1 geplant)
- ~6 WorkOrder-Positionen
"""
from datetime import date, timedelta
from pathlib import Path

from odf.opendocument import OpenDocumentSpreadsheet
from odf.table import Table, TableCell, TableColumn, TableRow
from odf.text import P

OUT = Path(__file__).resolve().parent / "Beispiel_GardenWorld.ods"

TODAY = date(2026, 5, 10)


def d(days_offset: int) -> str:
    return (TODAY + timedelta(days=days_offset)).isoformat()


# --------------------------------------------------------------------------
# _config-Sheet — Reihenfolge wichtig: erst Anlagen, dann Items, dann
# WorkOrders+Items.

# Window-/Tab-Namen sind die deutschen Übersetzungen, weil REST-API und
# import-ods.py die Default-Sprache des Login-Users (GardenAdmin: de_DE)
# zurückliefern. Englische Default-Namen würden nur bei einem en_US-User
# matchen.
CONFIG = [
    ["Sheet",          "Window",            "Tab",            "ImportMode", "Skip"],
    ["BXS_Asset",      "Anlage",            "Anlage",         "I", ""],
    ["Status_Items",   "Anlage",            "Statusbericht",  "I", ""],
    ["Defect_Items",   "Anlage",            "Beanstandung",   "I", ""],
    ["Schedule_Items", "Anlage",            "Wartungstermin", "I", ""],
    ["WorkOrder",      "Werkstattauftrag",  "Werkstattauftrag", "I", ""],
    ["WorkOrder_Item", "Werkstattauftrag",  "Position",       "I", ""],
]

# --------------------------------------------------------------------------
# BXS_Asset — 15 Beispiel-Anlagen

ASSETS = [
    # LKW
    ["Value",       "Name",                          "BXS_AssetClass_ID[Value]", "Manufacturer",  "Model",       "SerialNo",          "YearBuilt", "CommissionDate", "Location",      "AssetStatus"],
    ["LKW-MB-2078",   "KR-JB 2078 Mercedes Atego 12t", "VEHICLE",                  "Mercedes-Benz", "Atego 1224",  "WDB97003110123456", "2020",      "2020-03-15",     "Hauptlager",    "InService"],
    ["LKW-MAN-2079",  "KR-JB 2079 MAN TGM 18t",        "VEHICLE",                  "MAN",           "TGM 18.290",  "WMAN18290700123",   "2018",      "2018-06-01",     "Hauptlager",    "InService"],
    ["LKW-IVE-2080",  "KR-JB 2080 Iveco Eurocargo",    "VEHICLE",                  "Iveco",         "Eurocargo",   "ZCFA1ED0102543210", "2019",      "2019-09-20",     "Hauptlager",    "InService"],
    ["LKW-MB-2081",   "KR-JB 2081 Mercedes Atego 7t",  "VEHICLE",                  "Mercedes-Benz", "Atego 818",   "WDB97002910654321", "2022",      "2022-04-04",     "Hauptlager",    "InService"],
    # PKW
    ["PKW-VW-1250",   "KR-JB 1250 VW Caddy",           "VEHICLE",                  "Volkswagen",    "Caddy",       "WVWZZZ2KZJX012345", "2021",      "2021-09-10",     "Verwaltung",    "InService"],
    ["PKW-OPL-1252",  "KR-JB 1252 Opel Astra",         "VEHICLE",                  "Opel",          "Astra K",     "W0LBD8ED0H1234567", "2017",      "2017-05-12",     "Verwaltung",    "InService"],
    # Stapler
    ["STAPLER-LIN-1", "Stapler Linde H35D #1",         "FORKLIFT",                 "Linde",         "H35D",        "LIN-H35-2019-001",  "2019",      "2019-04-20",     "Halle 1",       "InService"],
    ["STAPLER-LIN-2", "Stapler Linde H25D #2",         "FORKLIFT",                 "Linde",         "H25D",        "LIN-H25-2021-002",  "2021",      "2021-08-05",     "Halle 2",       "InService"],
    # Rolltore
    ["ROLLTOR-H1-N",  "Rolltor Halle 1 Nord",          "EQUIPMENT",                "Hörmann",       "Industrial",  "RLT-H1N-2020",      "2020",      "2020-08-15",     "Halle 1 Nord",  "InService"],
    ["ROLLTOR-H1-S",  "Rolltor Halle 1 Süd",           "EQUIPMENT",                "Hörmann",       "Industrial",  "RLT-H1S-2020",      "2020",      "2020-08-15",     "Halle 1 Süd",   "InService"],
    ["ROLLTOR-H2",    "Rolltor Halle 2",               "EQUIPMENT",                "Hörmann",       "Industrial",  "RLT-H2-2018",       "2018",      "2018-04-20",     "Halle 2",       "InService"],
    # Feuerlöscher
    ["FLG-EXT-101",   "Feuerlöscher 6kg ABC #101",     "EQUIPMENT",                "Gloria",        "P6G",         "GLO-2023-101",      "2023",      "2023-01-10",     "Halle 1",       "InService"],
    ["FLG-EXT-102",   "Feuerlöscher 6kg ABC #102",     "EQUIPMENT",                "Gloria",        "P6G",         "GLO-2023-102",      "2023",      "2023-01-10",     "Halle 2",       "InService"],
    ["FLG-EXT-201",   "Feuerlöscher 12kg #201",        "EQUIPMENT",                "Total",         "TG12",        "TOT-2022-201",      "2022",      "2022-06-01",     "Verwaltung",    "InService"],
    # Kehrmaschinen
    ["KEHR-1",        "Kehrmaschine Hako Citymaster",  "EQUIPMENT",                "Hako",          "Citymaster 1600", "HAK-CM-2022-1",  "2022",      "2022-04-01",     "Hauptlager",    "InService"],
    # Sackkarren
    ["SACK-12",       "Sackkarre Stahl 250kg #12",     "EQUIPMENT",                "Wagner",        "Stahl 250 kg","",                  "",          "",               "Halle 1",       "InService"],
    ["SACK-13",       "Sackkarre Stahl 250kg #13",     "EQUIPMENT",                "Wagner",        "Stahl 250 kg","",                  "",          "",               "Halle 2",       "InService"],
]

# --------------------------------------------------------------------------
# Status-Items (Type=Status, direkt Done)
# Erstaufnahmen für die wichtigsten Anlagen

STATUS_ITEMS = [
    ["DocumentNo",   "BXS_Asset_ID[Value]", "Type",   "Name",                       "Description",                                            "ReportedDate", "ItemStatus", "MeterReading", "AD_User_ID[Name]"],
    ["STA-2026-00001", "LKW-MB-2078",         "Status", "Erstaufnahme",               "Fahrzeug übergeben, sichtbar in Ordnung, km-Stand",       "2024-01-15",   "Done",       "324850",       "GardenAdmin"],
    ["STA-2026-00002", "LKW-MAN-2079",        "Status", "Erstaufnahme",               "Fahrzeug übergeben, kleinere Lackschäden Heckklappe",     "2024-02-20",   "Done",       "412300",       "GardenAdmin"],
    ["STA-2026-00003", "STAPLER-LIN-1",       "Status", "Erstaufnahme",               "Stapler übergeben, Bh-Stand notiert",                     "2024-03-10",   "Done",       "8420",         "GardenAdmin"],
    ["STA-2026-00004", "ROLLTOR-H1-N",        "Status", "Sichtprüfung Q1/2026",       "Funktionscheck — alles ok, leichte Geräusche beim Heben","2026-03-30",   "Done",       "",             "Carl Boss"],
    ["STA-2026-00005", "FLG-EXT-101",         "Status", "Sichtkontrolle Q1/2026",     "Plombe intakt, Druckanzeige im grünen Bereich",           "2026-03-30",   "Done",       "",             "Carl Boss"],
]

# --------------------------------------------------------------------------
# Defect-Items (Type=Defect, Mix aus Open + Done)

DEFECT_ITEMS = [
    ["DocumentNo",   "BXS_Asset_ID[Value]", "Type",   "Name",                              "Description",                                                              "ReportedDate", "ItemStatus", "Priority", "MeterReading", "EstimatedCost", "AD_User_ID[Name]"],
    ["BEA-2026-00001", "LKW-MB-2078",         "Defect", "Ladeklappe schließt nicht sauber",  "Klappe verkantet beim Schließen, lässt sich nur mit Gewalt verriegeln",    "2026-04-15",   "Open",       "High",     "338500",       "450",            "Joe Sales"],
    ["BEA-2026-00002", "LKW-MB-2078",         "Defect", "Reifen vorne links abgefahren",     "Profil unter 4mm, im nächsten Werkstattbesuch wechseln",                   "2026-04-20",   "Open",       "Medium",   "338500",       "180",            "Joe Sales"],
    ["BEA-2026-00003", "LKW-MAN-2079",        "Defect", "Klimaanlage kühlt nicht",           "Vermutlich Kältemittel verloren, kurzes Pfeifen beim Einschalten",         "2026-04-22",   "Open",       "Medium",   "428100",       "320",            "Joe Sales"],
    ["BEA-2026-00004", "PKW-VW-1250",         "Defect", "Anhängerkupplung-Stecker locker",   "7-Pin-Stecker hat Wackelkontakt, Blinker hinten fällt zeitweise aus",      "2026-04-28",   "Open",       "High",     "82400",        "85",             "Carl Boss"],
    ["BEA-2026-00005", "STAPLER-LIN-1",       "Defect", "Hubzylinder ölt",                   "Tropfen unter dem Stapler nach Standzeit, Hub-Performance noch unauffällig","2026-04-30",  "Open",       "Medium",   "9210",         "650",            "Henry Seed"],
    ["BEA-2026-00006", "ROLLTOR-H1-S",        "Defect", "Rolltor klemmt unten",              "Beim Schließen verkantet sich der Vorhang, manuelle Hilfe nötig",          "2026-05-05",   "Open",       "High",     "",             "280",            "Carl Boss"],
    ["BEA-2026-00007", "LKW-IVE-2080",        "Defect", "Scheibenwischer hinten defekt",     "Motor brummt aber Wischerarm bewegt sich nicht",                            "2026-03-12",   "Done",       "Low",      "298400",       "60",             "Joe Sales"],
    ["BEA-2026-00008", "KEHR-1",              "Defect", "Saugleistung nachgelassen",         "Seitenbürste dreht zu langsam, Filter verstopft?",                          "2026-04-10",   "Open",       "Low",      "",             "120",            "Carl Boss"],
]

# --------------------------------------------------------------------------
# Schedule-Items (Type=Schedule, alle Open mit DueDate in der Zukunft)

SCHEDULE_ITEMS = [
    ["DocumentNo",   "BXS_Asset_ID[Value]", "Type",     "Name",                "BXS_ScheduleType_ID[Value]", "DueDate",     "ReportedDate", "ItemStatus"],
    ["TER-2026-00001", "LKW-MB-2078",         "Schedule", "TÜV-Hauptuntersuchung", "TUV",                       "2026-09-01",  "2026-01-10",   "Open"],
    ["TER-2026-00002", "LKW-MB-2078",         "Schedule", "Sicherheitsprüfung",    "SP",                        "2026-09-01",  "2026-01-10",   "Open"],
    ["TER-2026-00003", "LKW-MAN-2079",        "Schedule", "TÜV-Hauptuntersuchung", "TUV",                       "2026-06-01",  "2025-12-10",   "Open"],
    ["TER-2026-00004", "LKW-MAN-2079",        "Schedule", "Sicherheitsprüfung",    "SP",                        "2026-06-01",  "2025-12-10",   "Open"],
    ["TER-2026-00005", "LKW-IVE-2080",        "Schedule", "TÜV-Hauptuntersuchung", "TUV",                       "2026-08-01",  "2026-02-15",   "Open"],
    ["TER-2026-00006", "LKW-MB-2081",         "Schedule", "TÜV-Hauptuntersuchung", "TUV",                       "2027-04-01",  "2026-04-10",   "Open"],
    ["TER-2026-00007", "PKW-VW-1250",         "Schedule", "TÜV-Hauptuntersuchung", "TUV",                       "2026-10-01",  "2026-04-15",   "Open"],
    ["TER-2026-00008", "STAPLER-LIN-1",       "Schedule", "UVV-Prüfung",           "UVV",                       "2026-07-01",  "2026-01-20",   "Open"],
    ["TER-2026-00009", "STAPLER-LIN-2",       "Schedule", "UVV-Prüfung",           "UVV",                       "2026-09-01",  "2026-03-05",   "Open"],
    ["TER-2026-00010", "FLG-EXT-101",         "Schedule", "Wartung Feuerlöscher",  "INSPECTION",                "2027-01-01",  "2026-01-05",   "Open"],
    ["TER-2026-00011", "FLG-EXT-102",         "Schedule", "Wartung Feuerlöscher",  "INSPECTION",                "2027-01-01",  "2026-01-05",   "Open"],
    ["TER-2026-00012", "PKW-OPL-1252",        "Schedule", "Garantie-Ablauf",       "WARRANTY",                  "2027-05-12",  "2026-05-01",   "Open"],
]

# --------------------------------------------------------------------------
# WorkOrder + WorkOrder_Item

WORKORDERS = [
    ["DocumentNo",   "BXS_Asset_ID[Value]", "Name",                            "Workshop_ID[Name]", "Driver_ID[Name]", "InternalContact_ID[Name]", "ScheduledDate", "ActualDate",  "CompletionDate", "EstimatedCost", "ActualCost", "ExternalDocumentNo", "WorkOrderStatus", "Description"],
    ["WAU-2026-00001", "LKW-IVE-2080",        "Wischer hinten + Sichtprüfung",   "Wood, Inc",         "Joe Sales",       "Carl Boss",                "2026-03-15",    "2026-03-15",  "2026-03-15",     "60",            "78",         "RG-2026-0034",       "Completed",       "Wischer hinten getauscht, Sicht-Check ohne Befund."],
    ["WAU-2026-00002", "LKW-MAN-2079",        "Klimaservice + TÜV-Vorbereitung", "Wood, Inc",         "Joe Sales",       "Carl Boss",                "2026-05-15",    "2026-05-15",  "",               "550",           "",           "",                   "Released",        "Geplant: Kältemittel + Bremsen-Vorcheck."],
    ["WAU-2026-00003", "LKW-MB-2078",         "Großwartung TÜV/SP + Klappe",     "Wood, Inc",         "Joe Sales",       "Carl Boss",                "2026-08-25",    "",            "",               "1100",          "",           "",                   "Draft",           "Disposition Sommer/Herbst."],
]

WORKORDER_ITEMS = [
    ["BXS_WorkOrder_ID[DocumentNo]", "BXS_AssetItem_ID[DocumentNo]", "IsResolved", "LineNo", "Note"],
    ["WAU-2026-00001",                 "BEA-2026-00007",                 "Y",          "10",     "Erledigt — Wischermotor war's."],
    ["WAU-2026-00003",                 "BEA-2026-00001",                 "Y",          "10",     "Klappe — komplett überholen."],
    ["WAU-2026-00003",                 "BEA-2026-00002",                 "Y",          "20",     "Reifen vorne, evtl. auch hinten prüfen."],
    ["WAU-2026-00003",                 "TER-2026-00001",                 "Y",          "30",     "TÜV-HU."],
    ["WAU-2026-00003",                 "TER-2026-00002",                 "Y",          "40",     "SP."],
    ["WAU-2026-00002",                 "BEA-2026-00003",                 "Y",          "10",     "Klima-Service."],
]


# --------------------------------------------------------------------------

def make_sheet(name: str, rows: list[list[str]]) -> Table:
    table = Table(name=name)
    if rows:
        TableColumn(numbercolumnsrepeated=str(len(rows[0])), parent=table)
    for row in rows:
        tr = TableRow()
        for value in row:
            tc = TableCell(valuetype="string")
            tc.addElement(P(text=str(value)))
            tr.addElement(tc)
        table.addElement(tr)
    return table


def main() -> None:
    doc = OpenDocumentSpreadsheet()
    for name, rows in [
        ("_config",        CONFIG),
        ("BXS_Asset",      ASSETS),
        ("Status_Items",   STATUS_ITEMS),
        ("Defect_Items",   DEFECT_ITEMS),
        ("Schedule_Items", SCHEDULE_ITEMS),
        ("WorkOrder",      WORKORDERS),
        ("WorkOrder_Item", WORKORDER_ITEMS),
    ]:
        doc.spreadsheet.addElement(make_sheet(name, rows))
    doc.save(str(OUT))
    print(f"Geschrieben: {OUT}")
    print(f"  Anlagen: {len(ASSETS)-1}")
    print(f"  Statusberichte: {len(STATUS_ITEMS)-1}")
    print(f"  Beanstandungen: {len(DEFECT_ITEMS)-1}")
    print(f"  Wartungstermine: {len(SCHEDULE_ITEMS)-1}")
    print(f"  Werkstattaufträge: {len(WORKORDERS)-1}")
    print(f"  Werkstatt-Positionen: {len(WORKORDER_ITEMS)-1}")


if __name__ == "__main__":
    main()
