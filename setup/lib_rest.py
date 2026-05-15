# SPDX-License-Identifier: AGPL-3.0-or-later
"""iDempiere-REST-Client (trekglobal Plugin).

Spezifika dieser API stehen in `~/iDempiere-development/rest/CLAUDE.md`:
  * Auth-Body: clientId/roleId/orgId/warehouseId müssen NUMERISCH sein.
  * Prozess-URL: AD_Process.Value wird via Slugify (lower + Satzzeichen→'-')
    transformiert. Korrekt: `bay_ngv_exportngv`. URL-Encoding (`%20`) ergibt 404.
  * Zwei Endpunkte:
      - global:    POST /api/v1/processes/{slug}
      - record:    POST /api/v1/models/{table}/{id}/{slug}
  * Zwei Fehlerformate:
      - HTTP 4xx/5xx mit {title, status, detail}
      - HTTP 200 mit {summary, isError: true, logs: [...]}
"""
from __future__ import annotations

import json
import re
import ssl
import unicodedata
from urllib import error, parse, request


_SLUG_PUNCT_RE = re.compile(r'[\s!"#$%&\'()*+,./:;<=>?@\[\\\]^`{|}~]')
_SLUG_NONWORD_RE = re.compile(r'[^a-zA-Z0-9_-]')
_SLUG_DASHES_RE = re.compile(r'-{2,}')


def slugify(text: str) -> str:
    """Re-Implementation von TypeConverterUtils.slugify aus trekglobal-rest."""
    s = _SLUG_PUNCT_RE.sub("-", text)
    s = unicodedata.normalize("NFD", s)
    s = _SLUG_NONWORD_RE.sub("", s)
    s = s.lower()
    s = _SLUG_DASHES_RE.sub("-", s).strip("-")
    return s


class RestError(RuntimeError):
    pass


class IdempiereRest:
    def __init__(self, base_url: str, user: str, password: str,
                 client_id: int, role_id: int,
                 org_id: int = 0, warehouse_id: int | None = None,
                 language: str = "en_US",
                 verify_tls: bool = True):
        self.base = base_url.rstrip("/")
        self.user = user
        self.password = password
        self.client_id = int(client_id)
        self.role_id = int(role_id)
        self.org_id = int(org_id)
        self.warehouse_id = int(warehouse_id) if warehouse_id else None
        self.language = language
        self.token: str | None = None
        if verify_tls:
            self._ssl = None
        else:
            self._ssl = ssl.create_default_context()
            self._ssl.check_hostname = False
            self._ssl.verify_mode = ssl.CERT_NONE

    # ── Public ────────────────────────────────────────────────────────────

    def login(self) -> None:
        # `language` ist Pflicht für Skript-Identitäten: ohne explizite
        # Angabe wählt der REST-Endpoint die Sprache aus AD_Preference oder
        # AD_Client.AD_Language — meist non-en_US. Folge: Lookups gegen
        # /api/v1/windows liefern Übersetzungen ("Anlagenbuch" statt
        # "BXS Asset"), und der ods-Importer findet "Eingefügt" nicht als
        # Erfolgs-Marker. Mit "en_US" laufen alle Tools auf den englischen
        # Standardnamen — das ist die zuverlässige Konvention.
        params: dict = {
            "clientId": self.client_id,
            "roleId": self.role_id,
            "organizationId": self.org_id,
            "language": self.language,
        }
        if self.warehouse_id is not None:
            params["warehouseId"] = self.warehouse_id
        body = {
            "userName": self.user,
            "password": self.password,
            "parameters": params,
        }
        resp = self._raw("POST", "/api/v1/auth/tokens", body=body, auth=False)
        self.token = resp.get("token") or resp.get("access_token")
        if not self.token:
            raise RestError(f"Kein Token in Login-Response: {resp}")

    def get_models(self, table: str, query: dict | None = None) -> dict:
        path = f"/api/v1/models/{table.lower()}"
        if query:
            path += "?" + parse.urlencode(query, safe="$ ,")
        return self._raw("GET", path)

    def post_model(self, table: str, body: dict) -> dict:
        return self._raw("POST", f"/api/v1/models/{table.lower()}", body=body)

    def run_process(self, process_value: str,
                    parameters: dict | None = None,
                    record_id: int | None = None,
                    record_table: str | None = None) -> dict:
        # Trekglobal-REST: /api/v1/processes/{slug} mit record-id/table-name
        # im Body funktioniert universell (sowohl global als auch für
        # datensatzbezogene Prozesse). Der Models-Endpunkt /api/v1/models/
        # {table}/{id}/{slug} liefert für unsere Prozesse 405.
        slug = slugify(process_value)
        path = f"/api/v1/processes/{slug}"
        body: dict = {}
        if parameters:
            body.update(parameters)
        if record_id is not None:
            body["record-id"] = int(record_id)
        if record_table:
            body["table-name"] = record_table.lower()
        res = self._raw("POST", path, body=body)
        # Zweites Fehlerformat: HTTP 200 mit isError=true
        if isinstance(res, dict) and res.get("isError"):
            logs = res.get("logs", [])
            log_msgs = "\n".join(e.get("msg", "") for e in logs if e.get("msg"))
            raise RestError(
                f"Prozess {process_value} meldete Fehler: "
                f"{res.get('summary', '?')}\n{log_msgs}".strip()
            )
        return res

    # ── Internals ─────────────────────────────────────────────────────────

    def _raw(self, method: str, path: str, body: dict | None = None,
             auth: bool = True) -> dict:
        url = f"{self.base}{path}"
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if auth:
            if not self.token:
                raise RestError("Nicht eingeloggt — login() zuerst aufrufen.")
            headers["Authorization"] = f"Bearer {self.token}"
        req = request.Request(url, data=data, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=600, context=self._ssl) as r:
                raw = r.read()
        except error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(raw)
                msg = f"{detail.get('title', '?')}: {detail.get('detail', '')}"
            except json.JSONDecodeError:
                msg = raw[:500]
            raise RestError(f"{method} {path} → HTTP {e.code}: {msg}") from e
        except error.URLError as e:
            raise RestError(f"{method} {path} → {e.reason}") from e
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"raw": raw.decode("utf-8", errors="replace")}


def from_config(cfg: dict) -> IdempiereRest:
    for key in ("IDEMPIERE_URL", "IDEMPIERE_USER", "IDEMPIERE_PASSWORD",
                "IDEMPIERE_CLIENT_ID", "IDEMPIERE_ROLE_ID"):
        if not cfg.get(key):
            raise RestError(f"{key} fehlt in config.env")
    rest = IdempiereRest(
        base_url=cfg["IDEMPIERE_URL"],
        user=cfg["IDEMPIERE_USER"],
        password=cfg["IDEMPIERE_PASSWORD"],
        client_id=int(cfg["IDEMPIERE_CLIENT_ID"]),
        role_id=int(cfg["IDEMPIERE_ROLE_ID"]),
        org_id=int(cfg.get("IDEMPIERE_ORG_ID", "0")),
        warehouse_id=int(cfg["IDEMPIERE_WAREHOUSE_ID"]) if cfg.get("IDEMPIERE_WAREHOUSE_ID") else None,
        language=cfg.get("IDEMPIERE_LANGUAGE", "en_US"),
        verify_tls=cfg.get("IDEMPIERE_VERIFY_TLS", "0") not in ("0", "false", "False", ""),
    )
    rest.login()
    return rest
