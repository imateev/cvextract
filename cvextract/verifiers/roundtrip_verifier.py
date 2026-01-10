"""
Roundtrip verifier for CV data structures.

Validates that two CV data structures are equivalent, with special
handling for certain fields like environment lists.
"""

from __future__ import annotations

import json
import re
from typing import Any, List

from ..shared import StepName, UnitOfWork, clean_text
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
                    cleaned = clean_text(part)
                    if cleaned:
                        tokens.append(cleaned.lower())
            else:
                tokens.append(clean_text(str(entry)).lower())
        return sorted(tokens)

    def _normalize_compare_text(self, text: str) -> str:
        cleaned = clean_text(text).lower()
        cleaned = re.sub(r"[^\w\s]", " ", cleaned)
        return clean_text(cleaned)

    def _normalize_sidebar_list(self, values: List[Any]) -> List[str]:
        tokens: List[str] = []
        for entry in values:
            if not isinstance(entry, str):
                entry = str(entry)
            parts = re.split(r"[\u2022•·,;]", entry)
            for part in parts:
                cleaned = self._normalize_compare_text(part).strip("()")
                if cleaned:
                    tokens.append(cleaned)
        return sorted(tokens)

    def _normalize_bullet_texts(self, bullets: List[Any]) -> List[str]:
        tokens: List[str] = []
        for entry in bullets:
            text = str(entry)
            text = re.sub(r"^(?:[•·*-]|\-\-|->|→)\s*", "", text).strip()
            cleaned = self._normalize_compare_text(text)
            if cleaned:
                tokens.append(cleaned)
        return tokens

    def _bullets_in_description(self, bullets: List[Any], description: str) -> bool:
        desc_norm = self._normalize_compare_text(description)
        if not desc_norm:
            return False
        for bullet in self._normalize_bullet_texts(bullets):
            if bullet and bullet not in desc_norm:
                return False
        return True

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
            if (
                "description" in a_keys
                and "bullets" in a_keys
                and "description" in b_keys
                and "bullets" in b_keys
            ):
                a_bullets = a.get("bullets") or []
                b_bullets = b.get("bullets") or []
                if (
                    a_bullets
                    and not b_bullets
                    and self._bullets_in_description(a_bullets, str(b.get("description", "")))
                ) or (
                    b_bullets
                    and not a_bullets
                    and self._bullets_in_description(b_bullets, str(a.get("description", "")))
                ):
                    a_keys.discard("description")
                    a_keys.discard("bullets")
                    b_keys.discard("description")
                    b_keys.discard("bullets")
            for missing in sorted(a_keys - b_keys):
                if isinstance(a.get(missing), list) and not a.get(missing):
                    continue
                errors.append(f"missing key in new at {path or '<root>'}.{missing}")
            for extra in sorted(b_keys - a_keys):
                if isinstance(b.get(extra), list) and not b.get(extra):
                    continue
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
            if (
                path.startswith("sidebar.")
                and all(isinstance(x, str) for x in a)
                and all(isinstance(x, str) for x in b)
            ):
                a_norm = self._normalize_sidebar_list(a)
                b_norm = self._normalize_sidebar_list(b)
                if a_norm != b_norm:
                    errors.append(
                        f"list mismatch at {path or '<root>'}: {a_norm} vs {b_norm}"
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

        if isinstance(a, str):
            a_norm = self._normalize_compare_text(a)
            b_norm = self._normalize_compare_text(b)
            if a_norm != b_norm:
                errors.append(
                    f"value mismatch at {path or '<root>'}: {a_norm!r} vs {b_norm!r}"
                )
            return

        # Primitive or other immutable
        if a != b:
            errors.append(f"value mismatch at {path or '<root>'}: {a!r} vs {b!r}")
