"""
DOCX-based CV extractor implementation.

Extracts structured CV data from Word .docx files.
"""

from __future__ import annotations

from typing import Any

from ..shared import UnitOfWork
from .base import CVExtractor
from .body_parser import parse_cv_from_docx_body
from .sidebar_parser import extract_all_header_paragraphs, split_identity_and_sidebar


class DocxCVExtractor(CVExtractor):
    """
    CV extractor for Microsoft Word .docx files.

    This implementation:
    - Parses Word documents as ZIP archives
    - Extracts header/sidebar content from text boxes
    - Parses the main body for overview and experience sections
    - Returns structured data conforming to the CV schema
    """

    def extract(self, work: UnitOfWork) -> UnitOfWork:
        """
        Extract structured CV data from a .docx file.

        Args:
            work: UnitOfWork containing input/output paths.

        Returns:
            UnitOfWork with output JSON populated.

        Raises:
            FileNotFoundError: If the .docx file does not exist
            Exception: For parsing or extraction errors
        """
        source = work.input
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")

        if not source.is_file() or source.suffix.lower() != ".docx":
            raise ValueError(f"Source must be a .docx file: {source}")

        # Extract body content (overview and experiences)
        overview, experiences = parse_cv_from_docx_body(source)

        # Extract header content (identity and sidebar)
        header_paragraphs = extract_all_header_paragraphs(source)
        identity, sidebar = split_identity_and_sidebar(header_paragraphs)

        data: dict[str, Any] = {
            "identity": identity.as_dict(),
            "sidebar": sidebar,
            "overview": overview,
            "experiences": experiences,
        }
        return self._write_output_json(work, data)
