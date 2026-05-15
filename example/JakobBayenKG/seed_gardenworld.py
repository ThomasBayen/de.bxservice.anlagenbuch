#!/usr/bin/env python3
"""Spielt einen Beispiel-Datenbestand fürs Anlagenbuch in den
GardenWorld-Mandanten der lokalen iDempiere-DB.

Mandanten-Daten (CreatedBy = GardenAdmin = 101) — also vom
Endanwender bearbeitbar. Idempotent über UUIDs:
ON CONFLICT (<Tabelle>_UU) DO UPDATE.

Das parallele `build_beispiel_ods.py` hält die gleichen Daten als
ODS-Datei für den späteren Produktiv-Import via idempiere-ods-import.
Solange dort der "Value ist schreibgeschützt"-Workaround offen ist,
ist dieses Direkt-Skript die zuverlässige Quelle für Demo-Daten.

Aufruf: ./seed_gardenworld.py
"""
import os
import subprocess
import sys
import uuid

CLIENT = 11   # GardenWorld
ORG = 11      # HQ
USER = 101    # GardenAdmin
ID_OFFSET = 9_000_000   # User-Range, ausreichend Abstand zu System-IDs

# Stabile UUIDs (deterministisch hergeleitet) — damit ON CONFLICT zieht.
def uu(seed: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_OID, "anlagenbuch-demo:" + seed))


# --------------------------------------------------------------------------
# Beispieldaten — Anlagen, Einträge, Werkstattaufträge

ASSETS = [
    # (id_offset, value, name, class_value, manufacturer, model, serialno, year, commission_date, location, status)
    (1,  "LKW-MB-2078",   "KR-JB 2078 Mercedes Atego 12t", "VEHICLE",   "Mercedes-Benz", "Atego 1224",       "WDB97003110123456",  2020, "2020-03-15", "Hauptlager",   "InService"),
    (2,  "LKW-MAN-2079",  "KR-JB 2079 MAN TGM 18t",        "VEHICLE",   "MAN",           "TGM 18.290",       "WMAN18290700123",    2018, "2018-06-01", "Hauptlager",   "InService"),
    (3,  "LKW-IVE-2080",  "KR-JB 2080 Iveco Eurocargo",    "VEHICLE",   "Iveco",         "Eurocargo",        "ZCFA1ED0102543210",  2019, "2019-09-20", "Hauptlager",   "InService"),
    (4,  "LKW-MB-2081",   "KR-JB 2081 Mercedes Atego 7t",  "VEHICLE",   "Mercedes-Benz", "Atego 818",        "WDB97002910654321",  2022, "2022-04-04", "Hauptlager",   "InService"),
    (5,  "PKW-VW-1250",   "KR-JB 1250 VW Caddy",           "VEHICLE",   "Volkswagen",    "Caddy",            "WVWZZZ2KZJX012345",  2021, "2021-09-10", "Verwaltung",   "InService"),
    (6,  "PKW-OPL-1252",  "KR-JB 1252 Opel Astra",         "VEHICLE",   "Opel",          "Astra K",          "W0LBD8ED0H1234567",  2017, "2017-05-12", "Verwaltung",   "InService"),
    (7,  "STAPLER-LIN-1", "Stapler Linde H35D #1",         "FORKLIFT",  "Linde",         "H35D",             "LIN-H35-2019-001",   2019, "2019-04-20", "Halle 1",      "InService"),
    (8,  "STAPLER-LIN-2", "Stapler Linde H25D #2",         "FORKLIFT",  "Linde",         "H25D",             "LIN-H25-2021-002",   2021, "2021-08-05", "Halle 2",      "InService"),
    (9,  "ROLLTOR-H1-N",  "Rolltor Halle 1 Nord",          "EQUIPMENT", "Hörmann",       "Industrial",       "RLT-H1N-2020",       2020, "2020-08-15", "Halle 1 Nord", "InService"),
    (10, "ROLLTOR-H1-S",  "Rolltor Halle 1 Süd",           "EQUIPMENT", "Hörmann",       "Industrial",       "RLT-H1S-2020",       2020, "2020-08-15", "Halle 1 Süd",  "InService"),
    (11, "ROLLTOR-H2",    "Rolltor Halle 2",               "EQUIPMENT", "Hörmann",       "Industrial",       "RLT-H2-2018",        2018, "2018-04-20", "Halle 2",      "InService"),
    (12, "FLG-EXT-101",   "Feuerlöscher 6kg ABC #101",     "EQUIPMENT", "Gloria",        "P6G",              "GLO-2023-101",       2023, "2023-01-10", "Halle 1",      "InService"),
    (13, "FLG-EXT-102",   "Feuerlöscher 6kg ABC #102",     "EQUIPMENT", "Gloria",        "P6G",              "GLO-2023-102",       2023, "2023-01-10", "Halle 2",      "InService"),
    (14, "FLG-EXT-201",   "Feuerlöscher 12kg #201",        "EQUIPMENT", "Total",         "TG12",             "TOT-2022-201",       2022, "2022-06-01", "Verwaltung",   "InService"),
    (15, "KEHR-1",        "Kehrmaschine Hako Citymaster",  "EQUIPMENT", "Hako",          "Citymaster 1600",  "HAK-CM-2022-1",      2022, "2022-04-01", "Hauptlager",   "InService"),
    (16, "SACK-12",       "Sackkarre Stahl 250kg #12",     "EQUIPMENT", "Wagner",        "Stahl 250 kg",     None,                 None, None,         "Halle 1",      "InService"),
    (17, "SACK-13",       "Sackkarre Stahl 250kg #13",     "EQUIPMENT", "Wagner",        "Stahl 250 kg",     None,                 None, None,         "Halle 2",      "InService"),
]

# Status-Items (immer Done, ReportedDate=CompletionDate)
STATUS_ITEMS = [
    # (id_offset, docno, asset_value, name, description, reported_date, meter, user_name)
    (1, "STA-2026-00001", "LKW-MB-2078",  "Erstaufnahme",            "Fahrzeug übergeben, sichtbar in Ordnung, km-Stand notiert.", "2024-01-15", 324850, "GardenAdmin"),
    (2, "STA-2026-00002", "LKW-MAN-2079", "Erstaufnahme",            "Fahrzeug übergeben, kleinere Lackschäden Heckklappe.",       "2024-02-20", 412300, "GardenAdmin"),
    (3, "STA-2026-00003", "STAPLER-LIN-1","Erstaufnahme",            "Stapler übergeben, Bh-Stand notiert.",                       "2024-03-10",   8420, "GardenAdmin"),
    (4, "STA-2026-00004", "ROLLTOR-H1-N", "Sichtprüfung Q1/2026",    "Funktionscheck — alles ok, leichte Geräusche beim Heben.",   "2026-03-30",   None, "Carl Boss"),
    (5, "STA-2026-00005", "FLG-EXT-101",  "Sichtkontrolle Q1/2026",  "Plombe intakt, Druckanzeige im grünen Bereich.",             "2026-03-30",   None, "Carl Boss"),
]

# Defect-Items
DEFECT_ITEMS = [
    # (id_offset, docno, asset_value, name, description, reported_date, status, priority, meter, est_cost, user_name)
    (1, "BEA-2026-00001", "LKW-MB-2078",  "Ladeklappe schließt nicht sauber", "Klappe verkantet beim Schließen, lässt sich nur mit Gewalt verriegeln.",      "2026-04-15", "Open", "High",   338500,  450, "Joe Sales"),
    (2, "BEA-2026-00002", "LKW-MB-2078",  "Reifen vorne links abgefahren",    "Profil unter 4 mm, im nächsten Werkstattbesuch wechseln.",                    "2026-04-20", "Open", "Medium", 338500,  180, "Joe Sales"),
    (3, "BEA-2026-00003", "LKW-MAN-2079", "Klimaanlage kühlt nicht",          "Vermutlich Kältemittel verloren, kurzes Pfeifen beim Einschalten.",           "2026-04-22", "Open", "Medium", 428100,  320, "Joe Sales"),
    (4, "BEA-2026-00004", "PKW-VW-1250",  "Anhängerkupplung-Stecker locker",  "7-Pin-Stecker hat Wackelkontakt, Blinker hinten fällt zeitweise aus.",        "2026-04-28", "Open", "High",    82400,   85, "Carl Boss"),
    (5, "BEA-2026-00005", "STAPLER-LIN-1","Hubzylinder ölt",                  "Tropfen unter dem Stapler nach Standzeit, Hub-Performance noch unauffällig.","2026-04-30", "Open", "Medium",   9210,  650, "Henry Seed"),
    (6, "BEA-2026-00006", "ROLLTOR-H1-S", "Rolltor klemmt unten",             "Beim Schließen verkantet sich der Vorhang, manuelle Hilfe nötig.",            "2026-05-05", "Open", "High",     None,  280, "Carl Boss"),
    (7, "BEA-2026-00007", "LKW-IVE-2080", "Scheibenwischer hinten defekt",    "Motor brummt aber Wischerarm bewegt sich nicht.",                             "2026-03-12", "Done", "Low",    298400,   60, "Joe Sales"),
    (8, "BEA-2026-00008", "KEHR-1",       "Saugleistung nachgelassen",        "Seitenbürste dreht zu langsam, Filter verstopft?",                            "2026-04-10", "Open", "Low",      None,  120, "Carl Boss"),
]

# Schedule-Items
SCHEDULE_ITEMS = [
    # (id_offset, docno, asset_value, name, schedule_type, due_date, reported_date, status)
    (1,  "TER-2026-00001", "LKW-MB-2078",  "TÜV-Hauptuntersuchung", "TUV",        "2026-09-01", "2026-01-10", "Open"),
    (2,  "TER-2026-00002", "LKW-MB-2078",  "Sicherheitsprüfung",    "SP",         "2026-09-01", "2026-01-10", "Open"),
    (3,  "TER-2026-00003", "LKW-MAN-2079", "TÜV-Hauptuntersuchung", "TUV",        "2026-06-01", "2025-12-10", "Open"),
    (4,  "TER-2026-00004", "LKW-MAN-2079", "Sicherheitsprüfung",    "SP",         "2026-06-01", "2025-12-10", "Open"),
    (5,  "TER-2026-00005", "LKW-IVE-2080", "TÜV-Hauptuntersuchung", "TUV",        "2026-08-01", "2026-02-15", "Open"),
    (6,  "TER-2026-00006", "LKW-MB-2081",  "TÜV-Hauptuntersuchung", "TUV",        "2027-04-01", "2026-04-10", "Open"),
    (7,  "TER-2026-00007", "PKW-VW-1250",  "TÜV-Hauptuntersuchung", "TUV",        "2026-10-01", "2026-04-15", "Open"),
    (8,  "TER-2026-00008", "STAPLER-LIN-1","UVV-Prüfung",           "UVV",        "2026-07-01", "2026-01-20", "Open"),
    (9,  "TER-2026-00009", "STAPLER-LIN-2","UVV-Prüfung",           "UVV",        "2026-09-01", "2026-03-05", "Open"),
    (10, "TER-2026-00010", "FLG-EXT-101",  "Wartung Feuerlöscher",  "INSPECTION", "2027-01-01", "2026-01-05", "Open"),
    (11, "TER-2026-00011", "FLG-EXT-102",  "Wartung Feuerlöscher",  "INSPECTION", "2027-01-01", "2026-01-05", "Open"),
    (12, "TER-2026-00012", "PKW-OPL-1252", "Garantie-Ablauf",       "WARRANTY",   "2027-05-12", "2026-05-01", "Open"),
]

# WorkOrders
WORKORDERS = [
    # (id_offset, docno, asset_value, name, workshop_name, driver_name, internal_contact_name,
    #  scheduled_date, actual_date, completion_date, est_cost, actual_cost, ext_doc_no, status, description)
    (1, "WAU-2026-00001", "LKW-IVE-2080", "Wischer hinten + Sichtprüfung",   "Wood, Inc", "Joe Sales", "Carl Boss", "2026-03-15", "2026-03-15", "2026-03-15",  60,   78, "RG-2026-0034", "Completed", "Wischer hinten getauscht, Sicht-Check ohne Befund."),
    (2, "WAU-2026-00002", "LKW-MAN-2079", "Klimaservice + TÜV-Vorbereitung", "Wood, Inc", "Joe Sales", "Carl Boss", "2026-05-15", "2026-05-15", None,         550, None, None,            "Released",  "Geplant: Kältemittel + Bremsen-Vorcheck."),
    (3, "WAU-2026-00003", "LKW-MB-2078",  "Großwartung TÜV/SP + Klappe",     "Wood, Inc", "Joe Sales", "Carl Boss", "2026-08-25", None,         None,        1100, None, None,            "Draft",     "Disposition Sommer/Herbst."),
]

# WorkOrder-Items: (id_offset, workorder_docno, item_docno, is_resolved, lineno, note)
WORKORDER_ITEMS = [
    (1, "WAU-2026-00001", "BEA-2026-00007", "Y", 10, "Erledigt — Wischermotor war's."),
    (2, "WAU-2026-00003", "BEA-2026-00001", "Y", 10, "Klappe — komplett überholen."),
    (3, "WAU-2026-00003", "BEA-2026-00002", "Y", 20, "Reifen vorne, evtl. auch hinten prüfen."),
    (4, "WAU-2026-00003", "TER-2026-00001", "Y", 30, "TÜV-HU."),
    (5, "WAU-2026-00003", "TER-2026-00002", "Y", 40, "SP."),
    (6, "WAU-2026-00002", "BEA-2026-00003", "Y", 10, "Klima-Service."),
]


# --------------------------------------------------------------------------

def q(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    return str(value)


def build_sql() -> str:
    out = ["BEGIN;"]
    base = ID_OFFSET

    # Helper für die häufigen Audit-Spalten
    audit = f"{CLIENT}, {ORG}, 'Y', now(), {USER}, now(), {USER}"

    # 1) BXS_Asset
    for i, (off, val, name, klasse, mfr, model, sn, yr, cd, loc, st) in enumerate(ASSETS):
        aid = base + 100 + off
        ouu = uu(f"asset:{val}")
        out.append(
            f"INSERT INTO BXS_Asset (BXS_Asset_ID, BXS_Asset_UU, AD_Client_ID, AD_Org_ID, IsActive, "
            f"Created, CreatedBy, Updated, UpdatedBy, Value, Name, BXS_AssetClass_ID, AssetStatus, "
            f"Manufacturer, Model, SerialNo, YearBuilt, CommissionDate, Location) VALUES "
            f"({aid}, '{ouu}', {audit}, {q(val)}, {q(name)}, "
            f"(SELECT BXS_AssetClass_ID FROM BXS_AssetClass WHERE Value={q(klasse)}), "
            f"{q(st)}, {q(mfr)}, {q(model)}, {q(sn)}, {q(yr)}, {q(cd)}, {q(loc)}) "
            f"ON CONFLICT (BXS_Asset_UU) DO UPDATE SET Value=EXCLUDED.Value, Name=EXCLUDED.Name, "
            f"BXS_AssetClass_ID=EXCLUDED.BXS_AssetClass_ID, AssetStatus=EXCLUDED.AssetStatus, "
            f"Manufacturer=EXCLUDED.Manufacturer, Model=EXCLUDED.Model, SerialNo=EXCLUDED.SerialNo, "
            f"YearBuilt=EXCLUDED.YearBuilt, CommissionDate=EXCLUDED.CommissionDate, "
            f"Location=EXCLUDED.Location, Updated=now();"
        )

    # 2) BXS_AssetItem (Status, Defect, Schedule)
    for off, docno, asset_val, name, descr, rep_date, meter, user_name in STATUS_ITEMS:
        iid = base + 200 + off
        ouu = uu(f"item:status:{docno}")
        out.append(
            f"INSERT INTO BXS_AssetItem (BXS_AssetItem_ID, BXS_AssetItem_UU, AD_Client_ID, AD_Org_ID, "
            f"IsActive, Created, CreatedBy, Updated, UpdatedBy, DocumentNo, BXS_Asset_ID, Type, Name, "
            f"Description, ReportedDate, ItemStatus, CompletionDate, MeterReading, AD_User_ID) VALUES "
            f"({iid}, '{ouu}', {audit}, {q(docno)}, "
            f"(SELECT BXS_Asset_ID FROM BXS_Asset WHERE Value={q(asset_val)} AND AD_Client_ID={CLIENT}), "
            f"'Status', {q(name)}, {q(descr)}, {q(rep_date)}, 'Done', {q(rep_date)}, {q(meter)}, "
            f"(SELECT AD_User_ID FROM AD_User WHERE Name={q(user_name)} AND AD_Client_ID={CLIENT})) "
            f"ON CONFLICT (BXS_AssetItem_UU) DO UPDATE SET Name=EXCLUDED.Name, "
            f"Description=EXCLUDED.Description, ItemStatus=EXCLUDED.ItemStatus, Updated=now();"
        )

    for off, docno, asset_val, name, descr, rep_date, status, prio, meter, est_cost, user_name in DEFECT_ITEMS:
        iid = base + 300 + off
        ouu = uu(f"item:defect:{docno}")
        compdate = rep_date if status == "Done" else None
        out.append(
            f"INSERT INTO BXS_AssetItem (BXS_AssetItem_ID, BXS_AssetItem_UU, AD_Client_ID, AD_Org_ID, "
            f"IsActive, Created, CreatedBy, Updated, UpdatedBy, DocumentNo, BXS_Asset_ID, Type, Name, "
            f"Description, ReportedDate, ItemStatus, Priority, MeterReading, EstimatedCost, "
            f"CompletionDate, AD_User_ID) VALUES "
            f"({iid}, '{ouu}', {audit}, {q(docno)}, "
            f"(SELECT BXS_Asset_ID FROM BXS_Asset WHERE Value={q(asset_val)} AND AD_Client_ID={CLIENT}), "
            f"'Defect', {q(name)}, {q(descr)}, {q(rep_date)}, {q(status)}, {q(prio)}, {q(meter)}, "
            f"{q(est_cost)}, {q(compdate)}, "
            f"(SELECT AD_User_ID FROM AD_User WHERE Name={q(user_name)} AND AD_Client_ID={CLIENT})) "
            f"ON CONFLICT (BXS_AssetItem_UU) DO UPDATE SET Name=EXCLUDED.Name, "
            f"Description=EXCLUDED.Description, ItemStatus=EXCLUDED.ItemStatus, "
            f"Priority=EXCLUDED.Priority, EstimatedCost=EXCLUDED.EstimatedCost, Updated=now();"
        )

    for off, docno, asset_val, name, sched_type, due_date, rep_date, status in SCHEDULE_ITEMS:
        iid = base + 400 + off
        ouu = uu(f"item:schedule:{docno}")
        out.append(
            f"INSERT INTO BXS_AssetItem (BXS_AssetItem_ID, BXS_AssetItem_UU, AD_Client_ID, AD_Org_ID, "
            f"IsActive, Created, CreatedBy, Updated, UpdatedBy, DocumentNo, BXS_Asset_ID, Type, Name, "
            f"ReportedDate, DueDate, ItemStatus, BXS_ScheduleType_ID) VALUES "
            f"({iid}, '{ouu}', {audit}, {q(docno)}, "
            f"(SELECT BXS_Asset_ID FROM BXS_Asset WHERE Value={q(asset_val)} AND AD_Client_ID={CLIENT}), "
            f"'Schedule', {q(name)}, {q(rep_date)}, {q(due_date)}, {q(status)}, "
            f"(SELECT BXS_ScheduleType_ID FROM BXS_ScheduleType WHERE Value={q(sched_type)})) "
            f"ON CONFLICT (BXS_AssetItem_UU) DO UPDATE SET Name=EXCLUDED.Name, "
            f"DueDate=EXCLUDED.DueDate, ItemStatus=EXCLUDED.ItemStatus, "
            f"BXS_ScheduleType_ID=EXCLUDED.BXS_ScheduleType_ID, Updated=now();"
        )

    # 3) BXS_WorkOrder
    for off, docno, asset_val, name, workshop, driver, contact, sched, actual, comp, est, actual_cost, ext, status, descr in WORKORDERS:
        wid = base + 500 + off
        ouu = uu(f"workorder:{docno}")
        out.append(
            f"INSERT INTO BXS_WorkOrder (BXS_WorkOrder_ID, BXS_WorkOrder_UU, AD_Client_ID, AD_Org_ID, "
            f"IsActive, Created, CreatedBy, Updated, UpdatedBy, DocumentNo, Name, BXS_Asset_ID, "
            f"Workshop_ID, Driver_ID, InternalContact_ID, ScheduledDate, ActualDate, CompletionDate, "
            f"EstimatedCost, ActualCost, ExternalDocumentNo, WorkOrderStatus, Description) VALUES "
            f"({wid}, '{ouu}', {audit}, {q(docno)}, {q(name)}, "
            f"(SELECT BXS_Asset_ID FROM BXS_Asset WHERE Value={q(asset_val)} AND AD_Client_ID={CLIENT}), "
            f"(SELECT C_BPartner_ID FROM C_BPartner WHERE Name={q(workshop)} AND AD_Client_ID={CLIENT}), "
            f"(SELECT AD_User_ID FROM AD_User WHERE Name={q(driver)} AND AD_Client_ID={CLIENT}), "
            f"(SELECT AD_User_ID FROM AD_User WHERE Name={q(contact)} AND AD_Client_ID={CLIENT}), "
            f"{q(sched)}, {q(actual)}, {q(comp)}, {q(est)}, {q(actual_cost)}, {q(ext)}, "
            f"{q(status)}, {q(descr)}) "
            f"ON CONFLICT (BXS_WorkOrder_UU) DO UPDATE SET Name=EXCLUDED.Name, "
            f"WorkOrderStatus=EXCLUDED.WorkOrderStatus, ActualCost=EXCLUDED.ActualCost, "
            f"CompletionDate=EXCLUDED.CompletionDate, ExternalDocumentNo=EXCLUDED.ExternalDocumentNo, "
            f"Updated=now();"
        )

    # 4) BXS_WorkOrder_Item
    for off, wo_docno, item_docno, resolved, lineno, note in WORKORDER_ITEMS:
        wiid = base + 600 + off
        ouu = uu(f"woitem:{wo_docno}:{item_docno}")
        out.append(
            f"INSERT INTO BXS_WorkOrder_Item (BXS_WorkOrder_Item_ID, BXS_WorkOrder_Item_UU, AD_Client_ID, "
            f"AD_Org_ID, IsActive, Created, CreatedBy, Updated, UpdatedBy, BXS_WorkOrder_ID, "
            f"BXS_AssetItem_ID, IsResolved, LineNo, Note) VALUES "
            f"({wiid}, '{ouu}', {audit}, "
            f"(SELECT BXS_WorkOrder_ID FROM BXS_WorkOrder WHERE DocumentNo={q(wo_docno)} AND AD_Client_ID={CLIENT}), "
            f"(SELECT BXS_AssetItem_ID FROM BXS_AssetItem WHERE DocumentNo={q(item_docno)} AND AD_Client_ID={CLIENT}), "
            f"{q(resolved)}, {lineno}, {q(note)}) "
            f"ON CONFLICT (BXS_WorkOrder_Item_UU) DO UPDATE SET IsResolved=EXCLUDED.IsResolved, "
            f"LineNo=EXCLUDED.LineNo, Note=EXCLUDED.Note, Updated=now();"
        )

    out.append("COMMIT;")
    return "\n".join(out) + "\n"


def main() -> int:
    sql = build_sql()
    cmd = ["psql",
           "-h", os.environ.get("DBHOST", "localhost"),
           "-p", os.environ.get("DBPORT", "5432"),
           "-U", os.environ.get("DBUSER", "adempiere"),
           "-d", os.environ.get("DBNAME", "idempiere"),
           "-v", "ON_ERROR_STOP=1"]
    env = os.environ.copy()
    env.setdefault("PGPASSWORD", "adempiere")
    r = subprocess.run(cmd, input=sql, text=True, env=env)
    if r.returncode != 0:
        print("psql exit code:", r.returncode, file=sys.stderr)
        return r.returncode
    print(f"Eingespielt: {len(ASSETS)} Anlagen, {len(STATUS_ITEMS)} Statusberichte, "
          f"{len(DEFECT_ITEMS)} Beanstandungen, {len(SCHEDULE_ITEMS)} Wartungstermine, "
          f"{len(WORKORDERS)} Werkstattaufträge, {len(WORKORDER_ITEMS)} Werkstatt-Positionen")
    return 0


if __name__ == "__main__":
    sys.exit(main())
