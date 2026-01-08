"""
DOCX-based CV renderer implementation.

Renders structured CV data to Word .docx files using docxtpl templates.
"""

from __future__ import annotations

import json

from docxtpl import DocxTemplate

from ..shared import StepName, UnitOfWork, sanitize_for_xml_in_obj
from .base import CVRenderer


class DocxCVRenderer(CVRenderer):
    """
    CV renderer for Microsoft Word .docx files.

    This implementation:
    - Uses docxtpl for template rendering
    - Sanitizes content for XML safety before rendering
    - Supports auto-escaping for security
    - Returns the UnitOfWork with rendered output populated
    """

    def render(self, work: UnitOfWork) -> UnitOfWork:
        """
        Render CV data to a .docx file using a docxtpl template.

        Args:
            work: UnitOfWork containing render configuration and paths.

        Returns:
            UnitOfWork with rendered output populated

        Raises:
            FileNotFoundError: If the template file does not exist
            Exception: For rendering or template errors
        """
        if not work.config.render:
            raise ValueError("Render configuration is missing")

        status = work.ensure_step_status(StepName.Render)
        if status.output is None:
            raise ValueError("Render output path is not set")

        if status.input is None:
            raise ValueError("Render input path is not set")

        template_path = work.config.render.template
        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")

        if not template_path.is_file():
            raise ValueError(f"Template path is not a file: {template_path}")

        if template_path.suffix.lower() != ".docx":
            raise ValueError(f"Template must be a .docx file: {template_path}")
        with status.input.open("r", encoding="utf-8") as f:
            cv_data = json.load(f)

        # Sanitize data for XML safety
        sanitized_data = sanitize_for_xml_in_obj(cv_data)

        # Load and render template
        tpl = DocxTemplate(str(template_path))
        tpl.render(sanitized_data, autoescape=True)

        # Ensure output directory exists
        status.output.parent.mkdir(parents=True, exist_ok=True)

        # Save rendered document
        tpl.save(str(status.output))

        return work
