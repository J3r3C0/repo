"""
webrelay/sdk_runtime_io.py

Runtime IO helpers for WebRelay/worker that uses sheratan-sdk primitives.
Keeps file naming + LCP envelope consistent across nodes.

Assumptions:
- narrative files: runtime/narrative/{job_id}.job.json
- output files:    runtime/output/{job_id}.result.json
"""
from __future__ import annotations

import os
import json
from typing import Any, Dict, Iterator, Optional, List

from sheratan_sdk.config import SheratanConfig
from sheratan_sdk.runtime_bridge import write_result
from sheratan_sdk.lcp import wrap_lcp


def iter_job_files(narrative_dir: Optional[str] = None) -> Iterator[str]:
    cfg = SheratanConfig.from_env()
    nd = narrative_dir or cfg.narrative_dir
    if not os.path.isdir(nd):
        return
    for fn in os.listdir(nd):
        if fn.endswith(".job.json"):
            yield os.path.join(nd, fn)


def read_job(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_lcp_result(
    job_id: str,
    result: Any,
    meta: Optional[Dict[str, Any]] = None,
    followups: Optional[List[Dict[str, Any]]] = None,
    output_dir: Optional[str] = None,
) -> str:
    cfg = SheratanConfig.from_env()
    od = output_dir or cfg.output_dir
    payload = wrap_lcp(result=result, meta=meta or {}, followups=followups or [])
    return write_result(job_id, payload, od)
