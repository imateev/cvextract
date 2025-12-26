"""
Verification helpers for extracted and rendered CV data.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from .shared import VerificationResult

# ------------------------- Extraction verification -------------------------

def verify_extracted_data(data: dict) -> VerificationResult:
    """
    Verify extracted CV data for completeness and validity.
    Returns issues without logging (so callers can log a single line per file).
    """
    errs: List[str] = []
    warns: List[str] = []

    identity = data.get("identity", {}) or {}
    if not identity.get("title") or not identity.get("full_name") or not identity.get("first_name") or not identity.get("last_name"):
        errs.append("identity")

    sidebar = data.get("sidebar", {}) or {}

    expected_sidebar = ["languages", "tools", "industries", "spoken_languages", "academic_background"]
    missing_sidebar = [s for s in expected_sidebar if not sidebar.get(s)]
    has_all_expected = all(s in sidebar for s in expected_sidebar)

    # Sidebar is an error only if absent or all expected sections are present but empty.
    if not sidebar or (has_all_expected and len(missing_sidebar) == len(expected_sidebar)):
        errs.append("sidebar")
    elif missing_sidebar:
        warns.append("missing sidebar: " + ", ".join(missing_sidebar))

    experiences = data.get("experiences", []) or []
    if not experiences:
        errs.append("experiences_empty")

    has_any_bullets = False
    has_any_environment = False
    issue_set = set()
    for exp in experiences:
        heading = (exp.get("heading") or "").strip()
        desc = (exp.get("description") or "").strip()
        bullets = exp.get("bullets") or []
        env = exp.get("environment")
        if not heading:
            issue_set.add("missing heading")
        if not desc:
            issue_set.add("missing description")
        if bullets:
            has_any_bullets = True
        if env:
            has_any_environment = True
        if env is not None and not isinstance(env, list):
            warns.append("invalid environment format")

    if not has_any_bullets and not has_any_environment:
        warns.append("no bullets or environment in any experience")

    if issue_set:
        warns.append("incomplete: " + "; ".join(sorted(issue_set)))

    ok = not errs
    return VerificationResult(ok=ok, errors=errs, warnings=warns)

# ------------------------- Roundtrip comparison -------------------------

@dataclass(frozen=True)
class DiffResult:
    ok: bool
    errors: List[str]


def _diff(a: Any, b: Any, path: str, errors: List[str]) -> None:
    # Strict type match
    if type(a) is not type(b):
        errors.append(f"type mismatch at {path or '<root>'}: {type(a).__name__} vs {type(b).__name__}")
        return

    if isinstance(a, dict):
        a_keys = set(a.keys())
        b_keys = set(b.keys())
        for missing in sorted(a_keys - b_keys):
            errors.append(f"missing key in new at {path or '<root>'}.{missing}")
        for extra in sorted(b_keys - a_keys):
            errors.append(f"extra key in new at {path or '<root>'}.{extra}")
        for k in sorted(a_keys & b_keys):
            _diff(a[k], b[k], f"{path}.{k}" if path else k, errors)
        return

    if isinstance(a, list):
        if len(a) != len(b):
            errors.append(f"list length mismatch at {path or '<root>'}: {len(a)} vs {len(b)}")
            return
        for idx, (x, y) in enumerate(zip(a, b)):
            _diff(x, y, f"{path}[{idx}]" if path else f"[{idx}]", errors)
        return

    # Primitive or other immutable
    if a != b:
        errors.append(f"value mismatch at {path or '<root>'}: {a!r} vs {b!r}")


def compare_data_structures(original: Dict[str, Any], new: Dict[str, Any]) -> VerificationResult:
    """Deep-compare two data structures and report mismatches as errors."""
    errs: List[str] = []
    _diff(original, new, "", errs)
    return VerificationResult(ok=not errs, errors=errs, warnings=[])


def compare_json_files(original_json: Path, roundtrip_json: Path) -> VerificationResult:
    with original_json.open("r", encoding="utf-8") as f:
        orig = json.load(f)
    with roundtrip_json.open("r", encoding="utf-8") as f:
        new = json.load(f)
    return compare_data_structures(orig, new)
