"""
Data verifier for extracted CV data.

Validates completeness and basic structure of extracted CV data.
"""

from __future__ import annotations

from typing import Any, Dict, List

from ..shared import VerificationResult
from .base import CVVerifier


class ExtractedDataVerifier(CVVerifier):
    """
    Verifier for extracted CV data completeness and validity.

    Checks that all required fields are present and non-empty,
    and warns about missing optional sections.
    """

    def verify(self, data: Dict[str, Any], **kwargs) -> VerificationResult:
        """
        Verify extracted CV data for completeness and validity.

        Args:
            data: Dictionary containing extracted CV data
            **kwargs: Not used for this verifier

        Returns:
            VerificationResult with errors for critical issues and warnings for optional issues
        """
        errs: List[str] = []
        warns: List[str] = []

        identity = data.get("identity", {}) or {}
        if (
            not identity.get("title")
            or not identity.get("full_name")
            or not identity.get("first_name")
            or not identity.get("last_name")
        ):
            errs.append("identity")

        sidebar = data.get("sidebar", {}) or {}

        expected_sidebar = [
            "languages",
            "tools",
            "industries",
            "spoken_languages",
            "academic_background",
        ]
        missing_sidebar = [s for s in expected_sidebar if not sidebar.get(s)]
        has_all_expected = all(s in sidebar for s in expected_sidebar)

        # Sidebar is an error only if absent or all expected sections are present but empty.
        if not sidebar or (
            has_all_expected and len(missing_sidebar) == len(expected_sidebar)
        ):
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
