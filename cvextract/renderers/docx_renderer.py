"""
DOCX-based CV renderer implementation.

Renders structured CV data to Word .docx files using docxtpl templates.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .base import CVRenderer
from ..shared import sanitize_for_xml_in_obj

from docxtpl import DocxTemplate


class DocxCVRenderer(CVRenderer):
    """
    CV renderer for Microsoft Word .docx files.
    
    This implementation:
    - Uses docxtpl for template rendering
    - Sanitizes content for XML safety before rendering
    - Supports auto-escaping for security
    - Returns the path to the rendered document
    """

    def render(self, cv_data: Dict[str, Any], template_path: Path, output_path: Path) -> Path:
        """
        Render CV data to a .docx file using a docxtpl template.

        Args:
            cv_data: Dictionary with CV data conforming to cv_schema.json
            template_path: Path to the .docx template file
            output_path: Path where the rendered .docx should be saved

        Returns:
            Path to the rendered .docx file

        Raises:
            FileNotFoundError: If the template file does not exist
            Exception: For rendering or template errors
        """
        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")

        if not template_path.is_file() or template_path.suffix.lower() != ".docx":
            raise ValueError(f"Template must be a .docx file: {template_path}")

        # Sanitize data for XML safety
        sanitized_data = sanitize_for_xml_in_obj(cv_data)

        # Load and render template
        tpl = DocxTemplate(str(template_path))
        tpl.render(sanitized_data, autoescape=True)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save rendered document
        tpl.save(str(output_path))
        
        return output_path
