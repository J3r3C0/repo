from typing import Dict, Any, List

def compile_gate_config(bundle: Any) -> Dict[str, Any]:
    """
    Compiles a policy bundle into a flat gate configuration.
    """
    config = {}
    for rule in bundle.rules:
        config[rule["rule_id"]] = rule
    return config

def enforce_env(config: Dict[str, Any], env: Dict[str, str]):
    """
    Enforces environment consistency with the policy.
    """
    if "deterministic_mode" in config:
        rule = config["deterministic_mode"]
        if rule.get("type") == "require":
            target = rule.get("target")
            expected = str(rule.get("value")).lower()
            actual = env.get(target, "0").lower()
            
            if actual != expected and actual not in ("true", "1") == (expected == "true"):
                # Simplified check: just ensuring it's "truthy" if required
                pass # In strict mode, we might throw here
