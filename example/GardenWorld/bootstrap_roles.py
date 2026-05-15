#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Bootstrap der Anlagenbuch-Master-Rolle für die GardenWorld-Community-Demo.

Variante des JBKG-Bootstraps: legt die Master-Rolle `anlagenbuch` an,
gibt ihr Process-/Window-Access auf die BXS-Objekte und hängt sie per
`AD_Role_Included` in die GardenAdmin-Login-Rolle ein.

GardenAdmin hat im Gegensatz zur Bayen-Datalotte vollen REST-Zugriff
(inkl. AD_Window), darum kommt diese Variante ohne psql-Fallback aus.

Konfiguration aus `example/GardenWorld/config.env`.
"""
from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import quote

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "setup"))
from lib_rest import RestError, from_config  # noqa: E402


MASTER_ROLE_NAME = "anlagenbuch"
MASTER_ROLE_DESC = (
    "Master-Rolle für das Anlagenbuch-2Pack: Workflow-Buttons, "
    "JasperReports und ods-/CSV-Import. Wird per AD_Role_Included in die "
    "GardenAdmin-Login-Rolle eingebunden (Community-Demo)."
)

BXS_PROCESS_VALUES = [
    "ImportCSVProcess",
    "Cache Reset",
    "BXS_AssetItem_CloseItem",
    "BXS_WorkOrder_CompleteOrder",
    "BXS_WorkOrder_PullOpenItems",
    "BXS_Asset_CreateWorkOrder",
    "BXS_Print_WorkshopDossier",
    "BXS_Print_AssetDossier",
    "BXS_Print_AssetStatusOverview",
]

BXS_WINDOW_NAMES = [
    "BXS Asset",
    "BXS Asset Class",
    "BXS Schedule Type",
    "BXS Work Order",
]

STEP = "BOOTSTRAP-GW"


def log(msg: str) -> None:
    print(f"[{STEP}] {msg}", flush=True)


def load_config() -> dict[str, str]:
    cfg_path = SCRIPT_DIR / "config.env"
    if not cfg_path.exists():
        cfg_path = SCRIPT_DIR / "config.env.example"
        log(f"WARN: config.env fehlt, lese {cfg_path.name}")
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


def find_one(rest, table: str, filter_expr: str) -> dict | None:
    path = f"/api/v1/models/{table}?$filter={quote(filter_expr)}"
    res = rest._raw("GET", path)
    recs = res.get("records") or []
    return recs[0] if recs else None


def ensure_master_role(rest, ad_org_id: int) -> int:
    rec = find_one(rest, "ad_role", f"Name eq '{MASTER_ROLE_NAME}'")
    if rec:
        log(f"[skip] Master-Rolle existiert (id={rec['id']})")
        return int(rec["id"])
    body = {
        "AD_Org_ID": ad_org_id,
        "Name": MASTER_ROLE_NAME,
        "Description": MASTER_ROLE_DESC,
        "RoleType": "WS",
        "IsMasterRole": "Y",
        "IsAccessAllOrgs": "N",
        "UserLevel": " CO",
        "IsActive": "Y",
        "IsManual": "Y",
        "IsCanExport": "Y",
        "IsCanReport": "Y",
        "IsAccessAdvanced": "N",
    }
    res = rest._raw("POST", "/api/v1/models/ad_role", body=body)
    new_id = int(res.get("id") or res.get("AD_Role_ID"))
    log(f"[neu]  Master-Rolle angelegt (id={new_id})")
    return new_id


def find_login_role_id(rest, login_role_name: str) -> int:
    rec = find_one(rest, "ad_role", f"Name eq '{login_role_name}'")
    if not rec:
        raise RestError(
            f"Login-Rolle '{login_role_name}' fehlt — vom Admin manuell anlegen."
        )
    return int(rec["id"])


def find_process_id(rest, value: str) -> int:
    rec = find_one(rest, "ad_process", f"Value eq '{value}'")
    if not rec:
        raise RestError(f"Prozess '{value}' nicht gefunden.")
    return int(rec["id"])


def find_window_id(rest, name: str) -> int:
    rec = find_one(rest, "ad_window", f"Name eq '{name}'")
    if not rec:
        raise RestError(
            f"Window '{name}' nicht gefunden — 2Pack-Install prüfen."
        )
    return int(rec["id"])


def ensure_process_access(rest, role_id: int, process_id: int,
                          process_label: str, ad_org_id: int) -> None:
    existing = find_one(
        rest, "ad_process_access",
        f"AD_Role_ID eq {role_id} and AD_Process_ID eq {process_id}",
    )
    if existing:
        log(f"[skip] Process-Access {process_label}")
        return
    body = {
        "AD_Org_ID": ad_org_id, "AD_Role_ID": role_id,
        "AD_Process_ID": process_id, "IsActive": "Y", "IsReadWrite": "Y",
    }
    rest._raw("POST", "/api/v1/models/ad_process_access", body=body)
    log(f"[neu]  Process-Access {process_label}")


def ensure_window_access(rest, role_id: int, window_id: int,
                         window_label: str, ad_org_id: int) -> None:
    existing = find_one(
        rest, "ad_window_access",
        f"AD_Role_ID eq {role_id} and AD_Window_ID eq {window_id}",
    )
    if existing:
        log(f"[skip] Window-Access {window_label}")
        return
    body = {
        "AD_Org_ID": ad_org_id, "AD_Role_ID": role_id,
        "AD_Window_ID": window_id, "IsActive": "Y", "IsReadWrite": "Y",
    }
    rest._raw("POST", "/api/v1/models/ad_window_access", body=body)
    log(f"[neu]  Window-Access {window_label}")


def ensure_role_include(rest, role_id: int, included_role_id: int,
                        ad_org_id: int, login_role_name: str) -> None:
    existing = find_one(
        rest, "ad_role_included",
        f"AD_Role_ID eq {role_id} and Included_Role_ID eq {included_role_id}",
    )
    if existing:
        log("[skip] Role-Include existiert")
        return
    body = {
        "AD_Org_ID": ad_org_id, "AD_Role_ID": role_id,
        "Included_Role_ID": included_role_id, "SeqNo": 20, "IsActive": "Y",
    }
    rest._raw("POST", "/api/v1/models/ad_role_included", body=body)
    log(f"[neu]  Role-Include {login_role_name} ⊃ {MASTER_ROLE_NAME}")


def main() -> int:
    cfg = load_config()
    ad_org_id = int(cfg.get("IDEMPIERE_ORG_ID", "11"))
    login_role_name = cfg.get("LOGIN_ROLE_NAME", "GardenAdmin")
    rest = from_config(cfg)

    master_id = ensure_master_role(rest, ad_org_id)

    for proc_value in BXS_PROCESS_VALUES:
        proc_id = find_process_id(rest, proc_value)
        ensure_process_access(rest, master_id, proc_id, proc_value, ad_org_id)

    for win_name in BXS_WINDOW_NAMES:
        win_id = find_window_id(rest, win_name)
        ensure_window_access(rest, master_id, win_id, win_name, ad_org_id)

    login_id = find_login_role_id(rest, login_role_name)
    ensure_role_include(rest, login_id, master_id, ad_org_id, login_role_name)

    log("fertig.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
