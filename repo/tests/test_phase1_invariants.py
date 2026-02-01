from __future__ import annotations

from pathlib import Path
import os
import pytest

from core.policy.loader import load_policy_bundle
from core.policy.gates import compile_gate_config, enforce_env


def test_policy_bundle_valid_and_hash_ok():
    repo = Path(__file__).resolve().parents[1]
    bundle_path = repo / "policies" / "active" / "sheratan-phase1-core.policy.json"
    schema_path = repo / "schemas" / "policy_bundle_v1.json"

    if not bundle_path.exists():
        pytest.skip("Policy bundle not yet created")

    # strict=True ensures hash mismatch fails
    bundle = load_policy_bundle(bundle_path=bundle_path, schema_path=schema_path, strict=True)
    cfg = compile_gate_config(bundle)

    env = dict(os.environ)
    env["DETERMINISTIC_MODE"] = "1"
    enforce_env(cfg, env)


def test_deterministic_mode_must_be_on():
    repo = Path(__file__).resolve().parents[1]
    bundle_path = repo / "policies" / "active" / "sheratan-phase1-core.policy.json"
    schema_path = repo / "schemas" / "policy_bundle_v1.json"

    if not bundle_path.exists():
        pytest.skip("Policy bundle not yet created")

    bundle = load_policy_bundle(bundle_path=bundle_path, schema_path=schema_path, strict=True)
    cfg = compile_gate_config(bundle)

    env = dict(os.environ)
    env["DETERMINISTIC_MODE"] = "0"

    from core.policy.loader import PolicyError
    with pytest.raises(PolicyError):
        enforce_env(cfg, env)
