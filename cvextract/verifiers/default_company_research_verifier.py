"""
Default company research verifier.

Validates company profile data against the JSON schema defined in research_schema.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..shared import VerificationResult
from .base import CVVerifier


class CompanyProfileVerifier(CVVerifier):
    """
    Verifier that validates company profile data against research_schema.json.

    Uses basic structure validation to ensure data conforms to the schema.
    For full JSON Schema validation, consider using a library like jsonschema.
    """

    def __init__(self, schema_path: Optional[Path] = None):
        """
        Initialize the company profile schema verifier.

        Args:
            schema_path: Path to research_schema.json. If None, uses default location.
        """
        if schema_path is None:
            # Default to research_schema.json in contracts directory
            schema_path = (
                Path(__file__).parent.parent / "contracts" / "research_schema.json"
            )

        self.schema_path = schema_path
        self._schema: Optional[Dict[str, Any]] = None

    def _load_schema(self) -> Dict[str, Any]:
        """Load the company profile schema from file."""
        if self._schema is None:
            with self.schema_path.open("r", encoding="utf-8") as f:
                self._schema = json.load(f)
        return self._schema

    def verify(self, **kwargs) -> VerificationResult:
        """
        Verify company profile data against the schema.

        Args:
            **kwargs: Must contain 'data' (Dict[str, Any]) with company profile data to validate

        Returns:
            VerificationResult with validation results
        """
        data = kwargs.get("data")
        if data is None:
            raise ValueError("CompanyProfileVerifier requires 'data' parameter")
        schema = self._load_schema()
        errs: List[str] = []
        warns: List[str] = []

        # Check required top-level fields
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in data:
                errs.append(f"missing required field: {field}")

        # Validate name if present
        if "name" in data:
            if not isinstance(data["name"], str):
                errs.append("name must be a string")
            elif not data["name"]:
                errs.append("name must be a non-empty string")

        # Validate description if present
        if "description" in data:
            if data["description"] is not None and not isinstance(
                data["description"], str
            ):
                errs.append("description must be a string or null")

        # Validate domains (required)
        if "domains" in data:
            domains = data["domains"]
            if not isinstance(domains, list):
                errs.append("domains must be an array")
            else:
                if not domains:
                    errs.append("domains must have at least one item")
                elif not all(isinstance(d, str) for d in domains):
                    errs.append("domains items must be strings")

        # Validate technology_signals if present
        if "technology_signals" in data:
            signals = data["technology_signals"]
            if not isinstance(signals, list):
                errs.append("technology_signals must be an array")
            else:
                for idx, signal in enumerate(signals):
                    if not isinstance(signal, dict):
                        errs.append(f"technology_signals[{idx}] must be an object")
                        continue

                    # Check required field in signal
                    if "technology" not in signal:
                        errs.append(
                            f"technology_signals[{idx}] missing required field: technology"
                        )
                    elif not isinstance(signal["technology"], str):
                        errs.append(
                            f"technology_signals[{idx}].technology must be a string"
                        )

                    # Validate optional fields
                    if "category" in signal and signal["category"] is not None:
                        if not isinstance(signal["category"], str):
                            errs.append(
                                f"technology_signals[{idx}].category must be a string or null"
                            )

                    if "interest_level" in signal:
                        if signal["interest_level"] not in [
                            None,
                            "low",
                            "medium",
                            "high",
                        ]:
                            errs.append(
                                f"technology_signals[{idx}].interest_level must be 'low', 'medium', 'high', or null"
                            )

                    if "confidence" in signal:
                        conf = signal["confidence"]
                        if not isinstance(conf, (int, float)) or conf < 0 or conf > 1:
                            errs.append(
                                f"technology_signals[{idx}].confidence must be a number between 0 and 1"
                            )

                    if "signals" in signal:
                        sigs = signal["signals"]
                        if not isinstance(sigs, list):
                            errs.append(
                                f"technology_signals[{idx}].signals must be an array"
                            )
                        elif not all(isinstance(s, str) for s in sigs):
                            errs.append(
                                f"technology_signals[{idx}].signals items must be strings"
                            )

                    if "notes" in signal and signal["notes"] is not None:
                        if not isinstance(signal["notes"], str):
                            errs.append(
                                f"technology_signals[{idx}].notes must be a string or null"
                            )

        # Validate industry_classification if present
        if "industry_classification" in data:
            ic = data["industry_classification"]
            if ic is not None and not isinstance(ic, dict):
                errs.append("industry_classification must be an object or null")
            elif isinstance(ic, dict):
                if (
                    "naics" in ic
                    and ic["naics"] is not None
                    and not isinstance(ic["naics"], str)
                ):
                    errs.append(
                        "industry_classification.naics must be a string or null"
                    )
                if (
                    "sic" in ic
                    and ic["sic"] is not None
                    and not isinstance(ic["sic"], str)
                ):
                    errs.append("industry_classification.sic must be a string or null")

        # Validate founded_year if present
        if "founded_year" in data:
            year = data["founded_year"]
            if year is not None:
                if not isinstance(year, int) or year < 1600 or year > 2100:
                    errs.append("founded_year must be an integer between 1600 and 2100")

        # Validate headquarters if present
        if "headquarters" in data:
            hq = data["headquarters"]
            if hq is not None and not isinstance(hq, dict):
                errs.append("headquarters must be an object or null")
            elif isinstance(hq, dict):
                if "country" not in hq:
                    errs.append("headquarters missing required field: country")
                if (
                    "city" in hq
                    and hq["city"] is not None
                    and not isinstance(hq["city"], str)
                ):
                    errs.append("headquarters.city must be a string or null")
                if (
                    "state" in hq
                    and hq["state"] is not None
                    and not isinstance(hq["state"], str)
                ):
                    errs.append("headquarters.state must be a string or null")
                if (
                    "country" in hq
                    and hq["country"] is not None
                    and not isinstance(hq["country"], str)
                ):
                    errs.append("headquarters.country must be a string or null")

        # Validate company_size if present
        if "company_size" in data:
            size = data["company_size"]
            if size not in [None, "solo", "small", "medium", "large", "enterprise"]:
                errs.append(
                    "company_size must be 'solo', 'small', 'medium', 'large', 'enterprise', or null"
                )

        # Validate employee_count if present
        if "employee_count" in data:
            count = data["employee_count"]
            if count is not None:
                if not isinstance(count, int) or count < 1:
                    errs.append("employee_count must be a positive integer or null")

        # Validate ownership_type if present
        if "ownership_type" in data:
            ot = data["ownership_type"]
            if ot not in [None, "private", "public", "nonprofit", "government"]:
                errs.append(
                    "ownership_type must be 'private', 'public', 'nonprofit', 'government', or null"
                )

        # Validate website if present
        if "website" in data:
            if data["website"] is not None and not isinstance(data["website"], str):
                errs.append("website must be a string or null")

        return VerificationResult(errors=errs, warnings=warns)
