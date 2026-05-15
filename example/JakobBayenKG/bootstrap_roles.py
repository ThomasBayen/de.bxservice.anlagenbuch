#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Bootstrap der Anlagenbuch-Master-Rolle und ihrer Verkabelung mit der
Bayen-Login-Rolle (Datalotte) via iDempiere-REST.

Dieses Skript ist **JBKG-spezifisch** — es ist Beispiel-Code für ein
Customer-Deployment.

Rollenkonzept: eine projektspezifische Master-Rolle `anlagenbuch`
(kleingeschrieben, `IsMasterRole=Y`). Sie wird sowohl von menschlichen
Login-Rollen (GF, Disposition, …) als auch von der Skript-Login-Rolle
„Datalotte" per `AD_Role_Included` eingebunden. Datalotte bekommt
**keine eigene Anlagenbuch-spezifische Master-Rolle** — sie nutzt
dieselbe wie GF.

Voraussetzung (einmalig manuell vom Admin in der iDempiere-UI):
  * Login-Rolle „Datalotte" existiert und User „Datalotte Bayen" ist
    der Rolle zugeordnet.
  * Datalotte hat Window-Access auf „Role" (AD_Role-CRUD per REST)
    und auf „Report and Process" (AD_Process-Lookups per REST).

Dieses Skript pflegt die `anlagenbuch`-Master-Rolle idempotent:
  1. Master-Rolle „anlagenbuch" anlegen, falls nicht vorhanden.
  2. Process-Access für alle Anlagenbuch-Prozesse + ImportCSVProcess
     + Cache Reset.
  3. Window-Access für die vier BXS-Fenster.
  4. Master-Rolle als Include in die Login-Rolle „Datalotte"
     eintragen (analoge Pflege für menschliche Login-Rollen wie GF
     macht der iDempiere-Admin manuell).

Konfiguration aus `example/JakobBayenKG/config.env`:
  LOGIN_ROLE_NAME=Datalotte    (umgebungs-spezifisch)
  IDEMPIERE_ORG_ID=1000000     (umgebungs-spezifisch)
  IDEMPIERE_URL, IDEMPIERE_USER, IDEMPIERE_PASSWORD, …
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
# lib_rest liegt im community-setup/-Verzeichnis und bleibt dort.
sys.path.insert(0, str(REPO_ROOT / "setup"))
from lib_rest import RestError, from_config  # noqa: E402


# ── Konfiguration ──────────────────────────────────────────────────────────

MASTER_ROLE_NAME = "anlagenbuch"
MASTER_ROLE_DESC = (
    "Master-Rolle für das Anlagenbuch-2Pack: Workflow-Buttons, "
    "JasperReports und ods-/CSV-Import. Wird per AD_Role_Included "
    "eingebunden von menschlichen Login-Rollen (GF, Disposition, …) "
    "UND von der Skript-Login-Rolle Datalotte."
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

# BXS-Fenster — gepaart mit ihrem `uuids.csv`-Schlüssel. Die UUID wird zum
# AD_Window_Access-POST mitgereicht (siehe ensure_window_access), damit
# trekglobal-REST die AD_Window_ID per FK-Resolution selbst bestimmt — kein
# vorgelagerter Lookup auf AD_Window nötig (das wäre per /api/v1/models/
# ad_window für CO-Rollen 403, siehe Datalotte.md).
BXS_WINDOWS = [
    ("BXS Asset",         "BXS_Asset_Window"),
    ("BXS Asset Class",   "BXS_AssetClass_Window"),
    ("BXS Schedule Type", "BXS_ScheduleType_Window"),
    ("BXS Work Order",    "BXS_WorkOrder_Window"),
]


STEP = "BOOTSTRAP"


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
    from urllib.parse import quote
    path = f"/api/v1/models/{table}?$filter={quote(filter_expr)}"
    res = rest._raw("GET", path)
    recs = res.get("records") or []
    return recs[0] if recs else None


# ── Bootstrap-Schritte ─────────────────────────────────────────────────────


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
        raise RestError(
            f"Prozess '{value}' nicht gefunden. "
            "Bei 403: Login-Rolle braucht Window-Access auf 'Report and Process'."
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
        "AD_Org_ID": ad_org_id,
        "AD_Role_ID": role_id,
        "AD_Process_ID": process_id,
        "IsActive": "Y",
        "IsReadWrite": "Y",
    }
    rest._raw("POST", "/api/v1/models/ad_process_access", body=body)
    log(f"[neu]  Process-Access {process_label}")


def load_uuid_map() -> dict[tuple[str, str], str]:
    """uuids.csv (Repo-Root) als (ObjectType, Key) → UUID-Mapping einlesen.

    Wird gebraucht, um AD_Window_Access via UUID-FK anlegen zu können (s.
    ensure_window_access). Der Generator schreibt diese Datei beim 2Pack-
    Bau; sie ist projekt-weit die einzige Wahrheit über fixe UUIDs.
    """
    csv_path = REPO_ROOT / "uuids.csv"
    if not csv_path.exists():
        raise RestError(f"uuids.csv fehlt unter {csv_path}.")
    import csv as _csv
    mapping: dict[tuple[str, str], str] = {}
    with csv_path.open() as fh:
        reader = _csv.reader(fh)
        next(reader, None)  # Header überspringen
        for row in reader:
            if not row or row[0].lstrip().startswith("#"):
                continue
            if len(row) < 3:
                continue
            mapping[(row[0].strip(), row[1].strip())] = row[2].strip()
    return mapping


def ensure_window_access(rest, role_id: int, window_uuid: str,
                         window_label: str, ad_org_id: int) -> None:
    """Window-Access auf der Master-Rolle anlegen — ohne vorgelagerten
    AD_Window-Lookup. trekglobal-REST resolved `{"uid": "<UUID>"}` in
    FK-Feldern serverseitig (s. Datalotte.md, Abschnitt „REST-FK per
    UUID auflösen"). Damit funktioniert der Bootstrap rein per REST,
    auch beim allerersten Lauf, wo die Login-Rolle noch keinen Window-
    Access auf die BXS-Fenster hat (Henne-Ei-Problem mit
    /api/v1/models/ad_window und /api/v1/windows umgangen)."""
    body = {
        "AD_Org_ID": ad_org_id,
        "AD_Role_ID": role_id,
        "AD_Window_ID": {"uid": window_uuid},
        "IsActive": "Y",
        "IsReadWrite": "Y",
    }
    # Idempotenz: kein Vor-Lookup möglich (REST-Filter kennt keinen
    # FK-Pfad-Filter à la AD_Window.AD_Window_UU für CO-Rollen). Stattdessen
    # POST direkt und „duplicate key" als Erfolg werten — der Constraint
    # AD_Window_Access(AD_Role_ID, AD_Window_ID) ist UNIQUE.
    try:
        rest._raw("POST", "/api/v1/models/ad_window_access", body=body)
        log(f"[neu]  Window-Access {window_label}")
    except RestError as e:
        if "duplicate key" in str(e):
            log(f"[skip] Window-Access {window_label}")
        else:
            raise


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
        "AD_Org_ID": ad_org_id,
        "AD_Role_ID": role_id,
        "Included_Role_ID": included_role_id,
        "SeqNo": 20,
        "IsActive": "Y",
    }
    rest._raw("POST", "/api/v1/models/ad_role_included", body=body)
    log(f"[neu]  Role-Include {login_role_name} ⊃ {MASTER_ROLE_NAME}")


# ── Main ───────────────────────────────────────────────────────────────────


def main() -> int:
    cfg = load_config()
    ad_org_id = int(cfg.get("IDEMPIERE_ORG_ID", "0"))
    login_role_name = cfg.get("LOGIN_ROLE_NAME", "Datalotte")
    rest = from_config(cfg)

    master_id = ensure_master_role(rest, ad_org_id)

    for proc_value in BXS_PROCESS_VALUES:
        proc_id = find_process_id(rest, proc_value)
        ensure_process_access(rest, master_id, proc_id, proc_value, ad_org_id)

    uuid_map = load_uuid_map()
    for win_label, uuid_key in BXS_WINDOWS:
        win_uuid = uuid_map.get(("AD_Window", uuid_key))
        if not win_uuid:
            raise RestError(
                f"AD_Window/{uuid_key} fehlt in uuids.csv — 2Pack neu bauen."
            )
        ensure_window_access(rest, master_id, win_uuid, win_label, ad_org_id)

    login_id = find_login_role_id(rest, login_role_name)
    ensure_role_include(rest, login_id, master_id, ad_org_id, login_role_name)

    log("fertig.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
