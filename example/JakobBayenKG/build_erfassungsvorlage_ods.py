#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Erzeugt eine ODS-Erfassungsvorlage für die JBKG-Disponentin.

Zwei Blätter:
  1. „Stammdaten (Aktenordner)" — Werte aus den Wagenpapieren.
  2. „Erstaufnahme (am Fahrzeug)" — Werte, die man draußen am Fahrzeug
     erfasst (Zählerstand, Sichtprüfung, Mängel).

Die Fahrzeugliste wird aus der iDempiere-Testinstallation (DB `freibier`,
Port 15432, Resource-Typen LKW + Gerät) gezogen und in beiden Blättern
in den Schlüsselspalten vorausgefüllt. Spalten ohne Wert sind von der
Disponentin auszufüllen.

Output: dieselbe Datei wie das Script-Verzeichnis +
`Erfassungsvorlage_Anlagenbuch.ods`.
"""
from __future__ import annotations
import os
import subprocess
from pathlib import Path

from odf.opendocument import OpenDocumentSpreadsheet
from odf.style import (
    Style, TableColumnProperties, TableCellProperties,
    TextProperties, ParagraphProperties,
)
from odf.table import Table, TableColumn, TableRow, TableCell
from odf.text import P


# ---------------------------------------------------------------------------
# Fahrzeugliste aus testinstallation/freibier laden
# ---------------------------------------------------------------------------

def fetch_fleet() -> list[tuple[str, str, str, str]]:
    """Liefert (Klasse, KFZ-Kennzeichen, Bezeichnung, Beschreibung)."""
    sql = (
        "SELECT rt.value AS klasse, r.value, r.name, COALESCE(r.description,'') "
        "FROM S_Resource r "
        "JOIN S_ResourceType rt ON rt.S_ResourceType_ID = r.S_ResourceType_ID "
        "WHERE rt.value IN ('LKW','Gerät') AND r.isactive='Y' "
        "ORDER BY rt.value, r.value;"
    )
    env = os.environ.copy(); env['PGPASSWORD'] = 'adempiere'
    out = subprocess.check_output(
        ['psql', '-h', 'localhost', '-p', '15432', '-U', 'adempiere',
         '-d', 'freibier', '-tA', '-F', '\t', '-c', sql],
        env=env, text=True,
    )
    rows: list[tuple[str, str, str, str]] = []
    for line in out.strip().splitlines():
        parts = line.split('\t')
        if len(parts) == 4:
            rows.append(tuple(parts))  # type: ignore[arg-type]
    return rows


# ---------------------------------------------------------------------------
# ODS-Styles
# ---------------------------------------------------------------------------

def build_doc() -> OpenDocumentSpreadsheet:
    doc = OpenDocumentSpreadsheet()

    # Titel oberhalb der Tabelle
    s_title = Style(name="Title", family="table-cell")
    s_title.addElement(TextProperties(fontsize="14pt", fontweight="bold",
                                       color="#1F2F50"))
    doc.automaticstyles.addElement(s_title)

    s_intro = Style(name="Intro", family="table-cell")
    s_intro.addElement(TextProperties(fontsize="9pt", color="#444444"))
    s_intro.addElement(ParagraphProperties(marginbottom="3mm"))
    doc.automaticstyles.addElement(s_intro)

    s_section = Style(name="Section", family="table-cell")
    s_section.addElement(TextProperties(fontsize="10pt", fontweight="bold",
                                         color="#FFFFFF"))
    s_section.addElement(TableCellProperties(backgroundcolor="#1F2F50",
                                              paddingleft="2mm",
                                              paddingright="2mm",
                                              paddingtop="1mm",
                                              paddingbottom="1mm"))
    doc.automaticstyles.addElement(s_section)

    s_header = Style(name="ColHeader", family="table-cell")
    s_header.addElement(TextProperties(fontsize="9pt", fontweight="bold",
                                        color="#FFFFFF"))
    s_header.addElement(TableCellProperties(backgroundcolor="#1F2F50",
                                             paddingleft="2mm",
                                             paddingright="2mm",
                                             paddingtop="1mm",
                                             paddingbottom="1mm",
                                             borderbottom="0.5pt solid #C0C0C0"))
    doc.automaticstyles.addElement(s_header)

    s_pref = Style(name="Prefilled", family="table-cell")
    s_pref.addElement(TextProperties(fontsize="10pt", fontweight="bold"))
    s_pref.addElement(TableCellProperties(backgroundcolor="#F4F4F0",
                                           paddingleft="2mm",
                                           paddingright="2mm",
                                           paddingtop="1mm",
                                           paddingbottom="1mm",
                                           borderright="0.5pt solid #C0C0C0",
                                           borderbottom="0.5pt solid #E0E0E0"))
    doc.automaticstyles.addElement(s_pref)

    s_empty = Style(name="Empty", family="table-cell")
    s_empty.addElement(TableCellProperties(backgroundcolor="#FFFFFF",
                                            paddingleft="2mm",
                                            paddingright="2mm",
                                            paddingtop="1mm",
                                            paddingbottom="1mm",
                                            borderright="0.5pt solid #E0E0E0",
                                            borderbottom="0.5pt solid #E0E0E0"))
    doc.automaticstyles.addElement(s_empty)

    s_help = Style(name="Help", family="table-cell")
    s_help.addElement(TextProperties(fontsize="8pt", color="#888888",
                                      fontstyle="italic"))
    s_help.addElement(TableCellProperties(paddingleft="2mm",
                                           paddingright="2mm",
                                           paddingtop="1mm",
                                           paddingbottom="1mm"))
    doc.automaticstyles.addElement(s_help)

    # Spaltenbreiten
    for name, width in (('ColNarrow', '20mm'), ('ColMed', '35mm'),
                        ('ColWide', '55mm'), ('ColXWide', '70mm')):
        s = Style(name=name, family="table-column")
        s.addElement(TableColumnProperties(columnwidth=width))
        doc.automaticstyles.addElement(s)

    return doc


def cell(value: str | None, style_name: str = "Empty") -> TableCell:
    c = TableCell(stylename=style_name, valuetype="string")
    c.addElement(P(text=(value or '')))
    return c


def add_intro(table: Table, title: str, intro: str) -> None:
    row = TableRow(); row.addElement(cell(title, "Title")); table.addElement(row)
    row = TableRow(); row.addElement(cell(intro, "Intro")); table.addElement(row)
    table.addElement(TableRow())  # Leerzeile


def header_row(values: list[str]) -> TableRow:
    row = TableRow()
    for v in values:
        row.addElement(cell(v, "ColHeader"))
    return row


def help_row(values: list[str]) -> TableRow:
    row = TableRow()
    for v in values:
        row.addElement(cell(v, "Help"))
    return row


# ---------------------------------------------------------------------------
# Build sheets
# ---------------------------------------------------------------------------

def build_stammdaten_sheet(doc: OpenDocumentSpreadsheet,
                            fleet: list[tuple[str, str, str, str]]) -> None:
    t = Table(name="Stammdaten (Aktenordner)")

    # Spaltenbreiten: 11 Spalten
    widths = ['ColMed', 'ColMed', 'ColXWide',  # Klasse, KFZ, Bezeichnung
              'ColMed', 'ColMed', 'ColMed',    # Hersteller, Modell, Baujahr
              'ColWide',                       # FIN
              'ColMed',                        # Erstzulassung
              'ColMed',                        # Standort
              'ColMed',                        # Stammnutzer
              'ColXWide']                      # Bemerkung
    for w in widths:
        t.addElement(TableColumn(stylename=w))

    add_intro(t,
        "Stammdaten — Erfassung mit Wagenpapieren",
        "Bitte mit dem Aktenordner der Fahrzeuge ausfüllen. "
        "Die grau hinterlegten Spalten (Klasse, Kennzeichen, Bezeichnung) "
        "sind vorausgefüllt. Bitte die weißen Spalten ergänzen — bei Fragen "
        'leer lassen. Die zweite Seite ("Erstaufnahme") wird draußen am '
        "Fahrzeug ausgefüllt; gleiche Reihenfolge der Zeilen.",
    )

    # Spaltenüberschriften
    t.addElement(header_row([
        "Klasse",
        "Kennzeichen",
        "Bezeichnung",
        "Hersteller",
        "Modell",
        "Baujahr",
        "Fahrgestellnr. (FIN)",
        "Erstzulassung",
        "Standort",
        "Stammnutzer",
        "Bemerkung Aktenordner",
    ]))
    t.addElement(help_row([
        "LKW / Gerät",
        "amtl. Kennz.",
        "wie im Anlagenbuch",
        "z.B. MAN, VW, Mercedes",
        "Typ-Bezeichnung",
        "JJJJ",
        "17-stellige VIN aus Fahrzeugschein",
        "TT.MM.JJJJ",
        "Hof, Halle, Standort",
        "Name des Hauptfahrers",
        "Auffälligkeiten in den Papieren",
    ]))

    for klasse, value, name, description in fleet:
        row = TableRow()
        row.addElement(cell(klasse, "Prefilled"))
        row.addElement(cell(value, "Prefilled"))
        row.addElement(cell(name, "Prefilled"))
        for _ in range(8):
            row.addElement(cell("", "Empty"))
        # Beschreibung aus S_Resource als Bemerkung-Vorschlag
        if description:
            row.appendChild(cell("[Resource: " + description + "]", "Help"))
        t.addElement(row)

    doc.spreadsheet.addElement(t)


def build_erstaufnahme_sheet(doc: OpenDocumentSpreadsheet,
                              fleet: list[tuple[str, str, str, str]]) -> None:
    t = Table(name="Erstaufnahme (am Fahrzeug)")

    widths = ['ColMed', 'ColMed', 'ColXWide',
              'ColMed', 'ColMed',
              'ColMed',
              'ColXWide', 'ColXWide']
    for w in widths:
        t.addElement(TableColumn(stylename=w))

    add_intro(t,
        "Erstaufnahme — Sichtprüfung am Fahrzeug",
        "Diese Seite ausdrucken und mit der Anlage rausgehen. "
        "Zählerstand ablesen, Reifen / Karosserie / Innenraum sichten, "
        "auffällige Mängel notieren. Datum nicht vergessen. Pro Anlage "
        "eine Zeile — die Reihenfolge entspricht der ersten Seite.",
    )

    t.addElement(header_row([
        "Klasse",
        "Kennzeichen",
        "Bezeichnung",
        "Zählerstand",
        "Einheit",
        "Datum",
        "Allgemeinzustand",
        "Sichtbare Mängel / Bemerkungen",
    ]))
    t.addElement(help_row([
        "vorausgefüllt",
        "vorausgefüllt",
        "vorausgefüllt",
        "Zahl ohne Einheit",
        "km / h",
        "TT.MM.JJJJ",
        "gut / Mängel / kritisch",
        "Stichwortartig — alles, was beim nächsten Werkstattbesuch ran muss",
    ]))

    for klasse, value, name, _description in fleet:
        row = TableRow()
        row.addElement(cell(klasse, "Prefilled"))
        row.addElement(cell(value, "Prefilled"))
        row.addElement(cell(name, "Prefilled"))
        for _ in range(5):
            row.addElement(cell("", "Empty"))
        t.addElement(row)

    doc.spreadsheet.addElement(t)


def main() -> None:
    fleet = fetch_fleet()
    if not fleet:
        raise SystemExit("Keine Fahrzeuge aus S_Resource gefunden — DB-Connect prüfen.")

    doc = build_doc()
    build_stammdaten_sheet(doc, fleet)
    build_erstaufnahme_sheet(doc, fleet)

    out = Path(__file__).parent / "Erfassungsvorlage_Anlagenbuch.ods"
    doc.save(str(out))
    print(f"Geschrieben: {out} ({len(fleet)} Anlagen)")


if __name__ == "__main__":
    main()
