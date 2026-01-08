"""
Schema verifier for CV data.

Validates CV data against the JSON schema defined in cv_schema.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..shared import UnitOfWork
from .base import CVVerifier


class CVSchemaVerifier(CVVerifier):
    """
    Verifier that validates CV data against cv_schema.json.

    Uses basic structure validation to ensure data conforms to the schema.
    For full JSON Schema validation, consider using a library like jsonschema.
    """

    def __init__(self, schema_path: Optional[Path] = None):
        """
        Initialize the schema verifier.

        Args:
            schema_path: Path to cv_schema.json. If None, uses default location.
        """
        if schema_path is None:
            # Default to cv_schema.json in contracts directory
            schema_path = Path(__file__).parent.parent / "contracts" / "cv_schema.json"

        self.schema_path = schema_path
        self._schema: Optional[Dict[str, Any]] = None

    def _load_schema(self) -> Dict[str, Any]:
        """Load the CV schema from file."""
        if self._schema is None:
            with self.schema_path.open("r", encoding="utf-8") as f:
                self._schema = json.load(f)
        return self._schema

    def verify(self, work: UnitOfWork) -> UnitOfWork:
        """
        Verify CV data against the schema.

        Returns:
            Updated UnitOfWork with validation results
        """
        step = work.resolve_verification_step()
        data, errs = self._load_output_json(work, step)
        if data is None:
            return self._record(work, errs, [])

        schema = self._load_schema()
        errs: List[str] = []
        warns: List[str] = []

        # Check required top-level fields
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in data:
                errs.append(f"missing required field: {field}")

        # Validate identity if present
        if "identity" in data:
            identity = data["identity"]
            identity_props = schema.get("properties", {}).get("identity", {})
            identity_required = identity_props.get("required", [])
            for field in identity_required:
                if not identity or field not in identity:
                    errs.append(f"identity missing required field: {field}")
                elif not isinstance(identity.get(field), str) or not identity.get(
                    field
                ):
                    errs.append(f"identity.{field} must be a non-empty string")

        # Validate sidebar if present
        if "sidebar" in data:
            sidebar = data["sidebar"]
            if sidebar is not None and not isinstance(sidebar, dict):
                errs.append("sidebar must be an object")

        # Validate overview if present
        if "overview" in data:
            overview = data["overview"]
            if overview is not None and not isinstance(overview, str):
                errs.append("overview must be a string")

        # Validate experiences if present
        if "experiences" in data:
            experiences = data["experiences"]
            if not isinstance(experiences, list):
                errs.append("experiences must be an array")
            else:
                for idx, exp in enumerate(experiences):
                    if not isinstance(exp, dict):
                        errs.append(f"experiences[{idx}] must be an object")
                        continue

                    # Check required fields in experience
                    if "heading" not in exp:
                        errs.append(
                            f"experiences[{idx}] missing required field: heading"
                        )
                    elif not isinstance(exp["heading"], str):
                        errs.append(f"experiences[{idx}].heading must be a string")

                    if "description" not in exp:
                        errs.append(
                            f"experiences[{idx}] missing required field: description"
                        )
                    elif not isinstance(exp["description"], str):
                        errs.append(f"experiences[{idx}].description must be a string")

                    # Check optional fields have correct types
                    if "bullets" in exp:
                        if not isinstance(exp["bullets"], list):
                            errs.append(f"experiences[{idx}].bullets must be an array")
                        elif exp["bullets"] and not all(
                            isinstance(b, str) for b in exp["bullets"]
                        ):
                            errs.append(
                                f"experiences[{idx}].bullets items must be strings"
                            )

                    if "environment" in exp:
                        env = exp["environment"]
                        if env is not None and not isinstance(env, list):
                            errs.append(
                                f"experiences[{idx}].environment must be an array or null"
                            )
                        elif (
                            isinstance(env, list)
                            and env
                            and not all(isinstance(e, str) for e in env)
                        ):
                            errs.append(
                                f"experiences[{idx}].environment items must be strings"
                            )

        return self._record(work, errs, warns)

    def _load_output_json(
        self, work: UnitOfWork, step: "StepName"
    ) -> tuple[Dict[str, Any] | None, List[str]]:
        output_path = work.get_step_output(step)
        if output_path is None:
            return None, ["verification input JSON path is not set"]
        if not output_path.exists():
            return None, [f"verification input JSON not found: {output_path}"]
        try:
            with output_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            return None, [f"verification input JSON unreadable: {type(e).__name__}"]
        if not isinstance(data, dict):
            return None, ["verification input JSON must be an object"]
        return data, []
