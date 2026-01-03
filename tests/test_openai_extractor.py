"""Tests for OpenAI CV extractor implementation."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from cvextract.extractors import OpenAICVExtractor, CVExtractor


class TestOpenAICVExtractor:
    """Tests for OpenAICVExtractor implementation."""

    def test_openai_extractor_is_cv_extractor(self):
        """OpenAICVExtractor is a CVExtractor."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            assert isinstance(extractor, CVExtractor)

    def test_openai_extractor_default_model(self):
        """OpenAICVExtractor uses default model."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            assert extractor.model == 'gpt-4o'

    def test_openai_extractor_custom_model(self):
        """OpenAICVExtractor accepts custom model."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor(model='gpt-4-turbo')
            assert extractor.model == 'gpt-4-turbo'

    def test_extract_raises_file_not_found(self):
        """extract() raises FileNotFoundError for missing file."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            with pytest.raises(FileNotFoundError):
                extractor.extract(Path('/nonexistent/file.pdf'))

    def test_extract_raises_value_error_for_directory(self, tmp_path):
        """extract() raises ValueError for directory."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            test_dir = tmp_path / "test_dir"
            test_dir.mkdir()
            with pytest.raises(ValueError, match="must be a file"):
                extractor.extract(test_dir)

    def test_extract_accepts_any_file_type(self, tmp_path):
        """extract() accepts any file type without validation."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            test_file = tmp_path / "test.xyz"
            test_file.write_text("test content")
            
            # Mock _extract_with_openai to return valid CV JSON
            mock_response = {
                "identity": {
                    "title": "Test",
                    "full_name": "Test User",
                    "first_name": "Test",
                    "last_name": "User"
                },
                "sidebar": {},
                "overview": "Test",
                "experiences": []
            }
            
            with patch.object(extractor, '_extract_with_openai', return_value=json.dumps(mock_response)):
                result = extractor.extract(test_file)
                assert result['identity']['full_name'] == 'Test User'

    def test_load_cv_schema(self):
        """_load_cv_schema() loads and returns CV schema."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            schema = extractor._load_cv_schema()
            
            assert isinstance(schema, dict)
            assert 'properties' in schema
            assert 'identity' in schema['properties']
            assert 'sidebar' in schema['properties']
            assert 'overview' in schema['properties']
            assert 'experiences' in schema['properties']

    def test_upload_file_success(self, tmp_path):
        """_upload_file() successfully uploads file and returns file_id."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            test_file = tmp_path / "test.pdf"
            test_file.write_text("test content")
            
            # Mock the OpenAI client
            mock_response = MagicMock()
            mock_response.id = "file_id_12345"
            extractor.client.files.create = MagicMock(return_value=mock_response)
            
            file_id = extractor._upload_file(test_file)
            
            assert file_id == "file_id_12345"
            extractor.client.files.create.assert_called_once()

    def test_upload_file_raises_on_error(self, tmp_path):
        """_upload_file() raises RuntimeError when upload fails."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            test_file = tmp_path / "test.pdf"
            test_file.write_text("test content")
            
            extractor.client.files.create = MagicMock(side_effect=Exception("Upload failed"))
            
            with pytest.raises(RuntimeError, match="Failed to upload file to OpenAI"):
                extractor._upload_file(test_file)

    def test_extract_with_openai_success(self, tmp_path):
        """_extract_with_openai() successfully extracts data using Assistants API."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('cvextract.extractors.openai_extractor.OpenAI'):
                extractor = OpenAICVExtractor()
                test_file = tmp_path / "test.pdf"
                test_file.write_text("test content")
                
                schema = extractor._load_cv_schema()
                
                # Mock OpenAI client methods
                mock_file = MagicMock()
                mock_file.id = "file_123"
                extractor.client.files.create = MagicMock(return_value=mock_file)
                
                mock_assistant = MagicMock()
                mock_assistant.id = "asst_123"
                extractor.client.beta.assistants.create = MagicMock(return_value=mock_assistant)
                
                mock_thread = MagicMock()
                mock_thread.id = "thread_123"
                extractor.client.beta.threads.create = MagicMock(return_value=mock_thread)
                
                mock_run = MagicMock()
                mock_run.status = "completed"
                extractor.client.beta.threads.runs.create = MagicMock(return_value=mock_run)
                extractor.client.beta.threads.runs.retrieve = MagicMock(return_value=mock_run)
                
                mock_message = MagicMock()
                mock_message.content = [MagicMock()]
                mock_message.content[0].text = '{"identity": {"title": "Test", "full_name": "Test", "first_name": "T", "last_name": "est"}, "sidebar": {}, "overview": "Test", "experiences": []}'
                mock_messages = MagicMock()
                mock_messages.data = [mock_message]
                extractor.client.beta.threads.messages.list = MagicMock(return_value=mock_messages)
                extractor.client.beta.threads.messages.create = MagicMock()
                
                result = extractor._extract_with_openai(test_file, schema)
                
                assert isinstance(result, str)
                assert "Test" in result

    def test_extract_with_openai_assistant_creation_failure(self, tmp_path):
        """_extract_with_openai() raises RuntimeError when assistant creation fails."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            test_file = tmp_path / "test.pdf"
            test_file.write_text("test content")
            
            schema = extractor._load_cv_schema()
            
            mock_file = MagicMock()
            mock_file.id = "file_123"
            extractor.client.files.create = MagicMock(return_value=mock_file)
            
            extractor.client.beta.assistants.create = MagicMock(side_effect=Exception("Assistant creation failed"))
            
            with pytest.raises(RuntimeError, match="Failed to create OpenAI assistant"):
                extractor._extract_with_openai(test_file, schema)

    def test_extract_with_openai_message_creation_failure(self, tmp_path):
        """_extract_with_openai() raises RuntimeError when message creation fails."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            test_file = tmp_path / "test.pdf"
            test_file.write_text("test content")
            
            schema = extractor._load_cv_schema()
            
            mock_file = MagicMock()
            mock_file.id = "file_123"
            extractor.client.files.create = MagicMock(return_value=mock_file)
            
            mock_assistant = MagicMock()
            mock_assistant.id = "asst_123"
            extractor.client.beta.assistants.create = MagicMock(return_value=mock_assistant)
            
            mock_thread = MagicMock()
            mock_thread.id = "thread_123"
            extractor.client.beta.threads.create = MagicMock(return_value=mock_thread)
            
            extractor.client.beta.threads.messages.create = MagicMock(side_effect=Exception("Message creation failed"))
            
            with pytest.raises(RuntimeError, match="Failed to create message in OpenAI thread"):
                extractor._extract_with_openai(test_file, schema)

    def test_extract_with_openai_run_failed(self, tmp_path):
        """_extract_with_openai() raises RuntimeError when run fails."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('cvextract.extractors.openai_extractor.OpenAI'):
                extractor = OpenAICVExtractor()
                test_file = tmp_path / "test.pdf"
                test_file.write_text("test content")
                
                schema = extractor._load_cv_schema()
                
                mock_file = MagicMock()
                mock_file.id = "file_123"
                extractor.client.files.create = MagicMock(return_value=mock_file)
                
                mock_assistant = MagicMock()
                mock_assistant.id = "asst_123"
                extractor.client.beta.assistants.create = MagicMock(return_value=mock_assistant)
                
                mock_thread = MagicMock()
                mock_thread.id = "thread_123"
                extractor.client.beta.threads.create = MagicMock(return_value=mock_thread)
                extractor.client.beta.threads.messages.create = MagicMock()
                
                mock_run = MagicMock()
                mock_run.status = "failed"
                extractor.client.beta.threads.runs.create = MagicMock(return_value=mock_run)
                
                with pytest.raises(RuntimeError, match="Assistant run failed with status"):
                    extractor._extract_with_openai(test_file, schema)

    def test_parse_and_validate_with_code_blocks_json(self):
        """_parse_and_validate() handles markdown code blocks with json label."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            schema = extractor._load_cv_schema()
            
            response = '''```json
{"identity": {"title": "Engineer", "full_name": "John Doe", "first_name": "John", "last_name": "Doe"}, "sidebar": {}, "overview": "Test", "experiences": []}
```'''
            
            result = extractor._parse_and_validate(response, schema)
            assert result['identity']['full_name'] == 'John Doe'

    def test_parse_and_validate_with_code_blocks_plain(self):
        """_parse_and_validate() handles plain markdown code blocks."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            schema = extractor._load_cv_schema()
            
            response = '''```
{"identity": {"title": "Engineer", "full_name": "Jane Smith", "first_name": "Jane", "last_name": "Smith"}, "sidebar": {}, "overview": "Test", "experiences": []}
```'''
            
            result = extractor._parse_and_validate(response, schema)
            assert result['identity']['full_name'] == 'Jane Smith'

    def test_parse_and_validate_without_code_blocks(self):
        """_parse_and_validate() handles raw JSON without code blocks."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            schema = extractor._load_cv_schema()
            
            response = '{"identity": {"title": "Dev", "full_name": "Bob Wilson", "first_name": "Bob", "last_name": "Wilson"}, "sidebar": {}, "overview": "Test", "experiences": []}'
            
            result = extractor._parse_and_validate(response, schema)
            assert result['identity']['full_name'] == 'Bob Wilson'

    def test_parse_and_validate_invalid_json(self):
        """_parse_and_validate() raises ValueError for invalid JSON."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            schema = extractor._load_cv_schema()
            
            response = '{"identity": {invalid json}}'
            
            with pytest.raises(ValueError, match="Failed to parse response as JSON"):
                extractor._parse_and_validate(response, schema)

    def test_parse_and_validate_schema_mismatch(self):
        """_parse_and_validate() raises ValueError when data doesn't match schema."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            schema = extractor._load_cv_schema()
            
            # Missing required fields
            response = '{"identity": {"title": "Test"}}'
            
            with pytest.raises(ValueError, match="Response does not match schema"):
                extractor._parse_and_validate(response, schema)

    def test_extract_with_openai_system_prompt_fails_to_load(self, tmp_path):
        """_extract_with_openai() raises RuntimeError when system prompt fails to load."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('cvextract.extractors.openai_extractor.OpenAI'):
                extractor = OpenAICVExtractor()
                test_file = tmp_path / "test.pdf"
                test_file.write_text("test content")
                
                schema = extractor._load_cv_schema()
                
                mock_file = MagicMock()
                mock_file.id = "file_123"
                extractor.client.files.create = MagicMock(return_value=mock_file)
                
                with patch('cvextract.extractors.openai_extractor.load_prompt', return_value=None):
                    with pytest.raises(RuntimeError, match="Failed to load system prompt"):
                        extractor._extract_with_openai(test_file, schema)

    def test_extract_with_openai_user_prompt_fails_to_format(self, tmp_path):
        """_extract_with_openai() raises RuntimeError when user prompt fails to format."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('cvextract.extractors.openai_extractor.OpenAI'):
                extractor = OpenAICVExtractor()
                test_file = tmp_path / "test.pdf"
                test_file.write_text("test content")
                
                schema = extractor._load_cv_schema()
                
                mock_file = MagicMock()
                mock_file.id = "file_123"
                extractor.client.files.create = MagicMock(return_value=mock_file)
                
                with patch('cvextract.extractors.openai_extractor.load_prompt', return_value="System prompt"):
                    with patch('cvextract.extractors.openai_extractor.format_prompt', return_value=None):
                        with pytest.raises(RuntimeError, match="Failed to format user prompt"):
                            extractor._extract_with_openai(test_file, schema)
