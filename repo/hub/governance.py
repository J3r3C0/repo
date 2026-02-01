# core/policy_engine.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, Literal


# NOTE (Integration Point):
# This PolicyEngine is meant to be called from the EXISTING heartbeat flow in core/main.py
# at the already-located heartbeat endpoint handler (e.g. "the heartbeat endpoint in core/main.py:923").
# Do NOT hardcode endpoint paths here. Reference the handler by location in core/main.py.


GovState = Literal["NORMAL", "WARN", "QUARANTINED"]
GovReason = Literal["NONE", "DRIFT", "SPOOF_SUSPECT", "ADMIN"]


@dataclass(frozen=True)
class GovernanceDecision:
    state: GovernanceState
    reason: GovernanceReason
    until_utc: Optional[str]  # ISO8601 string, or None
    cooldown_sec: int
    actions: tuple[str, ...]  # e.g. ("AUDIT", "ALERT", "THROTTLE")
    defer_ms: Optional[int] = None  # soft enforcement hint (optional)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _is_active_until(until_utc: Optional[str], now: datetime) -> bool:
    dt = _parse_iso(until_utc)
    if not dt:
        return False
    return dt > now


class GovernanceEngine:
    """
    Track A3 Governance Engine (v2.7+)

    Inputs:
      - host record (from storage): policy_state/policy_until_utc/policy_hits + A2 attestation fields
      - attestation_status (A2): OK|MISSING|DRIFT|SPOOF_SUSPECT
    Output:
      - PolicyDecision (NORMAL/WARN/QUARANTINED) with optional until + actions + optional defer_ms.

    IMPORTANT:
      - Soft by default: does not mandate 403 blocks.
      - Escalation is based on policy_hits (persisted in DB in v2.7.1).
        If v2.7 (stateless), engine still outputs decisions, but TTL escalation won't persist.
    """

    def __init__(
        self,
        quarantine_base_minutes: int = 10,
        quarantine_escalate_1h_minutes: int = 30,
        quarantine_escalate_24h_minutes: int = 120,
        warn_auto_clear_minutes: int = 10,
        soft_defer_ms_min: int = 2000,
        soft_defer_ms_max: int = 10000,
    ) -> None:
        self.quarantine_base_minutes = quarantine_base_minutes
        self.quarantine_escalate_1h_minutes = quarantine_escalate_1h_minutes
        self.quarantine_escalate_24h_minutes = quarantine_escalate_24h_minutes
        self.warn_auto_clear_minutes = warn_auto_clear_minutes
        self.soft_defer_ms_min = soft_defer_ms_min
        self.soft_defer_ms_max = soft_defer_ms_max

    def decide(
        self,
        host: Dict[str, Any],
        attestation_status: str,
        now_utc: Optional[datetime] = None,
    ) -> PolicyDecision:
        now = now_utc or _utcnow()

        # Current persisted state
        cur_state: GovState = (host.get("policy_state") or "NORMAL")
        cur_until: Optional[str] = host.get("policy_until_utc")
        cur_hits: int = int(host.get("policy_hits") or 0)

        # If we are currently quarantined and TTL still active, keep it (idempotent behavior)
        if cur_state == "QUARANTINED" and _is_active_until(cur_until, now):
            return PolicyDecision(
                state="QUARANTINED",
                reason=(host.get("policy_reason") or "SPOOF_SUSPECT"),
                until_utc=cur_until,
                cooldown_sec=60,
                actions=("AUDIT", "THROTTLE"),
                defer_ms=self._defer_ms(cur_hits),
            )

        # If we are currently WARN and want auto-clear behavior:
        if cur_state == "WARN":
            # If WARN is stale (no recent change), allow auto-clear (soft)
            updated = _parse_iso(host.get("policy_updated_utc"))
            if updated and (now - updated) > timedelta(minutes=self.warn_auto_clear_minutes):
                return PolicyDecision(
                    state="NORMAL",
                    reason="NONE",
                    until_utc=None,
                    cooldown_sec=0,
                    actions=("AUDIT",),
                )

        # Map A2 signals to A3 decisions
        status = (attestation_status or "MISSING").upper()

        if status in ("OK", "MISSING"):
            return PolicyDecision(
                state="NORMAL",
                reason="NONE",
                until_utc=None,
                cooldown_sec=0,
                actions=(),  # no noise
            )

        if status == "DRIFT":
            # WARN only (no throttle by default)
            return PolicyDecision(
                state="WARN",
                reason="DRIFT",
                until_utc=None,
                cooldown_sec=300,
                actions=("AUDIT", "ALERT"),
            )

        if status == "SPOOF_SUSPECT":
            # Soft quarantine with TTL + throttle hint
            ttl_minutes = self._quarantine_minutes(cur_hits, now, host)
            until = now + timedelta(minutes=ttl_minutes)
            return PolicyDecision(
                state="QUARANTINED",
                reason="SPOOF_SUSPECT",
                until_utc=_iso(until),
                cooldown_sec=300,
                actions=("AUDIT", "ALERT", "THROTTLE"),
                defer_ms=self._defer_ms(cur_hits + 1),
            )

        # Unknown statuses: treat as WARN (safe)
        return PolicyDecision(
            state="WARN",
            reason="DRIFT",
            until_utc=None,
            cooldown_sec=300,
            actions=("AUDIT",),
        )

    def _quarantine_minutes(self, cur_hits: int, now: datetime, host: Dict[str, Any]) -> int:
        """
        Simple escalation policy:
          - first quarantine: base (10m)
          - repeated soon: 30m / 120m

        If you later add time-window logic (1h/24h), store last_quarantine_utc or use policy_updated_utc.
        For now, we approximate using policy_hits + recency.
        """
        updated = _parse_iso(host.get("policy_updated_utc"))
        if updated:
            age = now - updated
            if age <= timedelta(hours=1):
                return self.quarantine_escalate_1h_minutes
            if age <= timedelta(hours=24):
                return self.quarantine_escalate_24h_minutes

        if cur_hits <= 0:
            return self.quarantine_base_minutes

        # fallback escalation by hits
        if cur_hits == 1:
            return self.quarantine_escalate_1h_minutes
        return self.quarantine_escalate_24h_minutes

    def _defer_ms(self, hits: int) -> int:
        """
        Soft throttle hint. Increases with hits, capped.
        Deterministic (no randomness), so tests stay stable.
        """
        # base + step
        base = self.soft_defer_ms_min
        step = 1500
        v = base + max(0, hits - 1) * step
        return min(v, self.soft_defer_ms_max)
