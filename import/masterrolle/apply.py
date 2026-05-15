#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Spielt die Anlagenbuch-Master-Rolle aus CSV in eine iDempiere-Instanz ein.

Zwei Eingaben:
  1. `anlagenbuch.csv` (mandantenneutral, mit dem Plugin ausgeliefert)
     definiert die Master-Rolle + Window-/Process-Access.
  2. `--includes <CSV>` (mandantenspezifisch, vom Deployer mitgegeben)
     listet die Login-Rollen, in die die Master-Rolle per
     `AD_Role_Included` eingehängt wird. Beispiel:
     `example/JakobBayenKG/masterrolle_includes.csv`.

Idempotent: bestehende Rolle / Accesses / Includes werden mit `[skip]`
übersprungen.

Voraussetzungen:
  * Die Login-Rolle, mit der das Skript läuft, hat zeitweilig Schreib-
    rechte auf AD_Role, AD_Role_Included, AD_Window_Access,
    AD_Process_Access (vom Admin einmalig eingerichtet).
  * `setup/config.env` enthält die REST-/PG-Credentials.

Aufruf:
    ./apply.py --includes example/JakobBayenKG/masterrolle_includes.csv
    ./apply.py --no-includes      # nur Master-Rolle, keine Login-Includes
"""
from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "setup"))
from lib_rest import RestError, from_config  # noqa: E402


ROLE_CSV = SCRIPT_DIR / "anlagenbuch.csv"
SEQ_NO_INCLUDE = 30   # Reihenfolge in Login-Rolle — eigene SeqNo für Stabilität

STEP = "MASTERROLE"


def log(msg: str) -> None:
    print(f"[{STEP}] {msg}", flush=True)


# ── CSV-Parsing ───────────────────────────────────────────────────────────


def parse_role_csv(path: Path) -> dict:
    """Liest die strukturierte Master-Rollen-CSV (Section,Key,Value)."""
    meta: dict[str, str] = {}
    windows: list[str] = []
    processes: list[str] = []
    with path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            section = (row.get("Section") or "").strip()
            key     = (row.get("Key") or "").strip()
            if not section or not key:
                continue
            if section == "Meta":
                meta[key] = (row.get("Value") or "").strip()
            elif section == "WindowAccess":
                windows.append(key)
            elif section == "ProcessAccess":
                processes.append(key)
            else:
                log(f"WARN: unbekannte Section '{section}' in {path.name}")
    return {"meta": meta, "windows": windows, "processes": processes}


def parse_includes_csv(path: Path) -> list[str]:
    with path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return [(row.get("LoginRoleName") or "").strip()
                for row in reader if row.get("LoginRoleName")]


# ── Config / psql für AD_Window-Lookup ────────────────────────────────────


def load_config() -> dict[str, str]:
    cfg_path = REPO_ROOT / "setup" / "config.env"
    cfg: dict[str, str] = {}
    for line in cfg_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        v = v.strip().split("#", 1)[0].strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
            v = v[1:-1]
        cfg[k.strip()] = v
    return cfg


def find_window_id_via_psql(cfg: dict[str, str], name: str) -> int:
    """AD_Window ist nicht REST-zugänglich (REST_Resource-Whitelist).
    Fallback: direkter psql-Lookup."""
    env = os.environ.copy()
    env["PGPASSWORD"] = cfg.get("PGPASSWORD", "adempiere")
    out = subprocess.check_output(
        ["psql", "-h", cfg.get("PGHOST", "localhost"),
         "-p", cfg.get("PGPORT", "5432"),
         "-U", cfg.get("PGUSER", "adempiere"),
         "-d", cfg.get("PGDATABASE", "idempiere"),
         "-tA", "-c", f"SELECT ad_window_id FROM ad_window WHERE name='{name}'"],
        env=env, text=True,
    ).strip()
    if not out:
        raise RestError(f"AD_Window '{name}' nicht gefunden — 2Pack installiert?")
    return int(out)


# ── REST-Helper ───────────────────────────────────────────────────────────


def find_one(rest, table: str, filter_expr: str) -> dict | None:
    path = f"/api/v1/models/{table}?$filter={quote(filter_expr)}"
    res = rest._raw("GET", path)
    recs = res.get("records") or []
    return recs[0] if recs else None


# ── Bootstrap-Schritte ────────────────────────────────────────────────────


def ensure_master_role(rest, meta: dict[str, str], ad_org_id: int) -> int:
    name = meta["RoleName"]
    rec = find_one(rest, "ad_role", f"Name eq '{name}'")
    if rec:
        log(f"[skip] Master-Rolle '{name}' existiert (id={rec['id']})")
        return int(rec["id"])
    body = {
        "AD_Org_ID": ad_org_id,
        "Name": name,
        "Description": meta.get("Description", ""),
        # RoleType bleibt leer → klassische Login-/Include-Rolle, nicht WS
        "IsMasterRole": "Y",
        "IsManual":     "Y",
        "IsActive":     "Y",
        "UserLevel":         " " + meta.get("UserLevel", "CO"),   # AD_Ref mit führendem Leerzeichen
        "IsAccessAllOrgs":   meta.get("IsAccessAllOrgs", "N"),
        "IsCanReport":       meta.get("IsCanReport", "Y"),
        "IsCanExport":       meta.get("IsCanExport", "Y"),
        "IsAccessAdvanced":  meta.get("IsAccessAdvanced", "N"),
    }
    res = rest._raw("POST", "/api/v1/models/ad_role", body=body)
    new_id = int(res.get("id") or res.get("AD_Role_ID"))
    log(f"[neu]  Master-Rolle '{name}' angelegt (id={new_id})")
    return new_id


def ensure_window_access(rest, role_id: int, window_id: int,
                         label: str, ad_org_id: int) -> None:
    existing = find_one(
        rest, "ad_window_access",
        f"AD_Role_ID eq {role_id} and AD_Window_ID eq {window_id}",
    )
    if existing:
        log(f"[skip] Window-Access {label}")
        return
    body = {
        "AD_Org_ID":    ad_org_id,
        "AD_Role_ID":   role_id,
        "AD_Window_ID": window_id,
        "IsReadWrite":  "Y",
        "IsActive":     "Y",
    }
    rest._raw("POST", "/api/v1/models/ad_window_access", body=body)
    log(f"[neu]  Window-Access {label}")


def find_process_id(rest, value: str) -> int:
    rec = find_one(rest, "ad_process", f"Value eq '{value}'")
    if not rec:
        raise RestError(f"AD_Process '{value}' nicht gefunden — 2Pack installiert?")
    return int(rec["id"])


def ensure_process_access(rest, role_id: int, process_id: int,
                          label: str, ad_org_id: int) -> None:
    existing = find_one(
        rest, "ad_process_access",
        f"AD_Role_ID eq {role_id} and AD_Process_ID eq {process_id}",
    )
    if existing:
        log(f"[skip] Process-Access {label}")
        return
    body = {
        "AD_Org_ID":     ad_org_id,
        "AD_Role_ID":    role_id,
        "AD_Process_ID": process_id,
        "IsReadWrite":   "Y",
        "IsActive":      "Y",
    }
    rest._raw("POST", "/api/v1/models/ad_process_access", body=body)
    log(f"[neu]  Process-Access {label}")


def find_login_role_id(rest, name: str) -> int:
    # Apostrophe nicht in unseren Rollennamen — Quoting reicht.
    # Sonderzeichen wie 'ä' werden durch quote() URL-codiert.
    rec = find_one(rest, "ad_role", f"Name eq '{name}'")
    if not rec:
        raise RestError(f"Login-Rolle '{name}' nicht gefunden.")
    return int(rec["id"])


def ensure_role_include(rest, login_role_id: int, master_role_id: int,
                        login_role_name: str, master_role_name: str,
                        ad_org_id: int) -> None:
    existing = find_one(
        rest, "ad_role_included",
        f"AD_Role_ID eq {login_role_id} and Included_Role_ID eq {master_role_id}",
    )
    if existing:
        log(f"[skip] Include {login_role_name} ⊃ {master_role_name}")
        return
    body = {
        "AD_Org_ID":        ad_org_id,
        "AD_Role_ID":       login_role_id,
        "Included_Role_ID": master_role_id,
        "SeqNo":            SEQ_NO_INCLUDE,
        "IsActive":         "Y",
    }
    rest._raw("POST", "/api/v1/models/ad_role_included", body=body)
    log(f"[neu]  Include {login_role_name} ⊃ {master_role_name}")


# ── Main ──────────────────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--includes", type=Path, default=None,
                    help="CSV mit Login-Rollen, in die die Master-Rolle eingehängt wird "
                         "(z.B. example/JakobBayenKG/masterrolle_includes.csv).")
    ap.add_argument("--no-includes", action="store_true",
                    help="Nur die Master-Rolle einrichten; Includes überspringen.")
    args = ap.parse_args()
    if not args.no_includes and args.includes is None:
        ap.error("--includes <CSV> oder --no-includes erforderlich.")

    cfg = load_config()
    ad_org_id = int(cfg.get("IDEMPIERE_ORG_ID", "0"))
    rest = from_config(cfg)

    role_def = parse_role_csv(ROLE_CSV)
    log(f"CSV: {len(role_def['windows'])} Window-Access, "
        f"{len(role_def['processes'])} Process-Access")

    master_id = ensure_master_role(rest, role_def["meta"], ad_org_id)

    for win_name in role_def["windows"]:
        win_id = find_window_id_via_psql(cfg, win_name)
        ensure_window_access(rest, master_id, win_id, win_name, ad_org_id)

    for proc_value in role_def["processes"]:
        proc_id = find_process_id(rest, proc_value)
        ensure_process_access(rest, master_id, proc_id, proc_value, ad_org_id)

    if args.no_includes:
        log("Includes übersprungen (--no-includes).")
        return 0

    login_role_names = parse_includes_csv(args.includes)
    master_role_name = role_def["meta"]["RoleName"]
    log(f"Includes-CSV: {len(login_role_names)} Login-Rollen.")
    for login_name in login_role_names:
        login_id = find_login_role_id(rest, login_name)
        ensure_role_include(rest, login_id, master_id,
                            login_name, master_role_name, ad_org_id)

    log("fertig.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
