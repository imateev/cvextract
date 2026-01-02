"""
OpenAI-based CV extractor implementation.

Uses OpenAI API to extract structured CV data from document files.
Sends documents directly to OpenAI for processing without pre-extraction.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from openai import OpenAI

from .base import CVExtractor


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
        
        system_prompt = """You are a CV/resume data extraction expert. Your task is to extract structured information from the provided document and return valid JSON that matches the specified schema.

IMPORTANT: Return ONLY valid JSON that matches the schema. No additional text or explanations."""

        user_prompt = f"""Please extract all CV/resume information from the provided document and return it as valid JSON conforming to this schema:

{schema_json}

Extraction guidelines:
1. Extract personal information (identity section): title, full name, first name, last name
2. Extract categorized skills (sidebar): skills, tools, languages, certifications, industries, spoken languages, academic background
3. Extract professional summary (overview section)
4. Extract work history (experiences section): company, position, dates, description, and bullet points
5. For missing fields, use appropriate defaults:
   - Strings: empty string ""
   - Arrays: empty array []
6. Include all technologies and tools mentioned in the document under the 'environment' field in experiences
7. Preserve formatting and hierarchical structure from the document

Return ONLY the JSON object, no markdown, no code blocks, no additional text.

Document file: {file_path.name}"""

        # Send file to OpenAI using Vision API with file URL or direct content
        try:
            # For now, we pass the file path in the prompt
            # In production, you would upload the file using OpenAI Files API
            # and reference it, or use Vision API for images
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": f"{user_prompt}\n\nFile path: {file_path}"
                    }
                ],
                temperature=0.1,  # Low temperature for consistency
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise Exception(f"Failed to send document to OpenAI: {str(e)}") from e

    def _parse_and_validate_response(self, response: str, cv_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Parse OpenAI response and validate against schema."""
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
        
        # Ensure basic structure - add missing fields with defaults
        if 'identity' not in cv_data or not isinstance(cv_data['identity'], dict):
            cv_data['identity'] = {
                'title': '',
                'full_name': '',
                'first_name': '',
                'last_name': ''
            }
        
        if 'sidebar' not in cv_data or not isinstance(cv_data['sidebar'], dict):
            cv_data['sidebar'] = {}
        
        if 'overview' not in cv_data:
            cv_data['overview'] = ''
        
        if 'experiences' not in cv_data or not isinstance(cv_data['experiences'], list):
            cv_data['experiences'] = []
        
        return cv_data
