#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Vendored from idempiere-ods-import (AGPL-3.0-or-later).
# Upstream: https://github.com/tbayen/idempiere-ods-import
# Sync state: 71cdac3 + lokale uncommittete Upstream-Aenderungen
#   (Spalten-Padding fuer SuperCsv, language-Param, staging_ssh fuer
#   Remote-iDempiere-Server). Re-vendort 2026-06-17.
# Upstream-Fixes: tools/import-ods.py mit der upstream-Version
# ueberschreiben und Sync state oben aktualisieren.
"""ODS-Multi-Sheet-Importer für iDempiere.

Liest eine ODS-Datei mit einem Konfig-Sheet und mehreren Datensheets und
importiert jeden Datensheet per `ImportCSVProcess` über die iDempiere REST API.
"""
from __future__ import annotations

import argparse
import base64
import csv
import io
import os
import re
import shlex
import subprocess
import sys
import time
import urllib3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import requests
import yaml
from odf.opendocument import load as ods_load
from odf.table import Table, TableCell, TableRow
from odf.text import P

THIS_DIR = Path(__file__).resolve().parent
DEFAULT_PROFILES = THIS_DIR / "profiles.yaml"
LOCAL_PROFILES = THIS_DIR / "profiles.local.yaml"
LOG_DIR = THIS_DIR / "logs"

CONFIG_SHEET_NAME = "_config"
CONFIG_REQUIRED = ("Sheet", "Window", "Tab")
CONFIG_OPTIONAL = ("ImportMode", "Skip")


# ──────────────────────────────────────────────────────────────────────────────
# Profile
# ──────────────────────────────────────────────────────────────────────────────

def deep_merge(base: dict, overlay: dict) -> dict:
    """Recursive merge: overlay wins on scalars, dicts merge."""
    out = dict(base)
    for k, v in overlay.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_profiles() -> dict:
    if not DEFAULT_PROFILES.exists():
        sys.exit(f"profiles.yaml fehlt: {DEFAULT_PROFILES}")
    data = yaml.safe_load(DEFAULT_PROFILES.read_text()) or {}
    if LOCAL_PROFILES.exists():
        local = yaml.safe_load(LOCAL_PROFILES.read_text()) or {}
        data = deep_merge(data, local)
    return data


def select_profile(profiles_data: dict, name: str | None) -> tuple[str, dict]:
    profiles = profiles_data.get("profiles") or {}
    if not profiles:
        sys.exit("Keine Profile gefunden (weder in profiles.yaml noch profiles.local.yaml).")
    name = name or profiles_data.get("default")
    if not name:
        sys.exit("Kein --profile angegeben und kein 'default' in der YAML.")
    if name not in profiles:
        sys.exit(f"Profil '{name}' nicht gefunden. Verfügbar: {', '.join(sorted(profiles))}")
    return name, profiles[name]


# ──────────────────────────────────────────────────────────────────────────────
# ODS-Reader
# ──────────────────────────────────────────────────────────────────────────────

def _cell_text(cell: TableCell) -> str:
    """Konkateniert alle <text:p>-Inhalte der Zelle als String."""
    parts: list[str] = []
    for p in cell.getElementsByType(P):
        # str(p) liefert den Text aller Kinder rekursiv.
        parts.append(str(p))
    return "\n".join(parts).strip()


def _row_values(row: TableRow, min_len: int = 0) -> list[str]:
    """Werte einer Zeile, expandiert numbercolumnsrepeated. `min_len`
    sorgt dafür, dass die Zeile mindestens so viele Spalten hat wie der
    Header — wichtig, wenn die Master-Zeile zwar 12 Header-Spalten hat,
    aber die letzten Subtab-Detail-Spalten leer sind: SuperCsv im
    ImportCSVProcess akzeptiert keine Zeilen mit weniger Spalten als der
    Header. Trailing-Leerzellen jenseits min_len werden entfernt."""
    values: list[str] = []
    for cell in row.getElementsByType(TableCell):
        text = _cell_text(cell)
        repeated = cell.getAttribute("numbercolumnsrepeated")
        n = int(repeated) if repeated else 1
        # Sehr große Repeats am Zeilenende sind ODS-typisch (leere Zellen
        # bis Spalte 1024). Nicht expandieren, wenn alles leer ist.
        if n > 50 and text == "":
            break
        values.extend([text] * n)
    # Trailing-Leerzellen entfernen — aber Header-Länge behalten.
    while values and values[-1] == "" and len(values) > min_len:
        values.pop()
    # Bei zu kurzer Zeile mit "" auf min_len padden.
    while len(values) < min_len:
        values.append("")
    return values


def read_ods(path: Path) -> dict[str, list[list[str]]]:
    """Liest alle Sheets als Listen von Zeilen-Listen. Erste Zeile pro
    Sheet ist die Header-Länge — Folgezeilen werden auf diese Länge
    gepaddet, damit nachgelagertes SuperCsv im ImportCSVProcess nicht an
    Master-only-Zeilen mit leeren Subtab-Spalten am Ende scheitert."""
    doc = ods_load(str(path))
    sheets: dict[str, list[list[str]]] = {}
    for table in doc.spreadsheet.getElementsByType(Table):
        name = table.getAttribute("name")
        rows: list[list[str]] = []
        header_len = 0
        for i, row in enumerate(table.getElementsByType(TableRow)):
            values = _row_values(row, min_len=header_len)
            if i == 0:
                header_len = len(values)
            rows.append(values)
        # Trailing leere Zeilen abschneiden
        while rows and not any(c.strip() for c in rows[-1]):
            rows.pop()
        sheets[name] = rows
    return sheets


@dataclass
class ConfigEntry:
    sheet: str
    window: str
    tab: str
    import_mode: str = "M"
    skip: bool = False


def parse_config_sheet(rows: list[list[str]]) -> list[ConfigEntry]:
    if not rows:
        sys.exit(f"Konfig-Sheet '{CONFIG_SHEET_NAME}' ist leer.")
    header = [c.strip() for c in rows[0]]
    for col in CONFIG_REQUIRED:
        if col not in header:
            sys.exit(f"Konfig-Sheet: Spalte '{col}' fehlt. Header: {header}")
    idx = {col: header.index(col) for col in header}

    def get(row: list[str], col: str, default: str = "") -> str:
        i = idx.get(col)
        if i is None or i >= len(row):
            return default
        return row[i].strip()

    entries: list[ConfigEntry] = []
    for row in rows[1:]:
        if not any(c.strip() for c in row):
            continue
        sheet = get(row, "Sheet")
        if not sheet:
            continue
        entry = ConfigEntry(
            sheet=sheet,
            window=get(row, "Window"),
            tab=get(row, "Tab"),
            import_mode=(get(row, "ImportMode") or "M").upper(),
            skip=get(row, "Skip").upper() == "Y",
        )
        if entry.import_mode not in ("I", "U", "M"):
            sys.exit(f"Konfig-Sheet, Sheet '{sheet}': ImportMode '{entry.import_mode}' ungültig (erlaubt: I/U/M).")
        if not entry.window or not entry.tab:
            sys.exit(f"Konfig-Sheet, Sheet '{sheet}': Window oder Tab fehlt.")
        entries.append(entry)
    return entries


def sheet_to_csv(rows: list[list[str]]) -> str:
    """Sheet-Zeilen → CSV-String (UTF-8, Komma, doppelte Anführungszeichen)."""
    buf = io.StringIO()
    w = csv.writer(buf, quoting=csv.QUOTE_MINIMAL)
    for row in rows:
        w.writerow(row)
    return buf.getvalue()


# ──────────────────────────────────────────────────────────────────────────────
# REST-Client
# ──────────────────────────────────────────────────────────────────────────────

class RestError(Exception):
    pass


class IDempiereClient:
    def __init__(self, profile: dict):
        self.base_url = profile["base_url"].rstrip("/")
        self.profile = profile
        self.session = requests.Session()
        if not profile.get("verify_tls", True):
            self.session.verify = False
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.token: str | None = None

    def login(self) -> None:
        # `language` einhängen — Default en_US. Ohne den Parameter zieht der
        # Endpoint die Sprache aus AD_Preference/AD_Client (oft de_DE), und
        # der englische Log-Marker "Inserted" wird in iDempiere zu
        # "Eingefügt", was unsere Erfolgs-Erkennung weiter unten kippt.
        payload = {
            "userName": self.profile["username"],
            "password": self.profile["password"],
            "parameters": {
                "clientId": int(self.profile["client_id"]),
                "roleId": int(self.profile["role_id"]),
                "organizationId": int(self.profile["org_id"]),
                "warehouseId": int(self.profile.get("warehouse_id", 0)),
                "language": self.profile.get("language", "en_US"),
            },
        }
        r = self.session.post(f"{self.base_url}/api/v1/auth/tokens", json=payload, timeout=30)
        if r.status_code != 200:
            raise RestError(f"Login fehlgeschlagen ({r.status_code}): {r.text[:300]}")
        token = r.json().get("token")
        if not token:
            raise RestError(f"Login: kein Token in der Antwort: {r.text[:300]}")
        self.token = token
        self.session.headers["Authorization"] = f"Bearer {token}"

    # -- Models --------------------------------------------------------------

    def find_one(self, table: str, filt: str) -> dict | None:
        r = self.session.get(
            f"{self.base_url}/api/v1/models/{table}",
            params={"$filter": filt, "$top": 2},
            timeout=30,
        )
        if r.status_code != 200:
            raise RestError(f"GET {table} ({r.status_code}): {r.text[:300]}")
        records = r.json().get("records", [])
        if len(records) > 1:
            raise RestError(f"GET {table} mit Filter {filt!r}: {len(records)} Treffer, erwartet 1.")
        return records[0] if records else None

    def create(self, table: str, body: dict) -> dict:
        r = self.session.post(
            f"{self.base_url}/api/v1/models/{table}",
            json=body,
            timeout=30,
        )
        if r.status_code not in (200, 201):
            raise RestError(f"POST {table} ({r.status_code}): {r.text[:500]}")
        return r.json()

    def update(self, table: str, record_id: int, body: dict) -> dict:
        r = self.session.put(
            f"{self.base_url}/api/v1/models/{table}/{record_id}",
            json=body,
            timeout=30,
        )
        if r.status_code not in (200, 201):
            raise RestError(f"PUT {table}/{record_id} ({r.status_code}): {r.text[:500]}")
        return r.json()

    # -- Auflösung Window/Tab/Template --------------------------------------
    #
    # Hinweis: AD_Window/AD_Tab sind über /api/v1/models/... per Default für
    # GardenAdmin nicht zugänglich (REST-Whitelist). Wir nutzen daher den
    # /api/v1/windows-Endpoint, der die Window-Definition (inkl. Tabs) auch
    # ohne expliziten Resource-Access liefert.

    _windows_cache: list[dict] | None = None

    def _list_windows(self) -> list[dict]:
        if self._windows_cache is None:
            r = self.session.get(f"{self.base_url}/api/v1/windows", timeout=30)
            if r.status_code != 200:
                raise RestError(f"GET /windows ({r.status_code}): {r.text[:300]}")
            self._windows_cache = r.json().get("windows", [])
        return self._windows_cache

    def resolve_window(self, name: str) -> tuple[int, str]:
        matches = [w for w in self._list_windows() if w.get("Name") == name]
        if not matches:
            raise RestError(f"AD_Window mit Name '{name}' nicht gefunden.")
        if len(matches) > 1:
            ids = ", ".join(str(m["id"]) for m in matches)
            raise RestError(f"AD_Window mit Name '{name}' nicht eindeutig: {ids}")
        return int(matches[0]["id"]), matches[0]["slug"]

    def resolve_tab(self, window_slug: str, tab_name: str) -> int:
        r = self.session.get(
            f"{self.base_url}/api/v1/windows/{window_slug}/tabs", timeout=30
        )
        if r.status_code != 200:
            raise RestError(
                f"GET /windows/{window_slug}/tabs ({r.status_code}): {r.text[:300]}"
            )
        tabs = r.json().get("tabs", [])
        matches = [t for t in tabs if t.get("Name") == tab_name]
        if not matches:
            available = ", ".join(t.get("Name", "?") for t in tabs)
            raise RestError(
                f"AD_Tab '{tab_name}' im Window '{window_slug}' nicht gefunden. "
                f"Vorhanden: {available}"
            )
        return int(matches[0]["id"])

    def ensure_template(
        self,
        window_id: int,
        tab_id: int,
        csv_header: str,
        label: str,
    ) -> int:
        """Sucht ein Auto-Template für (window, tab); legt es bei Bedarf an
        (inkl. Access-Eintrag für die aktive Rolle) oder aktualisiert seinen
        CSVHeader auf den aktuellen Stand."""
        rec = self.find_one(
            "ad_importtemplate",
            f"AD_Window_ID eq {window_id} and AD_Tab_ID eq {tab_id}",
        )
        if rec:
            tmpl_id = int(rec["id"])
            if (rec.get("CSVHeader") or "") != csv_header:
                self.update("ad_importtemplate", tmpl_id, {"CSVHeader": csv_header})
            self._ensure_template_access(tmpl_id)
            return tmpl_id
        body = {
            "Name": f"auto: {label}",
            "AD_Window_ID": {"id": window_id},
            "AD_Tab_ID": {"id": tab_id},
            "ImportTemplateType": "CSV",
            "SeparatorChar": ",",   # Java nimmt charAt(0), also direkt das Zeichen
            "QuoteChar": "\"",
            "CharacterSet": "UTF-8",
            "CSVHeader": csv_header,
        }
        rec = self.create("ad_importtemplate", body)
        new_id = rec.get("id") or rec.get("AD_ImportTemplate_ID")
        if not new_id:
            raise RestError(f"AD_ImportTemplate angelegt, aber keine ID in Antwort: {rec}")
        tmpl_id = int(new_id)
        self._ensure_template_access(tmpl_id)
        return tmpl_id

    def _ensure_template_access(self, template_id: int) -> None:
        """Stellt sicher, dass die aktuelle Rolle Insert/Update/Merge auf
        diesem Template darf. Sonst lehnt ImportCSVProcess.initGridTab ab."""
        role_id = int(self.profile["role_id"])
        existing = self.find_one(
            "ad_importtemplateaccess",
            f"AD_ImportTemplate_ID eq {template_id} and AD_Role_ID eq {role_id}",
        )
        body = {
            "IsAllowInsert": True,
            "IsAllowUpdate": True,
            "IsAllowMerge": True,
        }
        if existing:
            need = any(not existing.get(k) for k in ("IsAllowInsert", "IsAllowUpdate", "IsAllowMerge"))
            if need:
                self.update("ad_importtemplateaccess", int(existing["id"]), body)
        else:
            self.create(
                "ad_importtemplateaccess",
                {
                    "AD_ImportTemplate_ID": {"id": template_id},
                    "AD_Role_ID": {"id": role_id},
                    **body,
                },
            )

    # -- ImportCSVProcess ----------------------------------------------------

    def run_import(self, template_id: int, server_path: str, mode: str) -> dict:
        r = self.session.post(
            f"{self.base_url}/api/v1/processes/importcsvprocess",
            json={
                "AD_ImportTemplate_ID": template_id,
                "FileName": server_path,
                "ImportMode": mode,
            },
            timeout=600,
        )
        if r.status_code != 200:
            raise RestError(f"ImportCSVProcess ({r.status_code}): {r.text[:500]}")
        data = r.json()
        if data.get("isError"):
            raise RestError(
                f"ImportCSVProcess meldet Fehler: {data.get('summary')!r} / "
                f"{[lg.get('msg') for lg in data.get('logs', [])][:5]}"
            )
        return data


def _q(value: str) -> str:
    """Einfaches Escapen für OData-String-Literal."""
    return value.replace("'", "''")


# ──────────────────────────────────────────────────────────────────────────────
# Ergebnis-CSV auswerten
# ──────────────────────────────────────────────────────────────────────────────

# Erfolg laut GridTabCSVImporter: "<Tabelle>: Inserted ..." oder "Updated ..."
SUCCESS_RE = re.compile(r"<[^>]+>:\s*(Inserted|Updated)\b")


def parse_export_csv(b64: str) -> tuple[list[dict], int, int]:
    """Dekodiert die Ergebnis-CSV. Liefert (Zeilen mit _LOG_, ok_count, err_count)."""
    if not b64:
        return [], 0, 0
    text = base64.b64decode(b64).decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    ok, err = 0, 0
    for row in rows:
        log = row.get("_LOG_", "") or ""
        if SUCCESS_RE.search(log):
            ok += 1
        else:
            err += 1
    return rows, ok, err


# ──────────────────────────────────────────────────────────────────────────────
# Hauptablauf
# ──────────────────────────────────────────────────────────────────────────────

def write_log_csv(rows: list[dict], log_path: Path) -> None:
    if not rows:
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def stage_csv(staging_dir: Path, basename: str, content: str) -> Path:
    staging_dir.mkdir(parents=True, exist_ok=True)
    path = staging_dir / basename
    path.write_text(content, encoding="utf-8")
    return path


def push_staged(local_path: Path, ssh_target: str, remote_dir: Path) -> str:
    """Kopiert die lokal gestagete CSV per scp auf einen entfernten
    iDempiere-Server. `server_staging_dir` liegt dort im Dateisystem des
    Servers, das der ImportCSVProcess per `FileName` einliest — bei einem
    Remote-Server (Importer läuft nicht auf demselben Host) ist das lokale
    Staging-Verzeichnis für den Server unsichtbar. Gibt den Remote-Pfad
    zurück, der dem Prozess als FileName übergeben wird.

    Voraussetzung: `ssh`/`scp` ohne interaktiven Prompt nutzbar (Key-Auth);
    der SSH-User muss in `server_staging_dir` schreiben dürfen und der
    iDempiere-Server-User es lesen können (z.B. derselbe Account)."""
    remote_path = remote_dir.as_posix().rstrip("/") + "/" + local_path.name
    subprocess.run(
        ["ssh", "-o", "BatchMode=yes", ssh_target, "mkdir", "-p", remote_dir.as_posix()],
        check=True,
    )
    subprocess.run(
        ["scp", "-q", "-o", "BatchMode=yes", str(local_path), f"{ssh_target}:{remote_path}"],
        check=True,
    )
    return remote_path


def remove_remote(ssh_target: str, remote_path: str) -> None:
    """Entfernt die zuvor per push_staged hochgeladene Remote-CSV (best effort)."""
    try:
        subprocess.run(
            ["ssh", "-o", "BatchMode=yes", ssh_target, "rm", "-f", remote_path],
            check=False,
        )
    except OSError:
        pass


def filter_entries(
    entries: list[ConfigEntry],
    start_from: str | None,
    only_sheets: list[str] | None,
) -> list[ConfigEntry]:
    out = list(entries)
    if start_from:
        names = [e.sheet for e in out]
        if start_from not in names:
            sys.exit(f"--start-from: Sheet '{start_from}' nicht im Konfig-Sheet.")
        out = out[names.index(start_from):]
    if only_sheets:
        wanted = set(only_sheets)
        out = [e for e in out if e.sheet in wanted]
        missing = wanted - {e.sheet for e in out}
        if missing:
            sys.exit(f"--only-sheets: unbekannt: {', '.join(sorted(missing))}")
    out = [e for e in out if not e.skip]
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ODS-Multi-Sheet-Importer für iDempiere (REST)."
    )
    parser.add_argument("ods_file", type=Path, help="Pfad zur ODS-Datei.")
    parser.add_argument("--profile", help="Profil-Name (siehe profiles.yaml).")
    parser.add_argument("--start-from", metavar="SHEET", help="Erstes Sheet, ab dem importiert wird.")
    parser.add_argument(
        "--only-sheets",
        metavar="A,B,C",
        help="Nur diese Sheets importieren (Reihenfolge bleibt aus _config).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Nur prüfen, nicht importieren.")
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Bei Zeilenfehlern in einem Sheet trotzdem mit dem nächsten weitermachen.",
    )
    args = parser.parse_args(argv)

    if not args.ods_file.exists():
        sys.exit(f"ODS-Datei nicht gefunden: {args.ods_file}")

    profiles_data = load_profiles()
    profile_name, profile = select_profile(profiles_data, args.profile)
    print(f"→ Profil: {profile_name} ({profile['username']}@{profile['base_url']})")

    sheets = read_ods(args.ods_file)
    if CONFIG_SHEET_NAME not in sheets:
        sys.exit(f"ODS hat kein '{CONFIG_SHEET_NAME}'-Sheet.")
    entries = parse_config_sheet(sheets[CONFIG_SHEET_NAME])
    only = args.only_sheets.split(",") if args.only_sheets else None
    todo = filter_entries(entries, args.start_from, only)

    if not todo:
        print("(Nichts zu tun.)")
        return 0

    print(f"→ {len(todo)} Sheet(s) zum Verarbeiten:")
    for e in todo:
        print(f"   • {e.sheet:30} → {e.window} / {e.tab}  [Mode={e.import_mode}]")

    # Datensheets prüfen
    for e in todo:
        if e.sheet not in sheets:
            sys.exit(f"Sheet '{e.sheet}' aus _config existiert nicht in der ODS.")
        if len(sheets[e.sheet]) < 2:
            sys.exit(f"Sheet '{e.sheet}' hat keine Datenzeilen (nur Header oder leer).")

    client = IDempiereClient(profile)
    print("→ Login …")
    client.login()
    print("  ok.")

    # Auflösung Window/Tab/Template (im Dry-Run nur prüfen)
    resolved: list[tuple[ConfigEntry, int]] = []  # (entry, template_id)
    print("→ Auflösung Window/Tab/Template:")
    for e in todo:
        win_id, win_slug = client.resolve_window(e.window)
        tab_id = client.resolve_tab(win_slug, e.tab)
        # Header der ersten Zeile des Datensheets als CSV-Header (Komma-getrennt,
        # ohne Quoting — entspricht dem, was die importierte CSV als erste Zeile
        # haben wird).
        header_row = sheets[e.sheet][0]
        csv_header = sheet_to_csv([header_row]).rstrip("\r\n")
        if args.dry_run:
            existing = client.find_one(
                "ad_importtemplate",
                f"AD_Window_ID eq {win_id} and AD_Tab_ID eq {tab_id}",
            )
            tmpl_state = f"vorhanden (ID={existing['id']})" if existing else "wird angelegt"
            print(f"   • {e.sheet:30} → Window {win_id}, Tab {tab_id}, Template {tmpl_state}")
            resolved.append((e, -1))
        else:
            tmpl_id = client.ensure_template(win_id, tab_id, csv_header, f"{e.window}/{e.tab}")
            print(f"   • {e.sheet:30} → Window {win_id}, Tab {tab_id}, Template {tmpl_id}")
            resolved.append((e, tmpl_id))

    if args.dry_run:
        print("\nDry-Run ok. Kein Import durchgeführt.")
        return 0

    staging_dir = Path(profile.get("server_staging_dir", "/tmp/idempiere-csv-import"))
    # Remote-iDempiere: liegt der Server nicht auf demselben Host wie dieser
    # Importer, kann er das lokale Staging-Verzeichnis nicht lesen. Mit
    # `staging_ssh: user@host` im Profil wird die gestagete CSV per scp ins
    # server_staging_dir des Servers geschoben und der Remote-Pfad übergeben.
    staging_ssh = profile.get("staging_ssh")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    overall_failed: list[ConfigEntry] = []

    for e, tmpl_id in resolved:
        print(f"\n→ Sheet '{e.sheet}' (Mode={e.import_mode}) …")
        csv_text = sheet_to_csv(sheets[e.sheet])
        basename = f"{timestamp}_{_safe(e.sheet)}.csv"
        staged = stage_csv(staging_dir, basename, csv_text)
        if staging_ssh:
            server_path = push_staged(staged, staging_ssh, staging_dir)
        else:
            server_path = str(staged)
        try:
            result = client.run_import(tmpl_id, server_path, e.import_mode)
        finally:
            try:
                staged.unlink()
            except OSError:
                pass
            if staging_ssh:
                remove_remote(staging_ssh, server_path)

        rows, ok, err = parse_export_csv(result.get("exportFile", ""))
        log_path = LOG_DIR / f"{timestamp}_{_safe(e.sheet)}.csv"
        write_log_csv(rows, log_path)
        print(f"   {ok} ok, {err} Fehler. Log: {log_path}")

        if err > 0:
            print(f"   ⚠ Fehler in Sheet '{e.sheet}':")
            for row in rows:
                log = row.get("_LOG_", "") or ""
                if not SUCCESS_RE.search(log):
                    short = " | ".join(f"{k}={v}" for k, v in row.items() if k != "_LOG_")[:200]
                    print(f"     {short}\n       _LOG_: {log[:300]}")
            overall_failed.append(e)
            if not args.continue_on_error:
                resume_cmd = _resume_cmd(args, e.sheet)
                print(
                    "\n✗ Abbruch nach Fehlern in diesem Sheet."
                    f"\n  Wiederaufnehmen mit:\n    {resume_cmd}"
                )
                return 2

    if overall_failed:
        names = ", ".join(e.sheet for e in overall_failed)
        print(f"\n✗ Fertig — aber Fehler in: {names}")
        return 2

    print("\n✓ Alle Sheets erfolgreich importiert.")
    return 0


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)


def _resume_cmd(args: argparse.Namespace, sheet: str) -> str:
    parts = [sys.argv[0], shlex.quote(str(args.ods_file))]
    if args.profile:
        parts += ["--profile", shlex.quote(args.profile)]
    parts += ["--start-from", shlex.quote(sheet)]
    return " ".join(parts)


if __name__ == "__main__":
    sys.exit(main())
