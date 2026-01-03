"""
OpenAI-based CV extractor implementation.

Uses OpenAI API to extract structured CV data from document files.
Sends documents directly to OpenAI for processing without pre-extraction.
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any, Dict

from openai import OpenAI

from .base import CVExtractor
from ..shared import load_prompt, format_prompt
from ..verifiers import get_verifier


class OpenAICVExtractor(CVExtractor):
    """
    CV extractor using OpenAI API for intelligent extraction.
    
    This implementation:
    - Accepts any document file (PDF, DOCX, TXT, PPTX, etc.)
    - Sends the file directly to OpenAI for processing
    - Returns structured data conforming to the CV schema
    
    OpenAI handles file parsing and content extraction.
    """

    def __init__(self, model: str = "gpt-4o", **kwargs):
        """
        Initialize the OpenAI extractor.
        
        Args:
            model: OpenAI model to use (default: gpt-4o for vision/document processing)
            **kwargs: Additional arguments (reserved for future use)
        """
        self.model = model
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def extract(self, file_path: str | Path) -> Dict[str, Any]:
        """
        Extract structured CV data by sending the file directly to OpenAI.

        Args:
            file_path: Path to the document file (any format: PDF, DOCX, TXT, PPTX, etc.)

        Returns:
            Dictionary with extracted CV data (identity, sidebar, overview, experiences)

        Raises:
            FileNotFoundError: If the file does not exist
            Exception: For OpenAI API errors or parsing errors
        """
        # Convert to Path object
        file_path = Path(file_path)
        
        # Verify file exists
        if not file_path.exists():
            raise FileNotFoundError(f"Document file not found: {file_path}")

        if not file_path.is_file():
            raise ValueError(f"Path must be a file: {file_path}")

        # Load CV schema for prompt context and validation
        cv_schema = self._load_cv_schema()

        # Send file directly to OpenAI for processing
        response = self._extract_with_openai(file_path, cv_schema)
        
        # Parse and validate response
        cv_data = self._parse_and_validate_response(response, cv_schema)
        return cv_data

    def _load_cv_schema(self) -> Dict[str, Any]:
        """Load the CV schema for prompt context."""
        schema_path = Path(__file__).parent.parent / "contracts" / "cv_schema.json"
        with open(schema_path, 'r') as f:
            return json.load(f)

    def _extract_with_openai(self, file_path: Path, cv_schema: Dict[str, Any]) -> str:
        """
        Send the file directly to OpenAI for CV extraction.
        
        Args:
            file_path: Path to the document file
            cv_schema: CV schema for prompt context
            
        Returns:
            OpenAI API response containing extracted CV data as JSON
        """
        schema_json = json.dumps(cv_schema, indent=2)
        
        # Load prompts from templates
        system_prompt = load_prompt("cv_extraction_system")
        
        if not system_prompt:
            raise RuntimeError("Failed to load CV extraction system prompt")
        
        # Use file upload API for large files
        file_id = self._upload_file_and_get_id(file_path)
                
        # Format user prompt with schema and file reference
        user_prompt = format_prompt(
            "cv_extraction_user",
            schema_json=schema_json,
            file_upload_id=file_id
        )
        
        if not user_prompt:
            raise RuntimeError("Failed to format CV extraction user prompt")

        # Send to OpenAI
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                temperature=0.1,  # Low temperature for consistency
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise Exception(f"Failed to send document to OpenAI: {str(e)}") from e

    def _upload_file_and_get_id(self, file_path: Path) -> str:
        """
        Upload a file to OpenAI's file storage for processing.
        
        Args:
            file_path: Path to the file to upload
            
        Returns:
            File ID from OpenAI for use in API calls
        """
        try:
            with open(file_path, 'rb') as f:
                response = self.client.files.create(
                    file=f,
                    purpose="assistants"
                )
            return response.id
        except Exception as e:
            raise RuntimeError(f"Failed to upload file to OpenAI: {str(e)}")

    def _parse_and_validate_response(self, response: str, cv_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse OpenAI response and validate against cv_schema.json.
        
        Uses CVSchemaVerifier to validate the extracted data.
        """
        # Extract JSON from response (handle markdown code blocks)
        response = response.strip()
        
        # Remove markdown code block markers if present
        if response.startswith('```json'):
            response = response[7:]  # Remove ```json
        elif response.startswith('```'):
            response = response[3:]  # Remove ```
        
        if response.endswith('```'):
            response = response[:-3]  # Remove closing ```
        
        response = response.strip()
        
        # Parse JSON
        try:
            cv_data = json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(f"OpenAI returned invalid JSON: {str(e)}\nResponse: {response[:500]}")
        
        # Validate against schema using CVSchemaVerifier
        schema_verifier = get_verifier("cv-schema-verifier")
        result = schema_verifier.verify(cv_data)
        
        if not result.ok:
            raise ValueError(f"Extracted data failed schema validation: {result.errors}")
        
        return cv_data
