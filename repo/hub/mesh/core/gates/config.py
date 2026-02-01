from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set


@dataclass(frozen=True)
class GateConfig:
    # canonical runtime zones
    #
    # The Sheratan core uses provenance.source_zone values like "api" for user/API
    # created jobs and may use "internal" for system-created jobs, as well as
    # "mesh"/"offgrid" for distributed execution. The original minimal gate config
    # used a different naming scheme ("input"/"output"/"narrative").
    #
    # To avoid schema drift (and the recurring "G0 fails for api" issue), we allow
    # both naming schemes. If you want stricter enforcement later, tighten this set
    # and update all producers to the same vocabulary.
    allowed_source_zones: Set[str] = frozenset({
        "api", "internal", "mesh", "offgrid", "quarantine",
        "input", "output", "narrative",
    })

    # EXEC boundary
    exec_zone: str = "input"

    # Allowlist kinds (capabilities)
    allowlisted_kinds: Set[str] = frozenset({
        "NOOP",
        "FILE_READ",
        "FILE_WRITE",
        "PATCH_APPLY",
        "RUN_TEST",
        # Planning / analysis (safe-by-default; still constrained by other gates)
        "agent_plan",
        "code_analysis",
        "documentation",
        "optimization",
        # Generic LLM call marker (if used by adapters)
        "llm_call",
        # "HTTP_GET",  # enable only if you really want network
    })

    # Kinds that are allowed only with operator ACK
    manual_only_kinds: Set[str] = frozenset({
        # Example: "PATCH_APPLY"  # if you want patching to require ack
    })

    # Explicitly forbidden kinds
    forbidden_kinds: Set[str] = frozenset({
        "SHELL_EXEC",
        "POWERSHELL_EXEC",
        "REGISTRY_EDIT",
        "DELETE_TREE",
        "SELF_MODIFY_LOCKCHECK",
        "EXEC_FROM_OUTPUT",
    })

    # Workspace rules
    project_root: Path = Path(".").resolve()
    workspace_roots: List[Path] = None  # default set in __post_init__ like behavior in factory

    # Forbidden path prefixes (relative)
    forbidden_rel_prefixes: List[str] = None

    # Escalation markers (hard stop)
    escalation_hard_markers: List[str] = None
    escalation_soft_markers: List[str] = None

    # Max patch ops or file changes
    max_patch_ops: int = 50


def default_gate_config(project_root: Path) -> GateConfig:
    pr = project_root.resolve()
    return GateConfig(
        project_root=pr,
        workspace_roots=[pr],  # simplest: project_root is workspace
        forbidden_rel_prefixes=[
            "build/",  # lockfile area (unless you explicitly allow reads elsewhere)
            ".git/",
            ".env",
            ".env.",
            "spec/",   # usually read-only; write should be blocked by path sandbox
        ],
        escalation_hard_markers=[
            "ignore policy",
            "override policy",
            "disable gate",
            "execute from output",
            "self modify",
            "rewrite rules",
            "no more questions",
            "final and irreversible",
        ],
        escalation_soft_markers=[
            "force",
            "bypass",
            "urgent override",
            "autonomous",
            "no confirmation",
        ],
    )
