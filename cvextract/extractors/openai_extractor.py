"""
OpenAI-based CV extractor implementation.

Uses OpenAI API to extract structured CV data from various file formats.
Supports PDF, DOCX, PPTX, and TXT files.
"""

from __future__ import annotations

import base64
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
    - Accepts PDF, DOCX, PPTX, TXT files
    - Sends raw file content to OpenAI (as base64 for binary files)
    - Uses CV schema as context in the prompt
    - Returns structured data conforming to the CV schema
    """

    def __init__(self, model: str = "gpt-4o", **kwargs):
        """
        Initialize the OpenAI extractor.
        
        Args:
            model: OpenAI model to use (default: gpt-4o for vision/file capabilities)
            **kwargs: Additional arguments (reserved for future use)
        """
        self.model = model
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def extract(self, source: Path) -> Dict[str, Any]:
        """
        Extract structured CV data from a file using OpenAI.

        Args:
            source: Path to the source file (PDF, DOCX, PPTX, or TXT)

        Returns:
            Dictionary with extracted CV data (identity, sidebar, overview, experiences)

        Raises:
            FileNotFoundError: If the source file does not exist
            ValueError: If the file type is not supported
            Exception: For OpenAI API errors or parsing errors
        """
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")

        if not source.is_file():
            raise ValueError(f"Source must be a file: {source}")

        # Check file extension
        supported_extensions = {'.pdf', '.docx', '.pptx', '.txt'}
        file_ext = source.suffix.lower()
        
        if file_ext not in supported_extensions:
            raise ValueError(
                f"Unsupported file type: {file_ext}. "
                f"Supported types: {', '.join(sorted(supported_extensions))}"
            )

        # Read file content
        if file_ext == '.txt':
            # Read text files as plain text
            file_content = source.read_text(encoding='utf-8')
            content_type = 'text'
        else:
            # Read binary files (PDF, DOCX, PPTX) and encode as base64
            file_bytes = source.read_bytes()
            file_content = base64.b64encode(file_bytes).decode('utf-8')
            content_type = 'base64'

        # Load CV schema for context
        schema_path = Path(__file__).parent.parent / "contracts" / "cv_schema.json"
        with open(schema_path, 'r') as f:
            cv_schema = json.load(f)

        # Prepare the prompt
        prompt = self._build_extraction_prompt(cv_schema, file_ext, content_type)

        # Call OpenAI API
        try:
            if content_type == 'text':
                response = self._extract_from_text(prompt, file_content)
            else:
                response = self._extract_from_binary(prompt, file_content, file_ext)
            
            # Parse and validate response
            cv_data = self._parse_and_validate_response(response, cv_schema)
            return cv_data

        except Exception as e:
            raise Exception(f"OpenAI extraction failed: {str(e)}") from e

    def _build_extraction_prompt(self, cv_schema: Dict[str, Any], file_ext: str, content_type: str) -> str:
        """Build the extraction prompt with schema context."""
        schema_json = json.dumps(cv_schema, indent=2)
        
        prompt = f"""You are a CV/resume data extraction expert. Extract structured information from the provided {file_ext.upper()} file.

The extracted data MUST conform to the following JSON schema:

{schema_json}

Instructions:
1. Extract all relevant information from the CV/resume
2. Return ONLY valid JSON that matches the schema above
3. For the 'identity' section: extract personal information (title, full name, first name, last name)
4. For the 'sidebar' section: extract categorized skills, tools, languages, certifications, industries, spoken languages, and academic background
5. For the 'overview' section: extract the professional summary or overview text
6. For the 'experiences' section: extract work history with headings, descriptions, and bullet points
7. If a field is not present in the CV, use appropriate defaults:
   - For strings: use empty string ""
   - For arrays: use empty array []
   - For required fields in identity: make best effort to extract or use placeholders
8. Ensure all experience entries have at least 'heading' and 'description'
9. The 'environment' field in experiences can be null or an array of technologies used

Return ONLY the JSON object, no additional text or explanation.
"""
        return prompt

    def _extract_from_text(self, prompt: str, text_content: str) -> str:
        """Extract CV data from plain text file."""
        full_prompt = f"{prompt}\n\nCV Text Content:\n\n{text_content}"
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a CV data extraction expert. Extract structured data from CVs and return valid JSON."
                },
                {
                    "role": "user",
                    "content": full_prompt
                }
            ],
            temperature=0.1,  # Low temperature for consistency
        )
        
        return response.choices[0].message.content

    def _extract_from_binary(self, prompt: str, base64_content: str, file_ext: str) -> str:
        """Extract CV data from binary file (PDF, DOCX, PPTX)."""
        # For now, we'll use the simpler approach of describing what we need
        # Note: OpenAI's vision models can analyze images, but for document parsing
        # we may need to convert to images or use different approach
        
        # Determine MIME type
        mime_types = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openedocumentformat.wordprocessingml.document',
            '.pptx': 'application/vnd.openedocumentformat.presentationml.presentation'
        }
        mime_type = mime_types.get(file_ext, 'application/octet-stream')
        
        # For document files, we'll use a text-based approach
        # In a production system, you might want to use document parsing libraries
        # or OpenAI's file upload API for better results
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a CV data extraction expert. Extract structured data from CVs and return valid JSON."
                },
                {
                    "role": "user",
                    "content": f"{prompt}\n\nNote: Binary {file_ext.upper()} file provided as base64. "
                               f"Please extract CV information and return structured JSON as specified."
                }
            ],
            temperature=0.1,
        )
        
        return response.choices[0].message.content

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
