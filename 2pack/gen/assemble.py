#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Generator für 2pack/source/PackOut.xml aus den YAML-Specs in 2pack/source/spec/.

Liest UUIDs aus uuids.csv (Repo-Root), ergänzt fehlende Einträge mit
neuen uuid4-Werten und schreibt die Datei zurück. Die UUIDs sind
projektübergreifend stabil — der Generator garantiert, dass derselbe
logische Schlüssel immer dieselbe UUID liefert.

Spec-Format siehe 2pack/source/spec/*.yaml. Dieser Generator ist
absichtlich auf das Anlagenbuch-Set zugeschnitten, kein generisches
2Pack-Tool.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import re
import sys
import uuid
import xml.etree.ElementTree as ET
import xml.sax.saxutils as saxutils
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# iDempiere-Konstanten (Reference-IDs in Core; bleiben stabil über Installationen)

DISPLAY_TYPE = {
    "ID":         13,
    "String":     10,
    "Text":       14,
    "Memo":       34,
    "Integer":    11,
    "Number":     22,
    "Amount":     12,
    "Date":       15,
    "DateTime":   16,
    "YesNo":      20,
    "List":       17,
    "Table":      18,
    "TableDir":   19,
    "Search":     30,
    "Button":     28,
    "UUID":       200231,
}

# AD_Reference-IDs für AD_Process_Para.AD_Reference_ID. Wir akzeptieren
# Aliase, die in YAML lesbar sind. „MultiSelectTable" ist die einzige
# Möglichkeit, ein Multi-Selection-Parameter mit Validierung gegen eine
# Tabelle zu bauen — IsMultiSelection ist KEIN Feld auf AD_Process_Para
# (anders als auf AD_Column), die Auswahl wird ausschließlich über das
# DisplayType-Reference 200162 gesteuert.
PROCESS_PARA_REFERENCE = {
    "Table":            18,
    "List":             17,
    "Yes-No":           20,
    "YesNo":            20,
    "String":           10,
    "Text":             14,
    "Integer":          11,
    "Number":           22,
    "Amount":           12,
    "Date":             15,
    "DateTime":         16,
    "Search":           30,
    "TableDir":         19,
    "MultiSelectList":  200161,  # Chosen Multiple Selection List
    "MultiSelectTable": 200162,  # Chosen Multiple Selection Table
    "MultiSelectSearch": 200163,
}

# Std-Spalten, die in jedem Tenant-Tabelle ergänzt werden (außer PK + UU).
# Werden mit fixen System-Element-IDs verknüpft.
STD_COLUMNS = [
    # (ColumnName, Element_ID, Reference, Mandatory, Default, Updateable)
    ("AD_Client_ID", 102, "Table",   True,  "@#AD_Client_ID@", False),
    ("AD_Org_ID",    113, "Table",   True,  "@#AD_Org_ID@",    True),
    ("IsActive",     348, "YesNo",   True,  "Y",               True),
    ("Created",      245, "DateTime",True,  "@#Date@",         False),
    ("CreatedBy",    246, "Table",   True,  "@#AD_User_ID@",   False),
    ("Updated",      607, "DateTime",True,  "@#Date@",         False),
    ("UpdatedBy",    608, "Table",   True,  "@#AD_User_ID@",   False),
]

STD_REF_VALUE = {
    "AD_Client_ID": 129,  # AD_Client Security
    "AD_Org_ID":    104,  # AD_Org Security
    "CreatedBy":    110,  # AD_User
    "UpdatedBy":    110,
}

# Core-AD_Element-IDs für Standard-Spaltennamen, die in iDempiere bereits
# existieren. Spalten dieser Namen erzeugen KEIN neues AD_Element, sondern
# referenzieren das vorhandene per ID. Falls ein Spaltenname in einer Spec
# eine andere Bedeutung hätte, wäre er BXS_-prefixed.
CORE_ELEMENTS = {
    "Value": 620, "Name": 469, "Description": 275,
    "Help": 326, "Note": 1115, "Comments": 230, "DocumentNo": 290,
    "C_UOM_ID": 215, "C_BPartner_ID": 187, "C_Invoice_ID": 1008,
    "AD_User_ID": 138, "AD_Client_ID": 102, "AD_Org_ID": 113,
    "IsActive": 348, "Created": 245, "CreatedBy": 246,
    "Updated": 607, "UpdatedBy": 608,
    "DateDoc": 265, "DocAction": 287,
    "EntityType": 1682, "Manufacturer": 1915, "S_Resource_ID": 1777,
    "Type": 600, "Priority": 1514, "DueDate": 2000,
    "LineNo": 2945, "Category": 52017, "Status": 3020,
}

# CreatedDate/UpdatedDate des <idempiere>-Root-Elements. Einzige Nicht-
# Determiniertheit des Generators. Für reproduzierbare Builds (Byte-Diff
# zwischen zwei Läufen) kann PACKOUT_NOW gesetzt werden; ohne die Variable
# bleibt es bei der aktuellen Uhrzeit — Default unverändert, golden-sicher.
NOW = os.environ.get("PACKOUT_NOW") \
    or dt.datetime.now().strftime("%a %b %d %H:%M:%S CET %Y")

# ---------------------------------------------------------------------------
# EntityType
#
# Jeder Application-Dictionary-Record trägt einen AD_EntityType-Code. Der
# Generator setzt ihn global aus dem package-Header (`entity_type:` —
# PFLICHTANGABE, kein stiller Default mehr; siehe main()). ENTITY_TYPE wird
# in main() einmalig überschrieben und von allen emit_*-Funktionen über
# b.leaf("EntityType", ENTITY_TYPE) gelesen.
ENTITY_TYPE = None

# Core-EntityTypes, die in JEDER iDempiere-Installation vorhanden sind. Für
# sie wird KEIN AD_EntityType-Record mitgeliefert (FK ist immer auflösbar).
CORE_ENTITY_TYPES = {"U", "D", "C", "EXT"}

# Eigene EntityType-Marken, die per 2Pack mitgeliefert werden MÜSSEN, sonst
# bricht auf einer frischen Ziel-DB die FK AD_*.EntityType → AD_EntityType.
# Feste UUIDs (NICHT ändern) aus plugins/template/db/000_entitytype_*.sql —
# alle BAY-/BXS-Plugins liefern denselben Record mit identischer UUID aus
# (ON CONFLICT DO NOTHING-Sharing; wer zuerst läuft, legt an).
ENTITY_TYPE_RECORDS: dict[str, dict[str, str]] = {
    "BAY": {
        "uu": "ea7c6bae-5992-4f08-8777-c264078da40f",
        "name": "FreiBier",
        "description": "Implementation from BX Service/Thomas Bayen for "
                       "FreiBier, German/European localization and more",
    },
    "BXS": {
        "uu": "a6667483-af36-4cca-9c98-e79a9f2fb0be",
        "name": "BX Service Community",
        "description": "Gemeinsame Marke der BX Service GmbH für "
                       "community-taugliche iDempiere-Plugins "
                       "(Namespace de.bxservice.*).",
    },
}

# ---------------------------------------------------------------------------
# UUID-Verwaltung


class UuidStore:
    """Persistenter Lookup logischer Schlüssel → UUID, gespeichert in uuids.csv."""

    HEADER_PATTERN = re.compile(r"^\s*#")

    def __init__(self, path: Path):
        self.path = path
        self._map: dict[str, str] = {}
        self._order: list[tuple[str, str, str]] = []  # (objtype, key, uuid) for round-trip
        self._comments: list[str] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        with self.path.open() as f:
            reader = csv.reader(f)
            header_skipped = False
            for row in reader:
                if not row:
                    continue
                if row[0].startswith("#") or (not header_skipped and row[0] == "ObjectType"):
                    self._comments.append(",".join(row))
                    header_skipped = True
                    continue
                objtype, key, u = row[0], row[1], row[2]
                full_key = f"{objtype}:{key}"
                self._map[full_key] = u
                self._order.append((objtype, key, u))

    def get(self, objtype: str, key: str) -> str:
        full = f"{objtype}:{key}"
        if full not in self._map:
            new = str(uuid.uuid4())
            self._map[full] = new
            self._order.append((objtype, key, new))
        return self._map[full]

    def save(self) -> None:
        with self.path.open("w") as f:
            for c in self._comments:
                f.write(c + "\n")
            for objtype, key, u in self._order:
                f.write(f"{objtype},{key},{u}\n")


# ---------------------------------------------------------------------------
# XML-Hilfen — wir generieren formatiertes XML manuell, weil ElementTree
# self-closing-Tags in iDempiere-Konvention nicht sauber abbildet.


def esc(value: Any) -> str:
    if value is None:
        return ""
    return saxutils.escape(str(value), {'"': "&quot;", "'": "&apos;"})


class XmlBuilder:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.indent = 0

    def _ind(self) -> str:
        return "    " * self.indent

    def open(self, tag: str, **attrs: Any) -> None:
        attr_str = "".join(f' {k}="{esc(v)}"' for k, v in attrs.items())
        self.lines.append(f"{self._ind()}<{tag}{attr_str}>")
        self.indent += 1

    def close(self, tag: str) -> None:
        self.indent -= 1
        self.lines.append(f"{self._ind()}</{tag}>")

    def leaf(self, tag: str, value: Any = None, **attrs: Any) -> None:
        attr_str = "".join(f' {k}="{esc(v)}"' for k, v in attrs.items())
        if value is None or value == "":
            self.lines.append(f"{self._ind()}<{tag}{attr_str}/>")
        else:
            self.lines.append(f"{self._ind()}<{tag}{attr_str}>{esc(value)}</{tag}>")

    def render(self) -> str:
        return "\n".join(self.lines) + "\n"


# ---------------------------------------------------------------------------
# Emit-Funktionen pro Record-Typ


def emit_trl(b: XmlBuilder, table: str, name: str, description: str = "",
             help_text: str = "", language: str = "de_DE") -> None:
    """Emit a nested <X_Trl type='translation'>… block. Must be inside the parent
    record (between its open and close), so the import handler updates the
    auto-created Trl row instead of inserting a duplicate."""
    b.open(table + "_Trl", type="translation")
    b.leaf("Name", name)
    b.leaf("Description", description or "")
    b.leaf("Help", help_text or "")
    b.leaf("AD_Language", language)
    b.leaf("IsActive", "Y")
    b.leaf("IsTranslated", "Y")
    b.close(table + "_Trl")


def emit_entitytype(b: XmlBuilder, code: str) -> None:
    """AD_EntityType-Record für eine eigene Marke (BAY/BXS). Wird als ERSTES
    Schema-Element emittiert, weil alle folgenden AD_*-Records ihn per FK
    (AD_*.EntityType → AD_EntityType.EntityType) referenzieren.

    Die UUID ist FEST (Registry oben), kommt NICHT aus uuids.csv — alle
    Plugins derselben Marke teilen denselben Record. Der iDempiere-PIPO-
    EntityTypeElementHandler findet ihn beim Reimport per AD_EntityType_UU
    und macht UPDATE statt INSERT (kein doppelter Code-PK).

    Für Core-EntityTypes (U/D/C/EXT) wird diese Funktion nicht aufgerufen —
    deren Record existiert in jeder Installation.
    """
    rec = ENTITY_TYPE_RECORDS[code]
    b.open("AD_EntityType", type="table")
    b.leaf("AD_Client_ID", 0)
    b.leaf("AD_Org_ID", 0)
    b.leaf("EntityType", code)
    b.leaf("Name", rec["name"])
    b.leaf("Description", rec.get("description", ""))
    b.leaf("Help")
    b.leaf("ModelPackage")
    b.leaf("IsActive", "Y")
    b.leaf("Processing", "N")
    b.leaf("AD_EntityType_UU", rec["uu"])
    b.close("AD_EntityType")


def emit_reference(b: XmlBuilder, ref: dict, uuids: UuidStore) -> None:
    ref_uu = uuids.get("AD_Reference", ref["name"])
    b.open("AD_Reference", type="table")
    b.leaf("AD_Client_ID", 0)
    b.leaf("AD_Org_ID", 0)
    b.leaf("Name", ref["label"])
    b.leaf("Description", ref.get("description", ""))
    b.leaf("Help")
    b.leaf("ValidationType", "L")  # List
    b.leaf("VFormat")
    b.leaf("EntityType", ENTITY_TYPE)
    b.leaf("IsActive", "Y")
    b.leaf("IsOrderByValue", "N")
    if ref.get("label_de"):
        emit_trl(b, "AD_Reference", ref["label_de"], ref.get("description", ""))
    b.leaf("AD_Reference_UU", ref_uu)
    b.close("AD_Reference")

    # Werte
    for v in ref["values"]:
        rl_key = f"{ref['name']}.{v['value']}"
        rl_uu = uuids.get("AD_Ref_List", rl_key)
        b.open("AD_Ref_List", type="table")
        b.leaf("AD_Client_ID", 0)
        b.leaf("AD_Org_ID", 0)
        b.leaf("Value", v["value"])
        b.leaf("Name", v["name"])
        b.leaf("Description", v.get("description", ""))
        b.leaf("AD_Reference_ID", ref_uu, reference="uuid", **{"reference-key": "AD_Reference"})
        b.leaf("EntityType", ENTITY_TYPE)
        b.leaf("IsActive", "Y")
        if v.get("name_de"):
            emit_trl(b, "AD_Ref_List", v["name_de"], v.get("description_de", v.get("description", "")))
        b.leaf("AD_Ref_List_UU", rl_uu)
        b.close("AD_Ref_List")

def emit_element(b: XmlBuilder, column_name: str, label: str, label_de: str,
                 description: str, help_text: str, uuids: UuidStore) -> str:
    """Legt AD_Element + nested Trl an; gibt UUID zurück."""
    el_uu = uuids.get("AD_Element", column_name)
    b.open("AD_Element", type="table")
    b.leaf("AD_Client_ID", 0)
    b.leaf("AD_Org_ID", 0)
    b.leaf("ColumnName", column_name)
    b.leaf("Name", label)
    b.leaf("PrintName", label)
    b.leaf("Description", description or "")
    b.leaf("Help", help_text or "")
    b.leaf("EntityType", ENTITY_TYPE)
    b.leaf("IsActive", "Y")
    if label_de:
        # AD_Element_Trl benötigt zusätzlich PrintName
        b.open("AD_Element_Trl", type="translation")
        b.leaf("Name", label_de)
        b.leaf("PrintName", label_de)
        b.leaf("Description", description or "")
        b.leaf("Help", help_text or "")
        b.leaf("AD_Language", "de_DE")
        b.leaf("IsActive", "Y")
        b.leaf("IsTranslated", "Y")
        b.close("AD_Element_Trl")
    b.leaf("AD_Element_UU", el_uu)
    b.close("AD_Element")
    return el_uu


def emit_table(b: XmlBuilder, table: dict, uuids: UuidStore) -> None:
    tbl_name = table["name"]
    tbl_uu = uuids.get("AD_Table", tbl_name)

    # 1) AD_Element nur für Custom-Spalten (PK, UU, BXS_-prefix). Für
    # Standardnamen wie Value/Name/Description benutzt emit_column die
    # Core-Element-ID aus CORE_ELEMENTS.
    pk_col = f"{tbl_name}_ID"
    uu_col = f"{tbl_name}_UU"
    emit_element(b, pk_col, table["label"], table.get("label_de", ""),
                 table.get("description", ""), table.get("help", ""), uuids)
    emit_element(b, uu_col, f"{table['label']} UUID", "",
                 f"UUID für {tbl_name}", "", uuids)
    for col in table["columns"]:
        if col["name"] in CORE_ELEMENTS:
            continue  # vorhandenes AD_Element wird in emit_column per ID referenziert
        emit_element(b,
                     col["name"],
                     col.get("label", col["name"].replace("_", " ")),
                     col.get("label_de", ""),
                     col.get("description", ""),
                     col.get("help", ""),
                     uuids)

    # 2) AD_Table
    b.open("AD_Table", type="table")
    b.leaf("AD_Client_ID", 0)
    b.leaf("AD_Org_ID", 0)
    b.leaf("Name", table["label"])
    b.leaf("Description", table.get("description", ""))
    b.leaf("Help", table.get("help", ""))
    # AD_Window_ID darf hier NICHT auf eine UUID verweisen, weil der
    # AD_Window-Datensatz im PackOut erst NACH den Tabellen kommt — sonst
    # bricht TableElementHandler die Tabellen-Anlage stumm ab. Die
    # primary_window-Verkabelung wird am Ende per emit_table_primary_window
    # nachgereicht (UPDATE auf den AD_Table-Datensatz via UUID).
    b.leaf("AD_Window_ID", reference="id")
    b.leaf("AD_Val_Rule_ID", reference="id")
    b.leaf("TableName", tbl_name)
    b.leaf("LoadSeq", 0)
    b.leaf("AccessLevel", str(table.get("access_level", "3")))
    b.leaf("IsActive", "Y")
    b.leaf("IsSecurityEnabled", "N")
    b.leaf("IsDeleteable", "Y")
    b.leaf("IsHighVolume", "N")
    b.leaf("IsView", "N")
    b.leaf("EntityType", ENTITY_TYPE)
    b.leaf("ImportTable", "N")
    b.leaf("IsChangeLog", "Y")
    b.leaf("ReplicationType", "L")
    b.leaf("PO_Window_ID", reference="id")
    b.leaf("CopyColumnsFromTable", "N")
    b.leaf("IsCentrallyMaintained", "Y")
    b.leaf("AD_Table_UU", tbl_uu)
    b.leaf("Processing", "N")
    b.leaf("DatabaseViewDrop", "N")
    b.leaf("CopyComponentsFromView", "N")
    b.leaf("CreateWindowFromTable", "N")
    b.leaf("IsShowInDrillOptions", "N")
    b.leaf("IsPartition", "N")
    b.leaf("CreatePartition", "N")

    # 3) AD_Column für PK + UU + Standard-Spalten + Custom-Spalten
    seq = 0

    def col(**kwargs: Any) -> None:
        nonlocal seq
        seq += 10
        emit_column(b, tbl_uu, seq, kwargs, uuids)

    # PK
    col(column_name=pk_col, label=table["label"], reference="ID",
        is_key=True, mandatory=True, updateable=False, length=22,
        element_uuid=uuids.get("AD_Element", pk_col))
    # UU
    col(column_name=uu_col, label=f"{table['label']} UUID", reference="String",
        mandatory=False, updateable=False, length=36,
        element_uuid=uuids.get("AD_Element", uu_col))
    # Std-Spalten — verwenden Core-Element-IDs
    for cn, el_id, ref_name, mand, default, upd in STD_COLUMNS:
        col(column_name=cn, label=cn, reference=ref_name, mandatory=mand,
            updateable=upd, default=default, length=22 if ref_name == "Table" else 1 if ref_name == "YesNo" else 7,
            element_id=el_id,
            ref_value_id=STD_REF_VALUE.get(cn))
    # Custom-Spalten
    identifier_cols = []
    for c in table["columns"]:
        elem_args: dict[str, Any] = {}
        if c["name"] in CORE_ELEMENTS:
            elem_args["element_id"] = CORE_ELEMENTS[c["name"]]
        else:
            elem_args["element_uuid"] = uuids.get("AD_Element", c["name"])
        # List columns need AD_Reference_Value_ID pointing to the AD_Reference UUID
        if c.get("ref_value"):
            elem_args["ref_value_uuid"] = uuids.get("AD_Reference", c["ref_value"])
        if c.get("ref_value_id"):
            elem_args["ref_value_id"] = c["ref_value_id"]
        col(column_name=c["name"],
            label=c.get("label", c["name"]),
            reference=c["type"],
            ref_table=c.get("ref"),
            mandatory=c.get("mandatory", False),
            updateable=c.get("updateable", True),
            is_parent=c.get("is_parent", False),
            length=c.get("length", _default_length(c["type"])),
            default=c.get("default", ""),
            help_text=c.get("help", ""),
            description=c.get("description", ""),
            is_identifier=bool(c.get("identifier_seq")),
            seq_no_identifier=c.get("identifier_seq", 0),
            column_sql=c.get("column_sql", ""),
            ad_process=c.get("ad_process", ""),
            **elem_args)
        if c.get("identifier_seq"):
            identifier_cols.append(c["name"])

    b.close("AD_Table")
    # AD_Sequence wird automatisch von MTable.afterSave() erzeugt — kein
    # eigener Eintrag im 2Pack nötig.


def emit_table_primary_window(b: XmlBuilder, table: dict, uuids: UuidStore) -> None:
    """Nachträgliches UPDATE auf AD_Table, um AD_Window_ID zu setzen.

    Wird nach allen Windows emittiert. PIPO merged AD_Table-Records über
    die UUID — ein Mini-Record mit Name + AD_Window_ID + UU reicht.
    """
    if not table.get("primary_window"):
        return
    tbl_uu = uuids.get("AD_Table", table["name"])
    win_uu = uuids.get("AD_Window", table["primary_window"])
    b.open("AD_Table", type="table")
    b.leaf("AD_Client_ID", 0)
    b.leaf("AD_Org_ID", 0)
    b.leaf("Name", table["label"])
    b.leaf("TableName", table["name"])
    b.leaf("AD_Window_ID", win_uu, reference="uuid", **{"reference-key": "AD_Window"})
    b.leaf("AD_Table_UU", tbl_uu)
    b.close("AD_Table")


def _default_length(reftype: str) -> int:
    return {
        "String": 60, "Text": 2000, "Memo": 4000,
        "Integer": 11, "Number": 14, "Amount": 14,
        "Date": 7, "DateTime": 7, "YesNo": 1,
        "List": 60, "Table": 22, "TableDir": 22, "Search": 22,
        "ID": 22, "UUID": 36, "Button": 1,
    }.get(reftype, 60)


def emit_column(b: XmlBuilder, table_uu: str, seq: int, c: dict, uuids: UuidStore) -> None:
    col_uu = uuids.get("AD_Column", c.get("table_name", "") + "." + c["column_name"]) \
        if False else uuids.get("AD_Column", _col_key(table_uu, c["column_name"]))

    ref_id = DISPLAY_TYPE[c["reference"]]
    is_key = c.get("is_key", False)
    is_uu_col = c["column_name"].endswith("_UU")

    b.open("AD_Column", type="table")
    b.leaf("IsSyncDatabase", "Y")
    b.leaf("AD_Table_ID", table_uu, reference="uuid", **{"reference-key": "AD_Table"})

    # Reference-Value
    rv_id = c.get("ref_value_id")
    rv_uuid = c.get("ref_value_uuid")
    if rv_id:
        b.leaf("AD_Reference_Value_ID", rv_id, reference="id")
    elif rv_uuid:
        b.leaf("AD_Reference_Value_ID", rv_uuid, reference="uuid",
               **{"reference-key": "AD_Reference"})
    else:
        b.leaf("AD_Reference_Value_ID", reference="id")

    b.leaf("AD_Client_ID", 0)
    b.leaf("AD_Org_ID", 0)
    b.leaf("Version", 0)
    b.leaf("Name", c["label"])
    b.leaf("Description", c.get("description", ""))
    b.leaf("Help", c.get("help_text", ""))
    b.leaf("AD_Val_Rule_ID", reference="id")
    b.leaf("ColumnName", c["column_name"])
    b.leaf("DefaultValue", c.get("default", ""))
    b.leaf("FieldLength", c["length"])
    b.leaf("IsKey", "Y" if is_key else "N")
    b.leaf("IsParent", "Y" if c.get("is_parent") else "N")
    b.leaf("IsMandatory", "Y" if c.get("mandatory") else "N")
    b.leaf("IsTranslated", "N")
    b.leaf("IsIdentifier", "Y" if c.get("is_identifier") else "N")
    b.leaf("SeqNo", c.get("seq_no_identifier", 0) if c.get("is_identifier") else 0)
    b.leaf("IsEncrypted", "N")
    b.leaf("AD_Reference_ID", ref_id, reference="id")
    b.leaf("IsActive", "Y")
    b.leaf("VFormat")
    b.leaf("Callout")
    if c.get("element_id"):
        b.leaf("AD_Element_ID", c["element_id"], reference="id")
    else:
        b.leaf("AD_Element_ID", c["element_uuid"], reference="uuid",
               **{"reference-key": "AD_Element"})
    b.leaf("IsUpdateable", "Y" if c.get("updateable", True) else "N")
    if c.get("ad_process"):
        b.leaf("AD_Process_ID",
               uuids.get("AD_Process", c["ad_process"]),
               reference="uuid", **{"reference-key": "AD_Process"})
    else:
        b.leaf("AD_Process_ID", reference="id")
    b.leaf("ValueMin")
    b.leaf("ValueMax")
    b.leaf("IsSelectionColumn", "N")
    b.leaf("ReadOnlyLogic")
    b.leaf("EntityType", ENTITY_TYPE)
    b.leaf("IsAlwaysUpdateable", "N")
    b.leaf("ColumnSQL", c.get("column_sql", ""))
    b.leaf("MandatoryLogic")
    b.leaf("IsAutocomplete", "N")
    b.leaf("IsAllowLogging", "Y")
    b.leaf("FormatPattern")
    b.leaf("AD_Chart_ID", reference="id")
    b.leaf("AD_Column_UU", col_uu)
    b.leaf("IsAllowCopy", "N" if is_key or is_uu_col else "Y")
    b.leaf("SeqNoSelection", 0)
    b.leaf("IsToolbarButton", "N")
    b.leaf("IsSecure", "N")
    b.leaf("FKConstraintName")
    b.leaf("FKConstraintType", "N")
    b.leaf("PA_DashboardContent_ID", reference="id")
    b.leaf("Placeholder")
    b.leaf("IsHtml", "N")
    b.leaf("AD_Val_Rule_Lookup_ID", reference="id")
    b.close("AD_Column")


def _col_key(table_uu: str, col_name: str) -> str:
    return f"{table_uu[:8]}.{col_name}"


# ---------------------------------------------------------------------------
# Window/Tab/Field/Menu

# Schlüssel des Top-Level-Menüknotens „Anlagenbuch" (Summary-Menu).
# Alle 2Pack-Menüpunkte hängen darunter — siehe emit_anlagenbuch_root und
# emit_menu. Wenn das 2Pack später um Untergruppen erweitert wird, wird
# stattdessen eine `menu:`-Sektion in den Specs durchgereicht; bis dahin
# bleibt es bei einem flachen Knoten.
ANLAGENBUCH_MENU_KEY = "BXS_Menu_Anlagenbuch"

# Hoher SeqNo-Wert für den „Anlagenbuch"-Knoten direkt unter Root.
# Der pipo MenuElementHandler ruft die FreeSlot-Logik
#   UPDATE AD_TREENODEMM SET SeqNo=SeqNo+1 WHERE SeqNo>=? ...
# auf, daher reicht jeder Wert größer als die heute belegte SeqNo unter
# Root. 999 ist konventionell „ganz am Ende" und kollidiert in praktisch
# keinem produktiven iDempiere mit einem Standardmenü.
ANLAGENBUCH_ROOT_SEQNO = 999

# Konfigurierbare Menü-Wurzel (package-Header `menu_root:`). In main()
# überschrieben. Zwei Modi:
#   "summary" — eigener Summary-Knoten (Default-Name „Anlagenbuch"); alle
#               Window/Process/Form-Menüs ohne expliziten `menu.parent`
#               hängen darunter. Default, damit Anlagenbuch byte-gleich bleibt.
#   "root"    — KEIN Summary-Knoten; Kinder hängen direkt unter dem
#               DB-Menü-Root (Parent_ID=0). Für Plugins mit nur einem
#               Menüpunkt (z. B. aireports: eine einzige Form).
# Die Defaults reproduzieren den bisherigen Anlagenbuch-Stand; ein Plugin
# überschreibt sie vollständig über `menu_root:` in 00-package.yaml.
MENU_ROOT_MODE = "summary"
MENU_ROOT_KEY = ANLAGENBUCH_MENU_KEY
MENU_ROOT_NAME = "Anlagenbuch"
MENU_ROOT_NAME_DE = "Anlagenbuch"
MENU_ROOT_DESC = "Wartungs- und Fehlerberichts-System"
MENU_ROOT_SEQNO = ANLAGENBUCH_ROOT_SEQNO


def _menu_parent(explicit_parent: str | None) -> dict:
    """Liefert die parent-kwargs für emit_menu aus optionalem Spec-Override
    und globalem Menü-Wurzel-Modus. Explizites `menu.parent` schlägt immer
    den Modus. Im „root"-Modus hängt der Default direkt unter DB-Root
    (Parent_ID=0), sonst unter dem Summary-Knoten."""
    if explicit_parent:
        return {"parent_key": explicit_parent}
    if MENU_ROOT_MODE == "root":
        return {"parent_id": 0}
    return {"parent_key": MENU_ROOT_KEY}


def emit_menu(b: XmlBuilder, uuids: UuidStore, *,
              menu_key: str,
              name: str,
              name_de: str | None = None,
              description: str = "",
              action: str | None = None,
              target_table: str | None = None,
              target_uu: str | None = None,
              parent_key: str | None = None,
              parent_id: int | None = None,
              seq_no: int = 10,
              is_summary: bool = False) -> None:
    """Ein AD_Menu-Record mit Tree-Verkabelung (Parent_ID + SeqNo).

    `action` ist eines der gültigen AD_Menu.Action-Werte aus AD_Reference 104.
    ACHTUNG, Form und WorkFlow sind nicht-intuitiv kodiert (verifiziert gegen
    X_AD_Menu.ACTION_* im Core):
      W=Window, P=Process, R=Report, X=Form, F=WorkFlow, T=Task,
      I=Info, B=Workbench, D=Detail
    Bei Summary-Knoten (is_summary=True) bleibt Action **leer** —
    AD_Reference 104 kennt kein „Summary"-Token; alle Summary-Menus in der
    DB haben Action=NULL. `action="N"` hatte sich als Validation-Fehler
    erwiesen (PackIn-Test 2026-05-12). Für Nicht-Summary-Knoten muss
    target_table+target_uu gesetzt sein.

    `parent_key` referenziert per UUID einen anderen via emit_menu erzeugten
    Knoten. `parent_id` als Alternative für Verankerung an Core-Menüs
    (numerische AD_Menu_ID). Wird beides weggelassen, hängt der Eintrag bei
    Root."""
    menu_uu = uuids.get("AD_Menu", menu_key)

    b.open("AD_Menu", type="table")
    b.leaf("AD_Client_ID", 0)
    b.leaf("AD_Org_ID", 0)
    b.leaf("Name", name)
    b.leaf("Description", description)
    b.leaf("IsActive", "Y")
    if not is_summary and action:
        b.leaf("Action", action)

    # Target-Referenzen: für die nicht-genutzten ActionTypes leere id-Refs
    # ausgeben (iDempiere-Import erwartet die Properties), die genutzte
    # wird mit dem UUID-Verweis bestückt.
    for kind in ("AD_Window", "AD_Process", "AD_Form", "AD_Workflow", "AD_Task"):
        if target_table == kind and target_uu:
            b.leaf(f"{kind}_ID", target_uu, reference="uuid",
                   **{"reference-key": kind})
        else:
            b.leaf(f"{kind}_ID", reference="id")
    b.leaf("EntityType", ENTITY_TYPE)
    b.leaf("IsSummary", "Y" if is_summary else "N")
    b.leaf("IsReadOnly", "N")
    b.leaf("IsSOTrx", "Y")
    b.leaf("AD_InfoWindow_ID", reference="id")

    # Tree-Position: vom MenuElementHandler ausgewertet, in AD_TreeNodeMM
    # eingetragen (UPDATE wenn AD_Menu.afterSave() den Knoten schon
    # eingefügt hat, sonst INSERT).
    if parent_key:
        parent_uu = uuids.get("AD_Menu", parent_key)
        b.leaf("Parent_ID", parent_uu, reference="uuid",
               **{"reference-key": "AD_Menu"})
    elif parent_id is not None:
        b.leaf("Parent_ID", parent_id, reference="id")
    b.leaf("SeqNo", seq_no)

    if name_de:
        emit_trl(b, "AD_Menu", name_de, description)
    b.leaf("AD_Menu_UU", menu_uu)
    b.close("AD_Menu")


def emit_menu_root(b: XmlBuilder, uuids: UuidStore) -> None:
    """Top-Level Summary-Menü (Default-Name „Anlagenbuch") — hängt direkt
    unter dem DB-Menü-Root (Parent_ID=0). Name/Key/Beschreibung/SeqNo kommen
    aus den MENU_ROOT_*-Globals (package-Header `menu_root:`). Wird im
    „root"-Modus NICHT aufgerufen (dann hängen die Kinder selbst unter Root)."""
    emit_menu(b, uuids,
              menu_key=MENU_ROOT_KEY,
              name=MENU_ROOT_NAME,
              name_de=MENU_ROOT_NAME_DE,
              description=MENU_ROOT_DESC,
              parent_id=0,
              seq_no=MENU_ROOT_SEQNO,
              is_summary=True)


def emit_window(b: XmlBuilder, w: dict, tables_by_name: dict, uuids: UuidStore) -> None:
    win_uu = uuids.get("AD_Window", w["name"])

    b.open("AD_Window", type="table")
    b.leaf("AD_Client_ID", 0)
    b.leaf("AD_Org_ID", 0)
    b.leaf("Name", w["label"])
    b.leaf("Description", w.get("description", ""))
    b.leaf("Help", w.get("help", ""))
    b.leaf("WindowType", w.get("window_type", "M"))  # Maintain
    b.leaf("IsActive", "Y")
    b.leaf("IsDefault", "N")
    b.leaf("IsSOTrx", "Y")
    b.leaf("EntityType", ENTITY_TYPE)
    b.leaf("AD_Color_ID", reference="id")
    b.leaf("AD_Image_ID", reference="id")
    b.leaf("ProcessParameterLayout", "V")
    if w.get("label_de"):
        emit_trl(b, "AD_Window", w["label_de"],
                 w.get("description_de", w.get("description", "")),
                 w.get("help_de", w.get("help", "")))
    b.leaf("AD_Window_UU", win_uu)
    b.close("AD_Window")

    # Tabs
    for tab in w["tabs"]:
        emit_tab(b, win_uu, w["name"], tab, tables_by_name, uuids)

    emit_menu(b, uuids,
              menu_key=w["name"],
              name=w["label"],
              name_de=w.get("label_de"),
              description=w.get("description", ""),
              action="W",
              target_table="AD_Window",
              target_uu=win_uu,
              seq_no=w.get("menu", {}).get("seq", 10),
              **_menu_parent(w.get("menu", {}).get("parent")))


def emit_form(b: XmlBuilder, form: dict, uuids: UuidStore) -> None:
    """AD_Form (ZK-Special-Form, registriert über eine OSGi-FormFactory) plus
    Menü-Eintrag (Action='X' = Form, siehe emit_menu-Docstring).

    Forms sind reiner UI-Code: der `classname` zeigt auf die im Plugin
    registrierte ADForm-Implementierung; das 2Pack liefert nur den
    Dictionary-Eintrag, damit sie im Menü auftaucht.

    YAML-Felder:
      name:           logischer Schlüssel (uuids.csv) — Pflicht
      label / label_de: AD_Form.Name (EN) + dt. Übersetzung
      description / help (+ _de)
      classname:      vollqualifizierter Java-Klassenname der ADForm
      access_level:   AccessLevel-Code (Default '3' = Client+Org; ZK-Forms,
                      die auch im System-Mandanten laufen sollen, '6' =
                      System+Client)
      beta:           IsBetaFunctionality, bool, Default False
      menu:           optionale { seq, parent }-Sektion wie bei Windows;
                      Default-Parent ist der Anlagenbuch-Knoten.
    """
    form_uu = uuids.get("AD_Form", form["name"])
    label = form.get("label", form["name"])

    b.open("AD_Form", type="table")
    b.leaf("AD_Client_ID", 0)
    b.leaf("AD_Org_ID", 0)
    b.leaf("Name", label)
    b.leaf("Description", form.get("description", ""))
    b.leaf("Help", form.get("help", ""))
    b.leaf("AccessLevel", str(form.get("access_level", "3")))
    b.leaf("EntityType", ENTITY_TYPE)
    b.leaf("Classname", form.get("classname", ""))
    b.leaf("IsActive", "Y")
    b.leaf("IsBetaFunctionality", _yn(form.get("beta", "N")))
    if form.get("label_de"):
        emit_trl(b, "AD_Form", form["label_de"],
                 form.get("description_de", form.get("description", "")),
                 form.get("help_de", form.get("help", "")))
    b.leaf("AD_Form_UU", form_uu)
    b.close("AD_Form")

    menu_cfg = form.get("menu") or {}
    emit_menu(b, uuids,
              menu_key=f"Form.{form['name']}",
              name=label,
              name_de=form.get("label_de"),
              description=form.get("description", ""),
              action="X",  # X = Form (NICHT F — siehe emit_menu-Docstring)
              target_table="AD_Form",
              target_uu=form_uu,
              seq_no=menu_cfg.get("seq", 60),
              **_menu_parent(menu_cfg.get("parent")))


def emit_tab(b: XmlBuilder, win_uu: str, win_name: str, tab: dict,
             tables_by_name: dict, uuids: UuidStore) -> None:
    tab_key = f"{win_name}.{tab['name']}"
    tab_uu = uuids.get("AD_Tab", tab_key)
    table = tables_by_name[tab["table"]]
    table_uu = uuids.get("AD_Table", tab["table"])

    b.open("AD_Tab", type="table")
    b.leaf("AD_Client_ID", 0)
    b.leaf("AD_Org_ID", 0)
    b.leaf("Name", tab["name"])
    b.leaf("Description", tab.get("description", ""))
    b.leaf("Help", tab.get("help", ""))
    b.leaf("AD_Column_ID", reference="id")
    b.leaf("AD_Table_ID", table_uu, reference="uuid", **{"reference-key": "AD_Table"})
    b.leaf("AD_Window_ID", win_uu, reference="uuid", **{"reference-key": "AD_Window"})
    b.leaf("EntityType", ENTITY_TYPE)
    b.leaf("HasTree", "N")
    b.leaf("IsActive", "Y")
    b.leaf("IsAdvancedTab", "N")
    b.leaf("IsAllowAdvancedLookup", "Y")
    b.leaf("IsInfoTab", "N")
    b.leaf("IsInsertRecord", "N" if tab.get("read_only") else "Y")
    b.leaf("IsLookupOnlySelection", "N")
    b.leaf("IsReadOnly", "Y" if tab.get("read_only") else "N")
    b.leaf("IsSingleRow", "Y" if tab.get("single_row", tab.get("tab_level", 0) == 0) else "N")
    b.leaf("IsSortTab", "N")
    b.leaf("IsTranslationTab", "N")
    b.leaf("MaxQueryRecords", 0)
    b.leaf("Processing", "N")
    b.leaf("SeqNo", tab["seq"])
    b.leaf("TabLevel", tab.get("tab_level", 0))
    b.leaf("Importing", "N")
    b.leaf("IsChangeLog", "N")
    b.leaf("CommitWarning")
    b.leaf("DisplayLogic", tab.get("display_logic", ""))
    b.leaf("ReadOnlyLogic", tab.get("read_only_logic", ""))
    b.leaf("OrderByClause", tab.get("order_by", ""))
    b.leaf("WhereClause", tab.get("where_clause", tab.get("where", "")))
    # Parent_Column_ID — explizite Tab-Verknüpfung zur Eltern-Spalte, wenn
    # die Spalte selbst kein IsParent='Y' tragen darf (z.B. weil sie in
    # ihrem primären Fenster als normales TableDir-Auswahlfeld dienen
    # soll). GridTab fällt laut iDempiere-Konvention auf diesen Wert
    # zurück, wenn keine IsParent-Spalte existiert (vgl. GridTab.java
    # L1335 — vom CSV-Importer ignoriert, siehe TBB006).
    if tab.get("parent_column"):
        parent_col_key = _col_key(table_uu, tab["parent_column"])
        b.leaf("Parent_Column_ID",
               uuids.get("AD_Column", parent_col_key),
               reference="uuid", **{"reference-key": "AD_Column"})
    else:
        b.leaf("Parent_Column_ID", reference="id")
    b.leaf("ImportFields", "N")
    b.leaf("IsCheckParentsChanged", "Y")
    b.leaf("IsRefreshAllOnActivate", "N")
    # AD_Tab.AD_Process_ID — wird vom Toolbar-Print-Knopf abgefragt:
    # GridTab.isPrinted() liefert true, wenn dieser Wert ≠ 0 ist; sonst
    # graut die WindowToolbar den Print-Button aus, und das Report-Menü
    # erscheint nicht. Als Wert nehmen wir den per `print_process`
    # benannten AD_Process (üblicherweise einer der BXS_Print_*-Reports).
    if tab.get("print_process"):
        b.leaf("AD_Process_ID",
               uuids.get("AD_Process", tab["print_process"]),
               reference="uuid", **{"reference-key": "AD_Process"})
    else:
        b.leaf("AD_Process_ID", reference="id")
    if tab.get("name_de"):
        emit_trl(b, "AD_Tab", tab["name_de"],
                 tab.get("description_de", tab.get("description", "")),
                 tab.get("help_de", tab.get("help", "")))
    b.leaf("AD_Tab_UU", tab_uu)
    b.close("AD_Tab")

    # AD_Field für ALLE Spalten der Tabelle. iDempiere-Konvention: jeder Tab
    # listet jede DB-Spalte als Field, weil GridTab.setCurrentRow() den
    # Tab-Kontext nur für Spalten mit Field füllt. Fehlt z.B. AD_Client_ID,
    # liest MRole.canUpdate AD_Client_ID=-1 → Save-Fehler "missing=C".
    # Fehlt der Parent-Link (BXS_Asset_ID), filtert das Detail-Tab leer.
    # System-/Audit-Spalten werden mit IsDisplayed=N versteckt.
    pk_col_name = f"{table['name']}_ID"
    uu_col_name = f"{table['name']}_UU"

    # Optionale Whitelist für Übersichts-Tabs: zeigt nur die genannten
    # Spalten in Kopf+Grid, alle anderen Business-Spalten werden ausgeblendet.
    # System/Audit-Spalten bleiben unabhängig davon hidden (PackIn braucht sie
    # als Field-Records, sonst Save-Fehler "missing=C"). Ausnahme: der PK
    # darf explizit in die Whitelist aufgenommen werden — z.B. in Read-only-
    # Sub-Tabs, wo das ID-Feld als Zoom-Anker ins Detail-Fenster dient.
    displayed_whitelist = tab.get("displayed_columns")
    pk_in_whitelist = (displayed_whitelist is not None
                       and pk_col_name in displayed_whitelist)

    hidden_columns = {uu_col_name,
                      "Created", "CreatedBy", "Updated", "UpdatedBy"}
    if not pk_in_whitelist:
        hidden_columns.add(pk_col_name)
    # AD_Client_ID und AD_Org_ID müssen als Fields existieren (Kontext!),
    # werden aber nicht angezeigt: Org wird vom System gefüllt.
    system_hidden = {"AD_Client_ID", "AD_Org_ID"}

    custom_field_columns = list(table["columns"])
    custom_names = {c["name"] for c in custom_field_columns}
    # IsActive prominent zeigen. type="YesNo" mitgeben, damit das Layout
    # die Checkbox eine Spalte rechts platziert (sonst rutscht sie unter
    # die Labels).
    if "IsActive" not in custom_names:
        custom_field_columns.append({
            "name": "IsActive", "label": "Active", "label_de": "Aktiv",
            "type": "YesNo",
        })
        custom_names.add("IsActive")
    # System-/Audit-Spalten am Ende, hidden — außer der PK, falls per
    # displayed_columns explizit angefordert.
    extra_hidden = []
    for cn in [pk_col_name, uu_col_name, "AD_Client_ID", "AD_Org_ID",
               "Created", "CreatedBy", "Updated", "UpdatedBy"]:
        if cn not in custom_names:
            is_pk_visible = (cn == pk_col_name and pk_in_whitelist)
            extra_hidden.append({"name": cn, "label": cn,
                                 "_hidden": not is_pk_visible})
    field_columns = custom_field_columns + extra_hidden

    seq = 0
    for c in field_columns:
        seq += 10
        col_key = _col_key(table_uu, c["name"])
        col_uu = uuids.get("AD_Column", col_key)
        field_key = f"{tab_key}.{c['name']}"
        field_uu = uuids.get("AD_Field", field_key)
        is_hidden = (c.get("_hidden", False)
                     or c.get("is_parent", False)
                     or c["name"] in hidden_columns
                     or c["name"] in system_hidden)
        if displayed_whitelist is not None and not is_hidden:
            is_hidden = c["name"] not in displayed_whitelist
        displayed = "N" if is_hidden else "Y"

        b.open("AD_Field", type="table")
        b.leaf("AD_Client_ID", 0)
        b.leaf("AD_Org_ID", 0)
        b.leaf("Name", c.get("label", c["name"]))
        b.leaf("Description", c.get("description", ""))
        b.leaf("Help", c.get("help", ""))
        b.leaf("AD_Column_ID", col_uu, reference="uuid", **{"reference-key": "AD_Column"})
        b.leaf("AD_Tab_ID", tab_uu, reference="uuid", **{"reference-key": "AD_Tab"})
        b.leaf("EntityType", ENTITY_TYPE)
        b.leaf("IsActive", "Y")
        b.leaf("IsCentrallyMaintained", "Y")
        b.leaf("IsDisplayed", displayed)
        b.leaf("IsDisplayedGrid", displayed)
        b.leaf("IsEncrypted", "N")
        b.leaf("IsFieldOnly", "N")
        b.leaf("IsHeading", "N")
        b.leaf("IsReadOnly", "N")
        b.leaf("IsSameLine", "N")
        b.leaf("DisplayLength", 0)
        b.leaf("DisplayLogic", c.get("display_logic", ""))
        b.leaf("SeqNo", seq)
        b.leaf("SeqNoGrid", seq)
        b.leaf("AD_FieldGroup_ID", reference="id")
        b.leaf("SortNo", 0)
        # 6-Spalten-Layout: gewöhnliche Felder bekommen Label-Spalte 1
        # (links) bzw. 4 (rechts) mit ColumnSpan=2. Buttons und Checkboxen
        # haben keinen sichtbaren Label-Text — würden sie in Spalte 1/4
        # gerendert, säßen sie unter den Labels und sähen optisch
        # versetzt aus. Deshalb pro Typ um eine Spalte nach rechts
        # schieben, in die eigentliche Wert-Spalte.
        col_type = c.get("type", "")
        is_widget = col_type in ("Button", "YesNo")
        base_x = 1 if (seq // 10) % 2 == 1 else 4
        b.leaf("XPosition", base_x + 1 if is_widget else base_x)
        b.leaf("ColumnSpan", 1 if is_widget else 2)
        b.leaf("NumLines", 1)
        b.leaf("IsQuickEntry", "N")
        if c.get("label_de"):
            emit_trl(b, "AD_Field", c["label_de"],
                     c.get("description_de", c.get("description", "")),
                     c.get("help_de", c.get("help", "")))
        b.leaf("AD_Field_UU", field_uu)
        b.close("AD_Field")


# ---------------------------------------------------------------------------
# AD_Process — Buttons / Berichte / Skript-Prozesse


def emit_validation_table(b: XmlBuilder, vt: dict, uuids: UuidStore) -> None:
    """AD_Reference mit ValidationType='T' (Table) plus AD_Ref_Table-Eintrag,
    der die zugehörige Tabelle/Schlüsselspalte/Anzeigespalte definiert.
    Dient als `AD_Reference_Value_ID` für AD_Process_Para mit
    Reference=Table/MultiSelectTable.

    YAML-Felder:
      name: logischer Schlüssel (eindeutig, auch für UUID-Lookup)
      label / label_de: Name + dt. Übersetzung
      ad_table: Tabellenname (BXS_… oder Core)
      key_column: optional, default = <ad_table>_ID
      display_column: optional, default = "Name"
      order_by: optional Order-Klausel
    """
    ref_uu = uuids.get("AD_Reference", vt["name"])
    ad_table = vt["ad_table"]
    key_col = vt.get("key_column", f"{ad_table}_ID")
    disp_col = vt.get("display_column", "Name")

    b.open("AD_Reference", type="table")
    b.leaf("AD_Client_ID", 0)
    b.leaf("AD_Org_ID", 0)
    b.leaf("Name", vt["label"])
    b.leaf("Description", vt.get("description", ""))
    b.leaf("Help")
    b.leaf("ValidationType", "T")  # Table
    b.leaf("VFormat")
    b.leaf("EntityType", ENTITY_TYPE)
    b.leaf("IsActive", "Y")
    b.leaf("IsOrderByValue", "N")
    if vt.get("label_de"):
        emit_trl(b, "AD_Reference", vt["label_de"], vt.get("description", ""))
    b.leaf("AD_Reference_UU", ref_uu)
    b.close("AD_Reference")

    # AD_Ref_Table: koppelt das AD_Reference an eine konkrete Tabelle.
    # Wir liefern AD_Table_ID + AD_Key + AD_Display als UUID-Refs auf
    # AD_Column. Damit der Importer die Spalten findet, müssen die
    # AD_Column-Records dieser Tabelle bereits im 2Pack stehen — was bei
    # eigenen BXS_*-Tabellen automatisch der Fall ist, weil emit_table
    # die Spalten vor allem Window-/Reference-Kram emittiert.
    rt_uu = uuids.get("AD_Ref_Table", vt["name"])
    tbl_uu = uuids.get("AD_Table", ad_table)
    key_col_uu = uuids.get("AD_Column", _col_key(tbl_uu, key_col))
    disp_col_uu = uuids.get("AD_Column", _col_key(tbl_uu, disp_col))

    b.open("AD_Ref_Table", type="table")
    b.leaf("AD_Client_ID", 0)
    b.leaf("AD_Org_ID", 0)
    b.leaf("AD_Reference_ID", ref_uu, reference="uuid",
           **{"reference-key": "AD_Reference"})
    b.leaf("AD_Table_ID", tbl_uu, reference="uuid", **{"reference-key": "AD_Table"})
    b.leaf("AD_Key", key_col_uu, reference="uuid", **{"reference-key": "AD_Column"})
    b.leaf("AD_Display", disp_col_uu, reference="uuid",
           **{"reference-key": "AD_Column"})
    b.leaf("IsValueDisplayed", "N")
    b.leaf("IsActive", "Y")
    b.leaf("EntityType", ENTITY_TYPE)
    b.leaf("WhereClause", vt.get("where_clause", ""))
    b.leaf("OrderByClause", vt.get("order_by", ""))
    b.leaf("AD_Ref_Table_UU", rt_uu)
    b.close("AD_Ref_Table")


def emit_process_para(b: XmlBuilder, proc_value: str, proc_uu: str,
                      param: dict, seq: int, uuids: UuidStore) -> None:
    """AD_Process_Para — Eingabe-Parameter für einen AD_Process.

    YAML-Felder (mindestens unterstützt):
      column_name: Pflicht, sprich der Jasper-$P{<column_name>}
      name / name_de: Label DE/EN
      description / help (+ _de)
      reference: Schlüssel aus PROCESS_PARA_REFERENCE
                 („Table", „Yes-No", „List", „MultiSelectTable", …)
      reference_value: Name einer Validation-Table-Reference oder einer
                       List-Reference (UUID-Lookup über AD_Reference). Bei
                       Reference=Table/MultiSelectTable PFLICHT.
      is_mandatory: 'Y'/'N' oder bool; default 'N'
      is_multiselect: 'Y'/'N' oder bool; Convenience-Flag — wenn 'Y' und
                      reference='Table', wird intern auf
                      „MultiSelectTable" (200162) umgebogen.
      default_value: optional
      seq_no: optional, sonst der laufende Index
    """
    column_name = param["column_name"]
    para_key = f"{proc_value}.{column_name}"
    para_uu = uuids.get("AD_Process_Para", para_key)

    ref_name = param.get("reference", "String")
    # Multi-Select Convenience: „is_multiselect: Y" + „reference: Table"
    # bedeutet de facto „Chosen Multiple Selection Table" (200162).
    is_multi = _yn(param.get("is_multiselect", "N")) == "Y"
    if is_multi and ref_name == "Table":
        ref_name = "MultiSelectTable"
    if is_multi and ref_name == "List":
        ref_name = "MultiSelectList"
    if ref_name not in PROCESS_PARA_REFERENCE:
        raise ValueError(f"AD_Process_Para reference '{ref_name}' unbekannt "
                         f"(Param {para_key}). Erlaubt: "
                         f"{sorted(PROCESS_PARA_REFERENCE.keys())}")
    ref_id = PROCESS_PARA_REFERENCE[ref_name]

    b.open("AD_Process_Para", type="table")
    b.leaf("AD_Client_ID", 0)
    b.leaf("AD_Org_ID", 0)
    b.leaf("AD_Process_ID", proc_uu, reference="uuid",
           **{"reference-key": "AD_Process"})
    b.leaf("ColumnName", column_name)
    b.leaf("Name", param.get("name", column_name))
    b.leaf("Description", param.get("description", ""))
    b.leaf("Help", param.get("help", ""))
    b.leaf("EntityType", ENTITY_TYPE)
    b.leaf("IsActive", "Y")
    b.leaf("IsCentrallyMaintained", "Y")
    b.leaf("IsMandatory", _yn(param.get("is_mandatory", "N")))
    b.leaf("IsRange", "N")
    b.leaf("IsEncrypted", "N")
    b.leaf("IsAutocomplete", "N")
    b.leaf("AD_Reference_ID", ref_id, reference="id")
    rv_name = param.get("reference_value")
    if rv_name:
        b.leaf("AD_Reference_Value_ID",
               uuids.get("AD_Reference", rv_name),
               reference="uuid", **{"reference-key": "AD_Reference"})
    else:
        b.leaf("AD_Reference_Value_ID", reference="id")
    b.leaf("AD_Val_Rule_ID", reference="id")
    b.leaf("AD_Element_ID", reference="id")
    # FieldLength sinnvoll defaulten — YesNo=1, Multi-Select-Tables nehmen
    # eine breite Zeichenkette (CSV-IDs als Wert), Tables 22, sonst String.
    _len_alias = {
        "Yes-No": "YesNo",
        "MultiSelectTable": "Text",
        "MultiSelectList": "Text",
        "MultiSelectSearch": "Text",
    }.get(ref_name, ref_name)
    b.leaf("FieldLength", param.get("field_length", _default_length(
        _len_alias if _len_alias in DISPLAY_TYPE else "String")))
    b.leaf("DefaultValue", param.get("default_value", ""))
    b.leaf("SeqNo", param.get("seq_no", seq))
    b.leaf("VFormat")
    b.leaf("ValueMin")
    b.leaf("ValueMax")
    b.leaf("ReadOnlyLogic")
    b.leaf("DisplayLogic", param.get("display_logic", ""))
    b.leaf("MandatoryLogic")
    b.leaf("Placeholder")
    if param.get("name_de"):
        b.open("AD_Process_Para_Trl", type="translation")
        b.leaf("Name", param["name_de"])
        b.leaf("Description", param.get("description_de", param.get("description", "")))
        b.leaf("Help", param.get("help_de", param.get("help", "")))
        b.leaf("AD_Language", "de_DE")
        b.leaf("IsActive", "Y")
        b.leaf("IsTranslated", "Y")
        b.close("AD_Process_Para_Trl")
    b.leaf("AD_Process_Para_UU", para_uu)
    b.close("AD_Process_Para")


def _yn(v: Any) -> str:
    if isinstance(v, bool):
        return "Y" if v else "N"
    s = str(v).strip().upper()
    if s in ("Y", "YES", "TRUE", "1"):
        return "Y"
    return "N"


def emit_process(b: XmlBuilder, proc: dict, uuids: UuidStore) -> None:
    """AD_Process. Wenn `rule` gesetzt ist, wird Classname auf
    `@script:<rule_value>` gesetzt — iDempiere führt dann das verknüpfte
    AD_Rule aus (RuleType=S, EventType=P)."""
    proc_uu = uuids.get("AD_Process", proc["value"])
    classname = proc.get("classname", "")
    if proc.get("rule"):
        classname = "@script:" + proc["rule"]

    b.open("AD_Process", type="table")
    b.leaf("AD_Client_ID", 0)
    b.leaf("AD_Org_ID", 0)
    b.leaf("Value", proc["value"])
    b.leaf("Name", proc.get("name", proc["value"]))
    b.leaf("Description", proc.get("description", ""))
    b.leaf("Help", proc.get("help", ""))
    b.leaf("AccessLevel", str(proc.get("access_level", "3")))
    b.leaf("EntityType", ENTITY_TYPE)
    b.leaf("ProcedureName", "")
    b.leaf("Classname", classname)
    b.leaf("IsReport", "Y" if proc.get("is_report", False) else "N")
    if proc.get("jasper_report"):
        b.leaf("JasperReport", proc["jasper_report"])
    if proc.get("ad_table"):
        b.leaf("AD_Table_ID",
               uuids.get("AD_Table", proc["ad_table"]),
               reference="uuid", **{"reference-key": "AD_Table"})
    b.leaf("IsDirectPrint", "N")
    b.leaf("IsActive", "Y")
    b.leaf("IsBetaFunctionality", "N")
    b.leaf("IsServerProcess", "N")
    b.leaf("ShowHelp", "Y")
    b.leaf("CopyFromProcess", "N")
    b.leaf("AllowMultipleExecution", "Y")
    b.leaf("FontSize", 0)
    if proc.get("name_de"):
        emit_trl(b, "AD_Process", proc["name_de"],
                 proc.get("description_de", proc.get("description", "")),
                 proc.get("help_de", proc.get("help", "")))
    b.leaf("AD_Process_UU", proc_uu)
    b.close("AD_Process")

    # AD_Process_Para — Eingabeparameter (Multi-Select-Filter, Yes/No-Flag,
    # Datum, …). Reihenfolge im XML wahrt die SeqNo, falls in der YAML
    # nicht gesetzt; ProcessParaElementHandler defert sich selbst, falls
    # AD_Process noch nicht in DB ist — aber wir emittieren ohnehin direkt
    # nach dem Parent.
    for idx, param in enumerate(proc.get("process_params", []) or []):
        emit_process_para(b, proc["value"], proc_uu, param,
                          seq=(idx + 1) * 10, uuids=uuids)

    # Optional: Menü-Eintrag für den Prozess. Buttons in Tabs brauchen
    # keinen Menüeintrag (sie kennen den Process über AD_Column.AD_Process_ID).
    # Reports und stand-alone-Prozesse werden im Anlagenbuch-Knoten
    # eingehängt, wenn `menu: true` (oder explizite `menu`-Sektion) in der
    # YAML-Spec steht.
    menu_cfg = proc.get("menu")
    if menu_cfg:
        if menu_cfg is True:
            menu_cfg = {}
        action = "R" if proc.get("is_report") else "P"
        emit_menu(b, uuids,
                  menu_key=f"Process.{proc['value']}",
                  name=proc.get("name", proc["value"]),
                  name_de=proc.get("name_de"),
                  description=proc.get("description_de", proc.get("description", "")),
                  action=action,
                  target_table="AD_Process",
                  target_uu=proc_uu,
                  seq_no=menu_cfg.get("seq", 50),
                  **_menu_parent(menu_cfg.get("parent")))


# ---------------------------------------------------------------------------
# AD_PrintFormat — registriert einen Jasper-Report als „Print"-Eintrag,
# der vom Report-Toolbar-Knopf eines Tabs aufgerufen wird.


def emit_printformat(b: XmlBuilder, pf: dict, uuids: UuidStore) -> None:
    pf_uu = uuids.get("AD_PrintFormat", pf["name"])
    b.open("AD_PrintFormat", type="table")
    b.leaf("AD_Client_ID", 0)
    b.leaf("AD_Org_ID", 0)
    b.leaf("Name", pf["name"])
    b.leaf("Description", pf.get("description", ""))
    b.leaf("AD_Table_ID",
           uuids.get("AD_Table", pf["ad_table"]),
           reference="uuid", **{"reference-key": "AD_Table"})
    b.leaf("AD_PrintPaper_ID", pf.get("ad_printpaper_id", 100), reference="id")
    b.leaf("AD_PrintColor_ID", pf.get("ad_printcolor_id", 100), reference="id")
    b.leaf("AD_PrintFont_ID", pf.get("ad_printfont_id", 130), reference="id")
    b.leaf("IsActive", "Y")
    b.leaf("IsTableBased", "N")     # Y würde Spalten-Renderer erwarten; bei Jasper läuft alles im Process
    b.leaf("IsForm", "Y")            # Single-Record-Report (nicht Liste)
    b.leaf("IsStandardHeaderFooter", "Y")
    b.leaf("HeaderMargin", 36)
    b.leaf("FooterMargin", 36)
    b.leaf("IsDefault", "Y" if pf.get("is_default", False) else "N")
    b.leaf("JasperProcess_ID",
           uuids.get("AD_Process", pf["jasper_process"]),
           reference="uuid", **{"reference-key": "AD_Process"})
    if pf.get("name_de"):
        emit_trl(b, "AD_PrintFormat", pf["name_de"], pf.get("description_de", ""))
    b.leaf("AD_PrintFormat_UU", pf_uu)
    b.close("AD_PrintFormat")


# ---------------------------------------------------------------------------
# AD_Rule + AD_Table_ScriptValidator (ModelValidator-Skripte)


def emit_rule(b: XmlBuilder, rule: dict, uuids: UuidStore) -> None:
    """AD_Rule-Record (BeanShell oder JS) plus optional Verknüpfung an
    Tabellen via AD_Table_ScriptValidator. ModelValidator-Skripte (eventtype
    'M') feuern bei den eingetragenen TBN/TBC/… Events."""
    rule_uu = uuids.get("AD_Rule", rule["value"])

    b.open("AD_Rule", type="table")
    b.leaf("AD_Client_ID", 0)
    b.leaf("AD_Org_ID", 0)
    b.leaf("Value", rule["value"])
    b.leaf("Name", rule.get("name", rule["value"]))
    b.leaf("Description", rule.get("description", ""))
    b.leaf("Help", rule.get("help", ""))
    b.leaf("AccessLevel", str(rule.get("access_level", "3")))
    b.leaf("EntityType", ENTITY_TYPE)
    b.leaf("EventType", rule.get("event_type", "M"))   # M=ModelValidator, P=Process, C=Callout, S=SQLValidate
    b.leaf("RuleType", rule.get("rule_type", "S"))     # S=JSR223 (engine aus Value-Prefix engine:name), Q=SQL, R=JSR94
    b.leaf("IsActive", "Y")
    b.leaf("Script", rule.get("script", ""))
    b.leaf("AD_Rule_UU", rule_uu)
    b.close("AD_Rule")

    for tv in rule.get("table_validators", []):
        tv_key = f"{rule['value']}.{tv['table']}.{tv['event']}"
        tv_uu = uuids.get("AD_Table_ScriptValidator", tv_key)
        tbl_uu = uuids.get("AD_Table", tv["table"])

        b.open("AD_Table_ScriptValidator", type="table")
        b.leaf("AD_Client_ID", 0)
        b.leaf("AD_Org_ID", 0)
        b.leaf("AD_Rule_ID", rule_uu, reference="uuid", **{"reference-key": "AD_Rule"})
        b.leaf("AD_Table_ID", tbl_uu, reference="uuid", **{"reference-key": "AD_Table"})
        b.leaf("EventModelValidator", tv["event"])
        b.leaf("SeqNo", tv.get("seqno", 10))
        b.leaf("IsActive", "Y")
        b.leaf("AD_Table_ScriptValidator_UU", tv_uu)
        b.close("AD_Table_ScriptValidator")


# ---------------------------------------------------------------------------
# Initial-Daten
#
# Werden als generische PO-Records (<TableName type="table">…</TableName>)
# emittiert, NICHT als <SQLStatement>. Grund: SQLStatementElementHandler
# führt in startElement synchron auf der DB aus, während TableElementHandler
# alle AD_Table/AD_Column-Records deferred und erst in
# processDeferElements applied — bei einem Erstinstall existiert die
# Tabelle daher noch nicht, wenn SQL-Inserts laufen würden. Generic-PO-
# Records hingegen defert PackInHandler selbst (siehe
# GenericPOElementHandler.java:97-101), sodass die Initial-Daten erst
# eingespielt werden, nachdem Tabelle UND alle FK-Referenzen aufgelöst
# sind. Quelle: ~/iDempiere-development/docs/2pack-knowhow.md "Initial-
# Daten in neuen Tabellen — Generic-PO statt SQLStatement".


# FK-Spalten-Syntax in den YAML-Specs: `{ColName}_ID[{LookupCol}]: Wert`.
# Wert wird gegen `LookupCol` der Zieltabelle gematched.
_FK_COL_RE = re.compile(r"^(\w+)_ID\[(\w+)\]$")


# Well-known IDs von Core-Records, die in unseren Initial-Daten als FK-
# Referenz auftauchen können. PackIn nimmt offizielle IDs ≤
# MAX_OFFICIAL_ID (50000) direkt — keine Cross-Tenant-Übersetzung nötig.
# Quelle: Frische iDempiere-Installation (`SELECT c_uom_id, x12de355 FROM
# c_uom WHERE c_uom_id <= 50000`).
CORE_REFS_BY_KEY: dict[tuple[str, str, str], int] = {
    ("C_UOM", "X12DE355", "HR"):  101,  # Hour
    ("C_UOM", "X12DE355", "DA"):  102,  # Day
    ("C_UOM", "X12DE355", "MON"): 103,  # Month
    ("C_UOM", "X12DE355", "EA"):  100,  # Each
}


def _initial_row_uu_key(row: dict) -> Any:
    """Spalte, deren Wert die UUID-Identität einer Initial-Daten-Zeile
    bestimmt. Stabilität wichtig: damit `uuids.csv` denselben UUID-Key
    zwischen Builds wiederfindet. Reihenfolge: Value (BXS_AssetClass et
    al.), X12DE355 (C_UOM), Name (Fallback), sonst erstes Feld."""
    return row.get("Value") or row.get("X12DE355") or row.get("Name") or next(iter(row.values()))


def build_initial_uuid_index(initial: list, uuids: UuidStore) -> dict:
    """Pre-Pass: indiziert die UUIDs aller eigenen Initial-Daten-Zeilen
    unter ihren nicht-FK-Spaltenwerten, damit FK-Referenzen aus anderen
    Initial-Daten-Zeilen (`C_UOM_ID[X12DE355]: KME`) auf die richtige
    UUID auflösen. Schlüssel: (table, col, value). FK-Spalten und
    Bool-Werte werden übersprungen (nicht als Lookup-Ziel geeignet)."""
    idx: dict[tuple[str, str, str], str] = {}
    for item in initial:
        if item.get("raw_sql"):
            continue
        table = item["table"]
        for row in item["rows"]:
            rec_uu = uuids.get("Initial", f"{table}.{_initial_row_uu_key(row)}")
            for k, v in row.items():
                if _FK_COL_RE.match(k):
                    continue
                if not isinstance(v, str):
                    continue
                idx[(table, k, v)] = rec_uu
    return idx


def emit_initial_data(b: XmlBuilder, item: dict, uuids: UuidStore,
                      initial_uuid_index: dict) -> None:
    """Initial-Daten als generische PO-Records emittieren — PackIn
    deferred sie automatisch, bis Tabelle und alle FK-Refs aufgelöst sind.

    Spezialfall: `raw_sql`-Items bleiben als <SQLStatement> (für DDL-
    Migrationen wie CREATE VIEW, die nicht in das Generic-PO-Modell
    passen). Diese laufen synchron — bitte nur für Statements verwenden,
    die keine im selben Pack neu angelegten Tabellen referenzieren."""
    if item.get("raw_sql"):
        b.open("SQLStatement")
        b.leaf("DBType", "PostgreSQL")
        b.leaf("statement", item["raw_sql"])
        b.close("SQLStatement")
        return

    table = item["table"]
    uu_col = f"{table}_UU"

    for row in item["rows"]:
        rec_uu = uuids.get("Initial", f"{table}.{_initial_row_uu_key(row)}")

        # `trl_de` ist eine optionale Sub-Map mit deutscher Übersetzung.
        # Wird *nach* allen Datenspalten als nested `<{table}_Trl>` emittiert
        # (siehe emit_trl-Konvention: nested in den Parent-Record).
        trl_de = row.get("trl_de") or {}

        b.open(table, type="table")
        b.leaf(uu_col, rec_uu)
        b.leaf("AD_Client_ID", 0)
        b.leaf("AD_Org_ID", 0)
        b.leaf("IsActive", "Y")

        for k, v in row.items():
            if k == "trl_de":
                continue
            m = _FK_COL_RE.match(k)
            if m:
                ref_table, lookup_col = m.group(1), m.group(2)
                fk_col = f"{ref_table}_ID"
                hit_uu = initial_uuid_index.get((ref_table, lookup_col, v))
                if hit_uu is not None:
                    b.leaf(fk_col, hit_uu, reference="uuid",
                           **{"reference-key": ref_table})
                    continue
                core_id = CORE_REFS_BY_KEY.get((ref_table, lookup_col, v))
                if core_id is not None:
                    b.leaf(fk_col, core_id, reference="id")
                    continue
                raise SystemExit(
                    f"FK-Referenz nicht auflösbar: {table} → {fk_col} via "
                    f"{lookup_col}={v!r}. Eintrag in CORE_REFS_BY_KEY ergänzen "
                    f"oder Wert als Spalte einer eigenen Initial-Daten-Zeile aufnehmen."
                )
            else:
                if isinstance(v, bool):
                    b.leaf(k, "Y" if v else "N")
                else:
                    b.leaf(k, v)

        if trl_de:
            emit_trl(b, table,
                     name=trl_de.get("Name", ""),
                     description=trl_de.get("Description", ""),
                     help_text=trl_de.get("Help", ""),
                     language="de_DE")

        b.close(table)


def emit_role(b: XmlBuilder, role: dict, uuids: UuidStore) -> None:
    """AD_Role im System-Mandanten (AD_Client_ID=0) als Master-Rolle plus
    AD_Window_Access / AD_Process_Access / AD_Form_Access / AD_Workflow_Access.

    Tenants binden die Rolle per AD_Role_Included in ihre Login-Rolle ein
    (Beispiel: example/JakobBayenKG/bootstrap_roles.py). Cross-Tenant-
    Inclusion ist in iDempiere-Core nicht gesperrt; die Master-Rolle muss
    dafür ausschließlich Access auf System-Records (AD_Client_ID=0)
    halten — was bei einem reinen 2Pack-Lieferumfang automatisch der Fall
    ist.

    YAML-Felder:
      name:                  Rollen-Name (Pflicht, identisch zum uuids.csv-Key)
      description / _de:     Beschreibung (optional)
      user_level:            UserLevel-Code (3-Zeichen-Pattern aus
                             AD_Reference 226): " CO" Client+Org, " C "
                             Client, "  O" Org, "S  " System.
                             Default " CO".
      is_master_role:        bool, default True
      process_access:        Liste von Plugin-Process-Values (per UUID gemappt)
      process_access_core_id:Liste von Core-AD_Process_ID (≤ 50000)
      window_access:         Liste von AD_Window-Namen (per UUID gemappt)
      form_access:           Liste von AD_Form-Namen (optional)
      workflow_access:       Liste von AD_Workflow-Werten (optional)
    """
    role_uu = uuids.get("AD_Role", role["name"])

    b.open("AD_Role", type="table")
    b.leaf("AD_Client_ID", 0)
    b.leaf("AD_Org_ID", 0)
    b.leaf("Name", role["name"])
    b.leaf("Description", role.get("description", ""))
    # UserLevel ist ein 3-Zeichen-Pattern (AD_Reference 226): " CO",
    # " C ", "  O", "S  ". Aliase ohne Leerzeichen werden hier
    # auf das Pattern gemappt, damit YAML-Specs lesbar bleiben.
    _user_level_alias = {
        "CO": " CO", "C": " C ", "O": "  O", "S": "S  ",
    }
    ul_raw = role.get("user_level", "CO").strip()
    user_level = _user_level_alias.get(ul_raw, role.get("user_level", " CO"))
    b.leaf("UserLevel", user_level)
    b.leaf("IsMasterRole", "Y" if role.get("is_master_role", True) else "N")
    # Konservative Defaults: Master-Rolle vergibt nur „darf sehen" / „darf
    # ausführen", keine Daten-Reichweite. OrgAccess / All-Orgs etc. kommt
    # aus der Login-Rolle, die diese Master-Rolle inkludiert.
    #
    # IsManual=Y ist **zwingend**: bei IsManual=N feuert MRole.afterSave()
    # → updateAccessRecords() und legt für ALLE Windows/Processes/Forms
    # automatisch Access-Records gemäß UserLevel an. Unsere expliziten
    # Window_Access/Process_Access-Inserts kollidieren dann am
    # unique-Index (ad_window_id, ad_role_id) und der ganze Pack-Import
    # rollt zurück. Mit IsManual=Y überspringt updateAccessRecords das
    # Auto-Pflegen (return "-" gleich am Anfang) — wir kontrollieren die
    # Access-Liste vollständig über das 2Pack.
    b.leaf("IsManual", "Y")
    b.leaf("IsActive", "Y")
    b.leaf("IsShowAcct", "N")
    b.leaf("IsPersonalLock", "N")
    b.leaf("IsPersonalAccess", "N")
    b.leaf("IsCanExport", "Y")
    b.leaf("IsCanReport", "Y")
    b.leaf("IsCanApproveOwnDoc", "N")
    b.leaf("IsAccessAllOrgs", "N")
    b.leaf("IsChangeLog", "N")
    b.leaf("PreferenceType", "C")
    b.leaf("OverwritePriceLimit", "N")
    b.leaf("IsUseUserOrgAccess", "N")
    b.leaf("ConfirmQueryRecords", 0)
    b.leaf("MaxQueryRecords", 0)
    b.leaf("Allow_Info_Account", "N")
    b.leaf("Allow_Info_Asset", "N")
    b.leaf("Allow_Info_BPartner", "N")
    b.leaf("Allow_Info_CashJournal", "N")
    b.leaf("Allow_Info_InOut", "N")
    b.leaf("Allow_Info_Invoice", "N")
    b.leaf("Allow_Info_Order", "N")
    b.leaf("Allow_Info_Payment", "N")
    b.leaf("Allow_Info_Product", "N")
    b.leaf("Allow_Info_Resource", "N")
    b.leaf("Allow_Info_Schedule", "N")
    b.leaf("Allow_Info_MRP", "N")
    b.leaf("Allow_Info_CRP", "N")
    b.leaf("IsDiscountUptoLimitPrice", "N")
    b.leaf("IsDiscountAllowedOnTotal", "N")
    b.leaf("IsMenuAutoExpand", "N")
    b.leaf("IsAccessAdvanced", "N")
    b.leaf("IsClientAdministrator", "N")
    b.leaf("EntityType", ENTITY_TYPE)
    # AD_Role hat keine Trl-Tabelle (Name+Description sind nicht übersetzbar).
    b.leaf("AD_Role_UU", role_uu)

    # Access-Records — nested innerhalb von <AD_Role>, analog zum
    # Core-RoleElementHandler.create (Output-Pfad). PIPO-Importer
    # dispatcht Top-Level-Elemente per Tag; AD_Role_ID auf den Access-
    # Records verweist per UUID auf die soeben angelegte Rolle.
    # Access-Records brauchen jeweils ein eigenes <…_UU>, damit PIPO beim
    # Reimport via findPO den vorhandenen Record erkennt und UPDATE statt
    # INSERT macht — sonst kollidiert der unique-Index (ad_role_id,
    # ad_window_id) bei jedem zweiten Lauf. UUID-Key kombiniert
    # Rolle+Ziel, deterministisch über uuids.csv.
    role_name = role["name"]

    for win_name in role.get("window_access", []) or []:
        acc_uu = uuids.get("AD_Window_Access",
                           f"{role_name}.{win_name}")
        b.open("AD_Window_Access", type="table")
        b.leaf("AD_Client_ID", 0)
        b.leaf("AD_Org_ID", 0)
        b.leaf("IsActive", "Y")
        b.leaf("AD_Role_ID", role_uu, reference="uuid",
               **{"reference-key": "AD_Role"})
        b.leaf("AD_Window_ID",
               uuids.get("AD_Window", win_name),
               reference="uuid", **{"reference-key": "AD_Window"})
        b.leaf("IsReadWrite", "Y")
        b.leaf("AD_Window_Access_UU", acc_uu)
        b.close("AD_Window_Access")

    for proc_value in role.get("process_access", []) or []:
        acc_uu = uuids.get("AD_Process_Access",
                           f"{role_name}.{proc_value}")
        b.open("AD_Process_Access", type="table")
        b.leaf("AD_Client_ID", 0)
        b.leaf("AD_Org_ID", 0)
        b.leaf("IsActive", "Y")
        b.leaf("AD_Role_ID", role_uu, reference="uuid",
               **{"reference-key": "AD_Role"})
        b.leaf("AD_Process_ID",
               uuids.get("AD_Process", proc_value),
               reference="uuid", **{"reference-key": "AD_Process"})
        b.leaf("IsReadWrite", "Y")
        b.leaf("AD_Process_Access_UU", acc_uu)
        b.close("AD_Process_Access")

    for proc_id in role.get("process_access_core_id", []) or []:
        # Core-AD_Process_ID ≤ MAX_OFFICIAL_ID (50000) ist installations-
        # stabil; ID-Referenz reicht, kein UUID-Lookup nötig.
        acc_uu = uuids.get("AD_Process_Access",
                           f"{role_name}.core.{proc_id}")
        b.open("AD_Process_Access", type="table")
        b.leaf("AD_Client_ID", 0)
        b.leaf("AD_Org_ID", 0)
        b.leaf("IsActive", "Y")
        b.leaf("AD_Role_ID", role_uu, reference="uuid",
               **{"reference-key": "AD_Role"})
        b.leaf("AD_Process_ID", proc_id, reference="id")
        b.leaf("IsReadWrite", "Y")
        b.leaf("AD_Process_Access_UU", acc_uu)
        b.close("AD_Process_Access")

    for form_name in role.get("form_access", []) or []:
        acc_uu = uuids.get("AD_Form_Access",
                           f"{role_name}.{form_name}")
        b.open("AD_Form_Access", type="table")
        b.leaf("AD_Client_ID", 0)
        b.leaf("AD_Org_ID", 0)
        b.leaf("IsActive", "Y")
        b.leaf("AD_Role_ID", role_uu, reference="uuid",
               **{"reference-key": "AD_Role"})
        b.leaf("AD_Form_ID",
               uuids.get("AD_Form", form_name),
               reference="uuid", **{"reference-key": "AD_Form"})
        b.leaf("IsReadWrite", "Y")
        b.leaf("AD_Form_Access_UU", acc_uu)
        b.close("AD_Form_Access")

    for wf_value in role.get("workflow_access", []) or []:
        acc_uu = uuids.get("AD_Workflow_Access",
                           f"{role_name}.{wf_value}")
        b.open("AD_Workflow_Access", type="table")
        b.leaf("AD_Client_ID", 0)
        b.leaf("AD_Org_ID", 0)
        b.leaf("IsActive", "Y")
        b.leaf("AD_Role_ID", role_uu, reference="uuid",
               **{"reference-key": "AD_Role"})
        b.leaf("AD_Workflow_ID",
               uuids.get("AD_Workflow", wf_value),
               reference="uuid", **{"reference-key": "AD_Workflow"})
        b.leaf("IsReadWrite", "Y")
        b.leaf("AD_Workflow_Access_UU", acc_uu)
        b.close("AD_Workflow_Access")

    b.close("AD_Role")


def emit_sequence(b: XmlBuilder, seq: dict, uuids: UuidStore) -> None:
    """DocumentNo-Sequenz (kein TableID — die wird automatisch von
    MTable.afterSave erzeugt). Format: {Prefix}{lfd.Nr.}, optional mit
    DecimalPattern. Der ModelValidator pickt sich anhand des
    Sequence-Namens den passenden Generator."""
    seq_uu = uuids.get("AD_Sequence", seq["name"])
    b.open("AD_Sequence", type="table")
    b.leaf("AD_Client_ID", 0)
    b.leaf("AD_Org_ID", 0)
    b.leaf("Name", seq["name"])
    b.leaf("Description", seq.get("description", ""))
    # `isactive: false` in der Spec → IsActive='N'. Wir nutzen das, um die
    # automatisch von MTable.afterSave erzeugten Default-Tabellen-Sequenzen
    # (`DocumentNo_BXS_AssetItem`, `DocumentNo_BXS_WorkOrder`) nachträglich
    # zu deaktivieren — damit unsere TBN-Rule mit Prefix-Sequenzen
    # (FEH-/STA-/TER-/WAU-) als alleinige DocumentNo-Quelle greift.
    b.leaf("IsActive", "Y" if seq.get("isactive", True) else "N")
    b.leaf("IsTableID", "N")
    b.leaf("IsAutoSequence", "Y")
    b.leaf("IsAudited", "N")
    b.leaf("StartNo", 1)
    b.leaf("CurrentNext", 1)
    b.leaf("CurrentNextSys", 1)
    b.leaf("IncrementNo", 1)
    b.leaf("Prefix", seq.get("prefix", ""))
    b.leaf("Suffix", seq.get("suffix", ""))
    b.leaf("DecimalPattern", seq.get("decimal_pattern", ""))
    b.leaf("StartNewYear", "N")
    b.leaf("IsRestartSequenceEveryYear", "N")
    b.leaf("VFormat", seq.get("vformat", ""))
    b.leaf("AD_Sequence_UU", seq_uu)
    b.close("AD_Sequence")


# ---------------------------------------------------------------------------
# Hauptlauf


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--scripts", required=True, type=Path)
    p.add_argument("--reports", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    # part: welcher Teil des PackOut emittiert wird.
    #   schema = Schema + Workflow (alles ausser initial_data)
    #   data   = ausschliesslich initial_data
    # Beide Teile liefern eine vollstaendige <idempiere>-Datei und werden
    # als separate ZIPs deployed (Naming `*_01_schema.zip` / `*_02_data.zip`),
    # die der iDempiere-Folder-Apply alphabetisch hintereinander appliziert
    # — mit Commit zwischen den ZIPs. Notwendig, weil iDempiere-PIPO im
    # selben Lauf frisch angelegte Custom-Tabellen + Initial-Daten nicht
    # atomar verarbeiten kann (PO.checkRecordIDCrossTenant sieht die noch
    # uncommitteten AD_Column-Zeilen nicht und liefert leere keyColumns →
    # ArrayIndexOutOfBoundsException).
    # schema = Schema + Workflow (alles ausser initial_data + roles)
    # data   = ausschliesslich initial_data
    # role   = System-Master-Rolle + Window-/Process-/Form-/Workflow-Access.
    #          Eigener Bucket, damit die Access-Records erst nach den
    #          AD_Window/AD_Process-Records importiert werden (deren
    #          UUIDs müssen bereits committet sein, sonst defert PIPO).
    # all    = schema + data + role in EINER PackOut.xml (Reihenfolge
    #          schema→data→role). NUR für Plugins, deren initial_data NICHT
    #          in eigene, im selben Pack frisch angelegte Tabellen schreibt
    #          (z. B. aireports: SysConfig/Ref_List auf Core-Tabellen) — sonst
    #          schlägt die fehlende Commit-Grenze zwischen Schema und Daten zu
    #          (siehe Kommentar oben). Ein einzelnes ZIP genügt dann als
    #          META-INF/2Pack_<ver>.zip im OSGi-Bundle. ACHTUNG: Enthält die
    #          Spec eine NEUE AD_Role, darf sie NICHT mit ins Bundle-ZIP —
    #          der Bundle-Auto-2Pack kann keine neue Rolle anlegen (TBB009).
    #          Dann `--part all --exclude role` fürs Bundle + `--part role`
    #          für ein separates, per Folder-Weg eingespieltes Rollen-ZIP.
    p.add_argument("--part", choices=("schema", "data", "role", "all"),
                   required=True)
    # --exclude: einzelne Buckets aus dem gewählten --part herausnehmen
    # (Komma-Liste). Praktisch für „alles AUSSER Rolle" in EINEM Lauf:
    #   --part all --exclude role  →  schema + data, OHNE die AD_Role-Records.
    # Hintergrund: Eine NEUE AD_Role lässt sich nicht über den Bundle-Auto-2Pack
    # (Incremental2PackActivator, ZIP im JAR) anlegen — der Import läuft ohne
    # Login-Kontext, MUserRoles.beforeSave wirft NPE und rollt das GANZE Pack
    # zurück (Core-Bug TBB009). Die Rolle muss daher in ein SEPARATES ZIP, das
    # über den Folder-Weg (PackInApplicationActivator / RUN_ApplyPackInFromFolder)
    # eingespielt wird. Mit --exclude baut build.sh das rollenfreie Bundle-ZIP
    # und per `--part role` das Rollen-ZIP — aus EINER Spec-Quelle.
    p.add_argument("--exclude", default="",
                   help="Komma-Liste von Buckets (schema,data,role), die aus "
                        "--part herausfallen. Z. B. '--part all --exclude role'.")
    args = p.parse_args()

    repo_root = args.source.parent.parent
    uuids = UuidStore(repo_root / "uuids.csv")

    # Specs in Reihenfolge laden
    spec_files = sorted((args.source / "spec").glob("*.yaml"))
    package = None
    references: list = []
    validation_tables: list = []
    tables: list = []
    windows: list = []
    forms: list = []
    sequences: list = []
    additional_columns: list = []
    rules: list = []
    processes: list = []
    print_formats: list = []
    initial: list = []
    roles: list = []

    for f in spec_files:
        with f.open() as fh:
            data = yaml.safe_load(fh) or {}
        if "package" in data:
            package = data["package"]
        if "references" in data:
            references.extend(data["references"])
        if "validation_tables" in data:
            validation_tables.extend(data["validation_tables"])
        if "tables" in data:
            tables.extend(data["tables"])
        if "windows" in data:
            windows.extend(data["windows"])
        if "forms" in data:
            forms.extend(data["forms"])
        if "sequences" in data:
            sequences.extend(data["sequences"])
        if "additional_columns" in data:
            additional_columns.extend(data["additional_columns"])
        if "rules" in data:
            rules.extend(data["rules"])
        if "processes" in data:
            processes.extend(data["processes"])
        if "print_formats" in data:
            print_formats.extend(data["print_formats"])
        if "initial_data" in data:
            initial.extend(data["initial_data"])
        if "roles" in data:
            roles.extend(data["roles"])

    if not package:
        print("ERROR: kein package-Header gefunden", file=sys.stderr)
        return 1

    # EntityType global aus dem package-Header übernehmen — PFLICHTANGABE.
    # Kein stiller „U"-Default mehr: eigene Plugins müssen ihre Marke bewusst
    # setzen (i. d. R. BAY/BXS), sonst landeten Records versehentlich als
    # User-Customization (U) und vermischten sich mit echten Kunden-Anpassungen.
    # Alle emit_*-Funktionen lesen ENTITY_TYPE; eigene Marken (BAY/BXS)
    # ziehen zusätzlich einen AD_EntityType-Record nach (siehe unten).
    global ENTITY_TYPE
    ENTITY_TYPE = package.get("entity_type")
    if not ENTITY_TYPE:
        print("ERROR: package-Header ohne 'entity_type'. Das ist eine "
              "Pflichtangabe — die EntityType-Marke explizit setzen (eigene "
              "Plugins i. d. R. 'BAY' oder 'BXS'; Core-Typen 'U'/'D'/'C'/'EXT' "
              "nur bewusst). Frueher fiel das still auf 'U' zurueck.",
              file=sys.stderr)
        return 1
    if ENTITY_TYPE not in CORE_ENTITY_TYPES and ENTITY_TYPE not in ENTITY_TYPE_RECORDS:
        print(f"ERROR: entity_type '{ENTITY_TYPE}' ist weder ein Core-Typ "
              f"({sorted(CORE_ENTITY_TYPES)}) noch in ENTITY_TYPE_RECORDS "
              f"hinterlegt. Feste UUID in ENTITY_TYPE_RECORDS ergänzen, sonst "
              f"bricht die FK auf der Ziel-DB.", file=sys.stderr)
        return 1

    # Menü-Wurzel aus dem package-Header (`menu_root:`) übernehmen. Ohne
    # Sektion bleiben die Defaults (summary-Modus, Knoten „Anlagenbuch") —
    # damit Anlagenbuch byte-gleich bleibt.
    mr = package.get("menu_root") or {}
    global MENU_ROOT_MODE, MENU_ROOT_KEY, MENU_ROOT_NAME, MENU_ROOT_NAME_DE
    global MENU_ROOT_DESC, MENU_ROOT_SEQNO
    MENU_ROOT_MODE = mr.get("mode", MENU_ROOT_MODE)
    if MENU_ROOT_MODE not in ("summary", "root"):
        print(f"ERROR: menu_root.mode '{MENU_ROOT_MODE}' unbekannt "
              f"(erlaubt: summary, root).", file=sys.stderr)
        return 1
    MENU_ROOT_KEY = mr.get("key", MENU_ROOT_KEY)
    MENU_ROOT_NAME = mr.get("name", MENU_ROOT_NAME)
    MENU_ROOT_NAME_DE = mr.get("name_de", mr.get("name", MENU_ROOT_NAME_DE))
    MENU_ROOT_DESC = mr.get("description", MENU_ROOT_DESC)
    MENU_ROOT_SEQNO = mr.get("seq", MENU_ROOT_SEQNO)

    tables_by_name = {t["name"]: t for t in tables}

    # Additional columns in die Tabellen-Spec mergen, damit emit_window
    # auch für diese Spalten AD_Field-Records erzeugt (sonst hätten sie
    # zwar AD_Column, aber wären in keinem Tab sichtbar — gerade für virtuelle
    # ColumnSQL-Spalten wie LastMeterReading wäre das fatal).
    for ac in additional_columns:
        target = tables_by_name.get(ac["table"])
        if target is not None:
            target.setdefault("columns", []).extend(ac["columns"])

    # XML aufbauen
    out = ['<?xml version="1.0" encoding="UTF-8"?>']
    attrs = (
        f'Name="{package["name"]}" Version="{package["version"]}" '
        f'idempiereVersion="{package["idempiere_version"]}" '
        f'Description="{esc(package["description"])}" '
        f'Author="{esc(package["author"])}" AuthorEmail="{package["author_email"]}" '
        f'CreatedDate="{NOW}" UpdatedDate="{NOW}" PackOutVersion="100" '
        f'UpdateDictionary="false" '
        f'AD_Client_UU="11000000-0000-1000-8000-000000000000" '
        f'Client="0-System-System"'
    )
    out.append(f"<idempiere {attrs}>")

    b = XmlBuilder()
    b.indent = 1
    # Welche Buckets in diese Datei kommen. "all" bündelt alle drei in
    # schema→data→role-Reihenfolge; sonst genau der eine gewählte Part.
    # --exclude nimmt anschließend einzelne Buckets wieder heraus
    # (z. B. `--part all --exclude role` → schema+data ohne Rolle).
    excluded = {x.strip() for x in args.exclude.split(",") if x.strip()}
    bad = excluded - {"schema", "data", "role"}
    if bad:
        print(f"ERROR: --exclude kennt nur schema/data/role, nicht {sorted(bad)}",
              file=sys.stderr)
        return 1
    parts_to_emit = ({"schema", "data", "role"} if args.part == "all"
                     else {args.part}) - excluded
    if not parts_to_emit:
        print(f"ERROR: --part {args.part} --exclude {args.exclude} lässt nichts "
              f"zu emittieren übrig.", file=sys.stderr)
        return 1
    if "schema" in parts_to_emit:
        # Eigene EntityType-Marke (BAY/BXS) als ALLERERSTES Element — alle
        # folgenden AD_*-Records referenzieren sie per FK. Core-Typen
        # (U/D/C/EXT) brauchen keinen Record.
        if ENTITY_TYPE in ENTITY_TYPE_RECORDS:
            emit_entitytype(b, ENTITY_TYPE)
        for ref in references:
            emit_reference(b, ref, uuids)
        for tbl in tables:
            emit_table(b, tbl, uuids)
        # Validation-Table-Referenzen (AD_Reference ValidationType='T' + AD_Ref_Table)
        # — müssen NACH den Tabellen kommen, weil AD_Ref_Table per UUID auf
        # AD_Table und AD_Column (Key/Display) verweist.
        for vt in validation_tables:
            emit_validation_table(b, vt, uuids)
    # Additional columns wurden oben in tables_by_name gemerged und damit
    # NOTE: dead loop (`if False`) — bleibt aus historischen Gründen stehen.
    # bereits von emit_table emittiert. Der hier folgende Loop ist nur noch
    # für Spalten relevant, die auf eine Tabelle verweisen, die NICHT als
    # tables[..]-Spec im 2Pack steht (z.B. Erweiterungen auf Core-Tabellen).
    for ac in additional_columns if False else []:
        tbl_uu = uuids.get("AD_Table", ac["table"])
        for c in ac["columns"]:
            # AD_Element für die neue Spalte (BXS_-prefix oder ähnlich)
            if c["name"] not in CORE_ELEMENTS:
                emit_element(b, c["name"],
                             c.get("label", c["name"].replace("_", " ")),
                             c.get("label_de", ""),
                             c.get("description", ""),
                             c.get("help", ""),
                             uuids)
            elem_args: dict[str, Any] = {}
            if c["name"] in CORE_ELEMENTS:
                elem_args["element_id"] = CORE_ELEMENTS[c["name"]]
            else:
                elem_args["element_uuid"] = uuids.get("AD_Element", c["name"])
            if c.get("ref_value"):
                elem_args["ref_value_uuid"] = uuids.get("AD_Reference", c["ref_value"])
            if c.get("ref_value_id"):
                elem_args["ref_value_id"] = c["ref_value_id"]
            emit_column(b, tbl_uu, 1000,  # SeqNo egal, AD-Records werden nicht über SeqNo sortiert
                        dict(column_name=c["name"],
                             label=c.get("label", c["name"]),
                             reference=c["type"],
                             ref_table=c.get("ref"),
                             mandatory=c.get("mandatory", False),
                             updateable=c.get("updateable", True),
                             is_parent=c.get("is_parent", False),
                             length=c.get("length", _default_length(c["type"])),
                             default=c.get("default", ""),
                             help_text=c.get("help", ""),
                             description=c.get("description", ""),
                             is_identifier=False,
                             seq_no_identifier=0,
                             **elem_args),
                        uuids)
    if "schema" in parts_to_emit:
        for seq in sequences:
            emit_sequence(b, seq, uuids)
        # Summary-Menü-Wurzel zuerst, damit Process-/Window-/Form-Menüs als
        # Kinder darauf referenzieren können — der MenuElementHandler
        # verarbeitet AD_Menu-Records in XML-Reihenfolge und braucht den
        # Parent bereits in der DB, bevor Kinder ihn via UUID auflösen.
        # Im „root"-Modus entfällt der Knoten; die Kinder hängen direkt
        # unter dem DB-Menü-Root (Parent_ID=0).
        if MENU_ROOT_MODE != "root":
            emit_menu_root(b, uuids)
        # Processes vor Windows, damit Button-Spalten in emit_window auf
        # bereits gepoolte AD_Process-UUIDs verweisen können.
        for proc in processes:
            emit_process(b, proc, uuids)
        for win in windows:
            emit_window(b, win, tables_by_name, uuids)
        # Forms nach den Windows — beide hängen Menüs unter den
        # Anlagenbuch-Knoten, der bereits emittiert ist.
        for form in forms:
            emit_form(b, form, uuids)
        # primary_window-Verkabelung an AD_Table nachreichen — siehe
        # emit_table_primary_window-Docstring.
        for tbl in tables:
            emit_table_primary_window(b, tbl, uuids)
        for rule in rules:
            emit_rule(b, rule, uuids)
        for pf in print_formats:
            emit_printformat(b, pf, uuids)
    if "data" in parts_to_emit:
        # Initial-Daten brauchen UUID-Auflösung gegen die im Schema-Pack
        # angelegten Records (per AD_<Tabelle>_UU). uuids.csv ist die
        # gemeinsame Quelle — beide Teile lesen denselben Store.
        initial_uuid_index = build_initial_uuid_index(initial, uuids)
        for init in initial:
            emit_initial_data(b, init, uuids, initial_uuid_index)
    if "role" in parts_to_emit:
        # System-Master-Rolle + Window-/Process-/Form-/Workflow-Access.
        # Läuft erst nach Schema + Daten, damit alle referenzierten
        # AD_Window/AD_Process-Records committet vorliegen.
        for role in roles:
            emit_role(b, role, uuids)

    out.append(b.render().rstrip())
    out.append("</idempiere>")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(out) + "\n", encoding="utf-8")
    uuids.save()

    _exc = f" exclude={args.exclude}" if excluded else ""
    print(f"Wrote {args.out}  [part={args.part}{_exc} -> {sorted(parts_to_emit)}]")
    if "schema" in parts_to_emit:
        print(f"  refs={len(references)} tables={len(tables)} "
              f"sequences={len(sequences)} windows={len(windows)} "
              f"forms={len(forms)} processes={len(processes)} rules={len(rules)} "
              f"print_formats={len(print_formats)}")
    if "data" in parts_to_emit:
        print(f"  initial-blocks={len(initial)}")
    if "role" in parts_to_emit:
        print(f"  roles={len(roles)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
