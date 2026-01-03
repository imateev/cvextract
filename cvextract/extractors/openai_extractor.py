"""
OpenAI-based CV extractor implementation.

Uses OpenAI API to extract structured CV data from document files.
Sends documents directly to OpenAI for processing using the Uploads API.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from openai import OpenAI

from .base import CVExtractor
from ..shared import load_prompt, format_prompt
from ..verifiers import get_verifier


class OpenAICVExtractor(CVExtractor):
    """
    CV extractor using OpenAI API for intelligent document analysis.
    
    Uses OpenAI's Uploads API to send documents directly, matching 
    the behavior of the ChatGPT UI.
    """

    def __init__(self, model: str = "gpt-4o", **kwargs):
        """
        Initialize the OpenAI extractor.
        
        Args:
            model: OpenAI model to use (default: gpt-4o)
            **kwargs: Additional arguments (reserved for future use)
        """
        self.model = model
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def extract(self, file_path: str | Path) -> dict[str, Any]:
        """
        Extract structured CV data from a document file.

        Args:
            file_path: Path to the document file (PDF, DOCX, etc.)

        Returns:
            Dictionary with extracted CV data conforming to cv_schema.json

        Raises:
            FileNotFoundError: If the file does not exist
            ValueError: If extraction or validation fails
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")
        
        if not file_path.is_file():
            raise ValueError(f"Path must be a file: {file_path}")

        # Load CV schema
        cv_schema = self._load_cv_schema()
        
        # Extract data using OpenAI
        response_text = self._extract_with_openai(file_path, cv_schema)
        
        # Parse and validate
        cv_data = self._parse_and_validate(response_text, cv_schema)
        
        return cv_data

    def _load_cv_schema(self) -> dict[str, Any]:
        """Load the CV schema."""
        schema_path = Path(__file__).parent.parent / "contracts" / "cv_schema.json"
        with open(schema_path, 'r') as f:
            return json.load(f)

    def _upload_file(self, file_path: Path) -> str:
        """
        Upload a file using OpenAI's Files API.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File ID from the upload
        """
        try:
            with open(file_path, 'rb') as f:
                response = self.client.files.create(
                    file=(file_path.name, f),
                    purpose='assistants'
                )
            return response.id
        except Exception as e:
            raise RuntimeError(f"Failed to upload file to OpenAI: {e}")

    def _extract_with_openai(self, file_path: Path, cv_schema: dict[str, Any]) -> str:
        """
        Send the file to OpenAI using Assistants API and get extraction results.
        
        Args:
            file_path: Path to the document
            cv_schema: CV schema for context
            
        Returns:
            OpenAI response containing JSON with extracted data
        """
        # Upload the file
        file_id = self._upload_file(file_path)
        
        # Load prompts
        system_prompt = load_prompt("cv_extraction_system")
        schema_str = json.dumps(cv_schema, indent=2)
        
        user_prompt = format_prompt(
            "cv_extraction_user",
            schema_json=schema_str,
            file_name=file_path.name
        )
        
        if not system_prompt:
            raise RuntimeError("Failed to load system prompt")
        
        if not user_prompt:
            raise RuntimeError("Failed to format user prompt")
        
        # Create an assistant for CV extraction with file_search enabled
        try:  
            assistant = self.client.beta.assistants.create(
                name="CV Extractor",
                instructions=system_prompt,
                model=self.model,
                tools=[{"type": "file_search"}]
            )
        except Exception as e:
            raise RuntimeError(f"Failed to create OpenAI assistant: {e}")
        
        # Create a thread
        thread = self.client.beta.threads.create()
        
        try:
            # Add message with file reference using attachments
            self.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=user_prompt,
                attachments=[
                    {
                        "file_id": file_id,
                        "tools": [{"type": "file_search"}]
                    }
                ]
            )
        except Exception as e:
            raise RuntimeError(f"Failed to create message in OpenAI thread: {e}")
        
        # Run the assistant
        run = self.client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id
        )
        
        # Wait for completion
        import time
        while run.status in ["queued", "in_progress"]:
            time.sleep(1.0)
            run = self.client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
        
        if run.status != "completed":
            raise RuntimeError(f"Assistant run failed with status: {run.status}")
        
        # Get the response
        messages = self.client.beta.threads.messages.list(thread_id=thread.id)
        response_text = messages.data[0].content[0].text
        
        # Clean up
        self.client.beta.assistants.delete(assistant.id)
        
        return response_text

    def _parse_and_validate(self, response_text: str, cv_schema: dict[str, Any]) -> dict[str, Any]:
        """
        Parse the response and validate against the schema.
        
        Args:
            response_text: Response from OpenAI
            cv_schema: Schema to validate against
            
        Returns:
            Validated CV data
        """
        # Clean up response (remove markdown code blocks if present)
        text = response_text.strip() if isinstance(response_text, str) else response_text.value.strip()
         
        if text.startswith('```json'):
            text = text[7:]
        elif text.startswith('```'):
            text = text[3:]
        if text.endswith('```'):
            text = text[:-3]
        text = text.strip()
        
        # Parse JSON
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse response as JSON: {e}\nResponse was: {text[:500]}")
        
        # Validate using the verifier
        verifier = get_verifier("cv-schema-verifier")
        if not verifier:
            raise RuntimeError("CV schema verifier not available")
        
        result = verifier.verify(data)
        if not result.ok:
            raise ValueError(f"Response does not match schema: {result.errors}")
        
        return data
