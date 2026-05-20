#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Hängt die System-Master-Rolle „anlagenbuch" in die GardenWorld-Login-
Rolle ein (per AD_Role_Included). Mehr macht dieses Skript nicht.

Das Anlagenbuch-2Pack (`Anlagenbuch_03_role.zip`) liefert die Master-
Rolle samt allen Window-/Process-Access-Records bereits im System-
Mandanten (AD_Client_ID=0) aus. Tenants müssen also keine eigenen
Access-Records mehr pflegen — sie binden die System-Rolle nur per
`AD_Role_Included` in eine ihrer eigenen Login-Rollen ein. Cross-Tenant-
Inclusion ist im iDempiere-Core erlaubt (siehe `docs/Architecture.md`,
Abschnitt „System-Master-Rolle").

Dieses Skript ist **GardenWorld-spezifisch** — es ist Beispiel-Code für
die Community-Demo gegen den iDempiere-Standard-Mandanten GardenWorld.
Andere Anwender können das gleiche Pattern manuell in der UI klicken
(Window „Role" → Login-Rolle öffnen → Tab „Included Role" → System-
Rolle `anlagenbuch` auswählen) oder ein analoges Skript für ihre
Umgebung schreiben (Vorlage: `example/JakobBayenKG/bootstrap_roles.py`).

Voraussetzung (einmalig manuell vom Admin):
  * Anlagenbuch-2Pack ist eingespielt (`./install.sh`) — die Rolle
    `anlagenbuch` existiert im System-Mandanten.
  * Login-Rolle aus `LOGIN_ROLE_NAME` (Default: „GardenWorld Admin")
    existiert; der User, mit dem das Skript läuft, ist dieser Rolle
    zugeordnet und hat Window-Access auf „Role" (für den
    AD_Role_Included-POST per REST). GardenAdmin erfüllt das.

Konfiguration aus `example/GardenWorld/config.env`:
  LOGIN_ROLE_NAME=GardenWorld Admin
  IDEMPIERE_ORG_ID=11
  IDEMPIERE_URL, IDEMPIERE_USER, IDEMPIERE_PASSWORD, …
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "setup"))
from lib_rest import RestError, from_config  # noqa: E402


MASTER_ROLE_NAME = "anlagenbuch"


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
    from urllib.parse import quote
    path = f"/api/v1/models/{table}?$filter={quote(filter_expr)}"
    res = rest._raw("GET", path)
    recs = res.get("records") or []
    return recs[0] if recs else None


def find_master_role_id(rest) -> int:
    # Master-Rolle liegt im System-Mandanten (AD_Client_ID=0). Der REST-
    # Filter sucht Client-übergreifend, weil unser Login-User in den
    # AD_Role-Filter SELECT alle Clients sieht; wir prüfen den Client zur
    # Sicherheit gleich mit, damit eine gleichnamige Tenant-Rolle aus
    # Versehen nicht erwischt wird.
    rec = find_one(
        rest, "ad_role",
        f"Name eq '{MASTER_ROLE_NAME}' and AD_Client_ID eq 0",
    )
    if not rec:
        raise RestError(
            f"System-Master-Rolle '{MASTER_ROLE_NAME}' fehlt im "
            "System-Mandanten. Erst `./install.sh` laufen lassen, damit "
            "das Anlagenbuch_03_role.zip eingespielt wird."
        )
    return int(rec["id"])


def find_login_role_id(rest, login_role_name: str) -> int:
    rec = find_one(rest, "ad_role", f"Name eq '{login_role_name}'")
    if not rec:
        raise RestError(
            f"Login-Rolle '{login_role_name}' fehlt — vom Admin manuell anlegen."
        )
    return int(rec["id"])


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


def main() -> int:
    cfg = load_config()
    ad_org_id = int(cfg.get("IDEMPIERE_ORG_ID", "11"))
    login_role_name = cfg.get("LOGIN_ROLE_NAME", "GardenWorld Admin")
    rest = from_config(cfg)

    master_id = find_master_role_id(rest)
    login_id = find_login_role_id(rest, login_role_name)
    ensure_role_include(rest, login_id, master_id, ad_org_id, login_role_name)

    log("fertig.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
