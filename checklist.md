Hier ist die **Patch-Checkliste** (minimal, aber “hart”), so dass der 8787/8788-Split sauber bleibt und du keine stillen Leaks bekommst.

## A) Konfig & Defaults

* [ ] **Einheitlicher TTL-Wert** als Konstante/ENV (Single Source of Truth)

  * `SHERATAN_NODE_TTL_SEC=120` (Default 120)
  * optional: `SHERATAN_NODE_DEAD_SEC=600` (Default 5×TTL)

* [ ] **Token Pflicht** zentral konfiguriert

  * `SHERATAN_HUB_TOKEN=...`
  * `SHERATAN_HUB_TOKEN_REQUIRED=true` (prod default)

* [ ] **Zwei URLs** sauber getrennt

  * `HUB_CONTROL_URL=http://<hub>:8787`
  * `HUB_DATA_URL=http://<hub>:8788`

---

## B) Hub: Port Split (serve_gateway.py)

* [ ] `app_control = FastAPI(...)` und `app_data = FastAPI(...)` **getrennt** erstellen
* [ ] **Control Router nur auf app_control mounten**

  * `/health` (ohne Token, nur minimal Info)
  * `/api/hosts/heartbeat` (alias)
  * `/api/registry` (read-only)
* [ ] **Data Router nur auf app_data mounten**

  * `/mesh/submit_request`
  * `/mesh/pull_requests`
  * `/mesh/results/*`
  * `/admin/*` (falls existiert)
* [ ] **Expliziter “Leak Guard”**: auf *beiden* Apps je ein Catch-All, der falsche Pfade hart blockt

  * Beispiel-Logik: Wenn Request-Pfad zu “queue/admin” gehört und Port=8787 → 404/410 + Log “PORT_MISMATCH”
* [ ] Start beider Apps:

  * Windows-sicher: `if __name__ == "__main__":`
  * getrennte Prozessnamen + getrennte Ports
  * **getrennte Logfiles** pro Prozess (`hub_control.jsonl`, `hub_data.jsonl`) oder QueueHandler

---

## C) Hub Auth (TokenAuth Dependency)

* [ ] `TokenAuth` als Dependency (einmal implementieren, überall reuse)
* [ ] Support **beider Header** (robust):

  * `Authorization: Bearer <token>` **oder**
  * `X-Sheratan-Token: <token>`
* [ ] `/health` explizit **ohne Auth** lassen
* [ ] Für alle anderen Hub Endpoints:

  * `401/403` bei missing/invalid token
  * **loggt** remote addr + path + reason (`missing_token|bad_token`)
  * **niemals** Token im Log ausgeben (nur “present: true/false”)

---

## D) Registry Persistence & TTL (registry.py)

* [ ] Prüfen: ist Registry aktuell **in-memory dict**?
  → Wenn ja: **persistieren**, sonst klappt’s mit zwei Prozessen nicht sauber.
* [ ] Minimal robuste Persistence (empfohlen, kleinster Patch):

  * `data/registry.json` (atomic write + lock) **oder** SQLite
* [ ] `mark_stale_nodes(ttl_sec=ENV_TTL)` implementieren:

  * ONLINE wenn `now - last_seen <= ttl`
  * STALE wenn `ttl < delta <= dead`
  * optional DEAD/GC wenn `delta > dead`
* [ ] TTL Refresh deterministisch triggern:

  * beim `GET /api/registry` **immer** `mark_stale_nodes()` aufrufen
  * optional zusätzlich background tick
* [ ] last_seen Parsing robust (UTC Zulu, ISO8601)

---

## E) Clients: Sauber Host / Gemmaloop Worker

### E1) heartbeat.py (Sauber Host)

* [ ] Heartbeat an `HUB_CONTROL_URL` (8787)
* [ ] Token Header hinzufügen (Bearer oder X-Header)
* [ ] Timeout + Retry (kurz & capped)
* [ ] Wenn 401/403: log “AUTH_FAIL” + disable spam (backoff)

### E2) mesh_client.py (Gemmaloop Worker)

* [ ] Dual-port support:

  * `hub_control_url` für heartbeat/registry
  * `hub_data_url` für queue/results/admin
* [ ] Token auf **alle** requests
* [ ] Klare Fehlermeldung bei Port-Mismatch:

  * Wenn queue call → 404 auf 8787: “wrong port, expected data-plane 8788”

---

## F) Sauber Core: Debug Endpoint Lockdown (main.py)

* [ ] `/api/gateway/config` nur lokal:

  * allow nur `127.0.0.1` und `::1`
* [ ] Proxy-Sicherheit:

  * Wenn Reverse Proxy: entweder DEV-only via ENV (`GATEWAY_DEBUG_LOCALONLY=true`)
  * oder zusätzlich Token/BasicAuth (empfohlen, minimal)
* [ ] Nicht “silent fail”: bei remote call → 403 + log

---

## G) Tests (pytest / smoke)

* [ ] **Auth**

  * missing token → 401/403 auf 8787 registry/heartbeat
  * missing token → 401/403 auf 8788 queue/admin
* [ ] **Port Separation**

  * queue endpoint via 8787 → 404/410
  * heartbeat endpoint via 8788 → 404/410
* [ ] **TTL**

  * fake node last_seen älter als TTL → STALE erscheint im registry
* [ ] **Compatibility alias**

  * `/api/hosts/heartbeat` funktioniert identisch wie canonical endpoint
* [ ] **Integration**

  * Sauber Host + Gemmaloop Worker erscheinen beide korrekt im unified registry

---

## H) Rollout / Safety Switch (empfohlen)

* [ ] Übergangsschalter:

  * `HUB_TOKEN_REQUIRED=false` beim ersten Deploy (optional, nur kurz)
  * danach `true`
* [ ] Hub loggt klare Hinweise, wenn Token fehlt (damit du Clients schnell fixen kannst)

---

Wenn du willst, kann ich das als **DoD-Liste** in exakt der Reihenfolge “erst Hub → dann Clients → dann Tests” sortieren – aber so wie oben kannst du’s direkt abarbeiten, ohne dass dir 8787 wieder zur “Daten-Autobahn” wird.
