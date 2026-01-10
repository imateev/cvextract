"""
Roundtrip verifier for CV data structures.

Validates that two CV data structures are equivalent, with special
handling for certain fields like environment lists.
"""

from __future__ import annotations

import json
import re
from typing import Any, List

from ..shared import StepName, UnitOfWork
from .base import CVVerifier


class RoundtripVerifier(CVVerifier):
    """
    Verifier for comparing two CV data structures.

    Performs deep comparison with special handling for environment fields
    which may use different separators but contain the same content.
    """

    def verify(self, work: UnitOfWork) -> UnitOfWork:
        """
        Compare two CV data structures.

        Returns:
            Updated UnitOfWork with errors for differences
        """
        extracted = work.ensure_step_status(StepName.Extract)
        data, data_errs = self._load_json(extracted.output, "roundtrip source JSON")

        roundtrip_comparer = work.ensure_step_status(StepName.VerifyRender)
        target_data, target_errs = self._load_json(
            roundtrip_comparer.input, "roundtrip target JSON"
        )
        if data is None or target_data is None:
            return self._record(work, data_errs + target_errs, [])

        errs: List[str] = []
        self._diff(data, target_data, "", errs)
        return self._record(work, errs, [])

    def _load_json(self, path: Any, label: str) -> tuple[Any | None, List[str]]:
        if path is None:
            return None, [f"{label} path is not set"]
        if not hasattr(path, "exists") or not path.exists():
            return None, [f"{label} not found: {path}"]
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            return None, [f"{label} unreadable: {type(e).__name__}"]
        return data, []

    def _normalize_environment_list(self, env: List[Any]) -> List[str]:
        """Normalize environment lists by splitting on common separators and lowercasing."""
        tokens: List[str] = []
        for entry in env:
            if isinstance(entry, str):
                parts = re.split(r"[\u2022•·,;]|\s•\s|\s-\s|•", entry)
                for part in parts:
                    cleaned = part.strip()
                    if cleaned:
                        tokens.append(cleaned.lower())
            else:
                tokens.append(str(entry).strip().lower())
        return sorted(tokens)

    def _is_environment_path(self, path: str) -> bool:
        """Check if the current path is an environment field."""
        return path.endswith("environment")

    def _diff(self, a: Any, b: Any, path: str, errors: List[str]) -> None:
        """Recursively compare two values and record differences."""
        # Strict type match
        if type(a) is not type(b):
            errors.append(
                f"type mismatch at {path or '<root>'}: {type(a).__name__} vs {type(b).__name__}"
            )
            return

        if isinstance(a, dict):
            a_keys = set(a.keys())
            b_keys = set(b.keys())
            for missing in sorted(a_keys - b_keys):
                errors.append(f"missing key in new at {path or '<root>'}.{missing}")
            for extra in sorted(b_keys - a_keys):
                errors.append(f"extra key in new at {path or '<root>'}.{extra}")
            for k in sorted(a_keys & b_keys):
                self._diff(a[k], b[k], f"{path}.{k}" if path else k, errors)
            return

        if isinstance(a, list):
            if self._is_environment_path(path):
                a_norm = self._normalize_environment_list(a)
                b_norm = self._normalize_environment_list(b)
                if a_norm != b_norm:
                    errors.append(
                        f"environment mismatch at {path or '<root>'}: {a_norm} vs {b_norm}"
                    )
                return
            if len(a) != len(b):
                errors.append(
                    f"list length mismatch at {path or '<root>'}: {len(a)} vs {len(b)}"
                )
                return
            for idx, (x, y) in enumerate(zip(a, b)):
                self._diff(x, y, f"{path}[{idx}]" if path else f"[{idx}]", errors)
            return

        # Primitive or other immutable
        if a != b:
            errors.append(f"value mismatch at {path or '<root>'}: {a!r} vs {b!r}")
