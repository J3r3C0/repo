Go A3 ✅ — und Stand ist gespeichert.

## Implementierungsplan v2.7 — Track A3: Policy & Response Layer (auf A2)

### Ziel

Aus **A2-Signalen** (OK/MISSING/DRIFT/SPOOF_SUSPECT + health YELLOW) werden **kontrollierte Reaktionen**:

* **keine** Downtime
* **keine** “False Positive”-Katastrophen
* erst **Soft-Policy**, dann optional **Hard-Policy**

---

## A3.1 Policy Engine (Signal → Action)

**Neu:** `core/policy_engine.py`

Input:

* node_id
* attestation_status
* drift_count / spoof_count
* last_change_utc
* remote_addr (optional)

Output (signal-only default):

```json
{
  "policy": "ALLOW|WARN|QUARANTINE",
  "reason": "DRIFT|SPOOF_SUSPECT|MISSING",
  "cooldown_sec": 300,
  "actions": ["AUDIT", "ALERT"]
}
```

**Default Mapping (sicher):**

* `OK` / `MISSING` → `ALLOW`
* `DRIFT` → `WARN` (kein Block, aber Alert möglich)
* `SPOOF_SUSPECT` → `QUARANTINE` (Soft-Quarantine: markieren + throttle, kein Hard-Block)

---

## A3.2 Quarantine State (Soft)

**DB/Storage:** erweitere hosts record um:

* `policy_state`: `NORMAL|WARN|QUARANTINED`
* `policy_until_utc`
* `policy_reason`
* `policy_hits` (counter)

**Wirkung (ohne zu brechen):**

* QUARANTINED nodes bleiben sichtbar/online,
* aber Data-Plane interactions (falls vorhanden) bekommen **defer_ms**/**low priority**/**rate limit**.

> Wichtig: In A3 **noch kein 403**, außer du willst es explizit als Hard-Mode.

---

## A3.3 Rate-Limits / Backoff für Risky Nodes

**Neu/Modify:** `core/risk_throttle.py` oder im Hub-Data-Plane handler:

* Wenn `policy_state=QUARANTINED`:

  * `pull_requests` → `defer_ms=2000..10000` (jitter)
  * `submit_results` → allowed, aber extra audit
* Wenn `WARN`:

  * nur audit + alert, sonst normal

---

## A3.4 Alerts (Observability Hook)

* schreibe `POLICY_WARN` / `POLICY_QUARANTINE` nach `alerts.jsonl`
* metrics:

  * `policy_warn_1m`
  * `policy_quarantine_1m`
  * `policy_quarantine_active`

---

## A3.5 Admin Override (Operations)

**Optionale Endpoints (localhost-only + token):**

* `POST /api/policy/quarantine/{node_id}` (set)
* `POST /api/policy/release/{node_id}` (clear)
* `GET /api/policy/state` (overview)

---

## Verification (A3)

Automated:

* T1: DRIFT ⇒ policy WARN, alert logged
* T2: SPOOF_SUSPECT ⇒ policy QUARANTINE, defer_ms increases
* T3: release override ⇒ back to NORMAL
* T4: no regression: normal nodes unaffected

Manual:

* run verify script
* check `alerts.jsonl`, policy metrics, host policy_state in DB

---

## DoD (A3 abgeschlossen)

* A2 Signals triggern deterministische Policy Decisions
* QUARANTINE wirkt **ohne** Systembruch (soft)
* Alerts + Metrics vollständig
* Override vorhanden oder bewusst deferred (dein Call)

Wenn du willst, gehe ich als nächstes direkt in **A3.1 Minimal Patch Set** (nur Policy Engine + Alerts, ohne Quarantine), oder in **A3 Full** (inkl. Quarantine + Override).
