"""Tests for OpenAI CV extractor implementation with retry and adaptive polling."""

import json
import tempfile
import pytest
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from cvextract.extractors import OpenAICVExtractor, CVExtractor
from cvextract.extractors.openai_extractor import _RetryConfig


class TestOpenAICVExtractorInit:
    """Tests for OpenAICVExtractor initialization."""

    def test_extractor_is_cv_extractor(self):
        """OpenAICVExtractor implements CVExtractor interface."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            assert isinstance(extractor, CVExtractor)

    def test_default_model_is_gpt4o(self):
        """Default model should be gpt-4o."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            assert extractor.model == 'gpt-4o'

    def test_custom_model(self):
        """Should accept custom model."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor(model='gpt-4-turbo')
            assert extractor.model == 'gpt-4-turbo'

    def test_custom_retry_config(self):
        """Should accept custom retry configuration."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            custom_config = _RetryConfig(max_attempts=5, base_delay_s=0.5)
            extractor = OpenAICVExtractor(retry_config=custom_config)
            assert extractor._retry.max_attempts == 5
            assert extractor._retry.base_delay_s == 0.5

    def test_custom_run_timeout(self):
        """Should accept custom run timeout."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor(run_timeout_s=300.0)
            assert extractor._run_timeout_s == 300.0


class TestExtractFileValidation:
    """Tests for file validation in extract()."""

    def test_extract_missing_file(self):
        """extract() raises FileNotFoundError for missing file."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            with pytest.raises(FileNotFoundError, match="Document not found"):
                extractor.extract(Path('/nonexistent/file.pdf'))

    def test_extract_directory_not_allowed(self, tmp_path):
        """extract() raises ValueError for directory."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            test_dir = tmp_path / "test_dir"
            test_dir.mkdir()
            with pytest.raises(ValueError, match="must be a file"):
                extractor.extract(test_dir)
                
        def test_extract_loads_schema_and_validates(self, tmp_path, monkeypatch):
            """extract() loads schema and validates after file checks."""
            with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
                extractor = OpenAICVExtractor()
                test_file = tmp_path / "test.docx"
                test_file.write_text("test content")
                extractor._extract_with_openai = MagicMock(return_value='{"identity": {}}')
                extractor._parse_and_validate = MagicMock(return_value={"identity": {}})
                with patch('cvextract.extractors.openai_extractor.files') as mock_files:
                    mock_files.return_value.joinpath.return_value = test_file
                    result = extractor.extract(str(test_file))
                    assert result == {"identity": {}}
    def test_resource_cache_created_and_used(self, tmp_path, monkeypatch):
        """Test that resource cache is created and reused."""
        from cvextract.extractors.openai_extractor import OpenAICVExtractor
        extractor = OpenAICVExtractor()
        cache_dir = tmp_path / "cvextract"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / "cv_schema.json"
        cache_path.write_text(json.dumps({"type": "object"}))
        with patch('cvextract.extractors.openai_extractor.files') as mock_files:
            mock_files.return_value.joinpath.return_value = cache_path
            result = extractor._load_cv_schema()
            assert result["type"] == "object"
    def test_load_cv_schema_permission_error(self):
        """Test schema loading with permission error."""
        from cvextract.extractors.openai_extractor import OpenAICVExtractor
        extractor = OpenAICVExtractor()
        cache_dir = Path(tempfile.gettempdir()) / "cvextract"
        cache_path = cache_dir / "cv_schema.json"
        if cache_path.exists():
            cache_path.unlink()
        with patch('cvextract.extractors.openai_extractor.files') as mock_files:
            tmp_file = Path('/tmp/test_perm.json')
            tmp_file.write_text(json.dumps({"type": "object"}))
            tmp_file.chmod(0)
            mock_files.return_value.joinpath.return_value = tmp_file
            try:
                with pytest.raises(PermissionError):
                    extractor._load_cv_schema()
            finally:
                tmp_file.chmod(0o644)
    def test_call_with_retry_jitter_and_deterministic(self):
        """Test call_with_retry with jitter and deterministic modes."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            attempt_count = [0]
            def failing_fn():
                attempt_count[0] += 1
                if attempt_count[0] < 2:
                    exc = Exception("Temporary network error")
                    exc.status_code = 503
                    raise exc
                return "success"
            config = _RetryConfig(deterministic=False)
            extractor = OpenAICVExtractor(retry_config=config, _sleep=lambda x: ...)
            result = extractor._call_with_retry(
                failing_fn,
                is_write=False,
                op_name="Test op"
            )
            assert result == "success"
            config2 = _RetryConfig(deterministic=True)
            extractor2 = OpenAICVExtractor(retry_config=config2, _sleep=lambda x: ...)
            attempt_count[0] = 0
            result2 = extractor2._call_with_retry(
                failing_fn,
                is_write=False,
                op_name="Test op"
            )
            assert result2 == "success"
    def test_parse_and_validate_markdown_variants(self):
        """Test parsing JSON with various markdown fences."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            schema = {"type": "object"}
            for text in [
                '```json\n{"identity": {}}\n```',
                '```\n{"identity": {}}\n```',
                '{"identity": {}}',
            ]:
                with patch('cvextract.extractors.openai_extractor.get_verifier') as mock_get_verifier:
                    mock_verifier = MagicMock()
                    mock_verifier.verify.return_value = MagicMock(ok=True)
                    mock_get_verifier.return_value = mock_verifier
                    result = extractor._parse_and_validate(text, schema)
                    assert result == {"identity": {}}

    def test_extract_accepts_any_file_type(self, tmp_path):
        """extract() accepts any file type."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            test_file = tmp_path / "test.xyz"
            test_file.write_text("test")

            with patch.object(extractor, '_extract_with_openai', return_value=json.dumps({
                "identity": {"title": "Test", "full_name": "User", "first_name": "T", "last_name": "U"},
                "sidebar": {}, "overview": "Test", "experiences": []
            })):
                result = extractor.extract(test_file)
                assert result['identity']['full_name'] == 'User'


class TestRetryMechanisms:
    """Tests for retry and backoff logic."""

    def test_is_transient_429(self):
        """_is_transient() recognizes 429 as transient."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            exc = MagicMock()
            exc.status_code = 429
            assert extractor._is_transient(exc) is True

    def test_is_transient_5xx(self):
        """_is_transient() recognizes 5xx as transient."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            for status in [500, 502, 503, 504]:
                exc = MagicMock()
                exc.status_code = status
                assert extractor._is_transient(exc) is True

    def test_is_transient_timeout(self):
        """_is_transient() recognizes timeout errors as transient."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            exc = Exception("Request timed out")
            assert extractor._is_transient(exc) is True

    def test_is_transient_non_transient_error(self):
        """_is_transient() recognizes non-transient errors."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            exc = MagicMock()
            exc.status_code = 400  # Bad request
            assert extractor._is_transient(exc) is False

    def test_get_retry_after_from_headers(self):
        """_get_retry_after_s() extracts Retry-After header."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            exc = MagicMock()
            exc.headers = {"retry-after": "5.5"}
            result = extractor._get_retry_after_s(exc)
            assert result == 5.5

    def test_sleep_with_backoff_uses_retry_after(self):
        """_sleep_with_backoff() uses Retry-After when available."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            mock_sleep = MagicMock()
            extractor = OpenAICVExtractor(_sleep=mock_sleep)
            
            exc = MagicMock()
            exc.headers = {"retry-after": "2.0"}
            
            extractor._sleep_with_backoff(0, is_write=False, exc=exc)
            mock_sleep.assert_called_once_with(2.0)

    def test_sleep_with_backoff_exponential_when_no_retry_after(self):
        """_sleep_with_backoff() uses exponential backoff without Retry-After."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            mock_sleep = MagicMock()
            config = _RetryConfig(base_delay_s=1.0, max_delay_s=10.0, deterministic=True)
            extractor = OpenAICVExtractor(retry_config=config, _sleep=mock_sleep)
            
            exc = MagicMock()
            exc.status_code = 429
            exc.headers = {}
            
            # First retry: 1.0 * (2^0) = 1.0
            extractor._sleep_with_backoff(0, is_write=False, exc=exc)
            mock_sleep.assert_called_with(1.0)

    def test_call_with_retry_succeeds_on_first_attempt(self):
        """_call_with_retry() returns immediately on success."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            fn = MagicMock(return_value="success")
            
            result = extractor._call_with_retry(fn, is_write=False, op_name="test")
            
            assert result == "success"
            fn.assert_called_once()

    def test_call_with_retry_raises_on_non_transient(self):
        """_call_with_retry() raises immediately for non-transient errors."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            
            # Create a proper exception that has status_code attribute
            exc = Exception("Bad request")
            exc.status_code = 400  # Bad request (non-transient)
            fn = MagicMock(side_effect=exc)
            
            with pytest.raises(RuntimeError, match="non-retryable"):
                extractor._call_with_retry(fn, is_write=False, op_name="test")

    def test_call_with_retry_exhausts_attempts(self):
        """_call_with_retry() raises after max attempts exceeded."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            mock_sleep = MagicMock()
            config = _RetryConfig(max_attempts=2)
            extractor = OpenAICVExtractor(retry_config=config, _sleep=mock_sleep)
            
            # Create an exception that looks like a 429 rate limit
            exc = Exception("Rate limited")
            exc.status_code = 429
            exc.headers = {}
            fn = MagicMock(side_effect=exc)
            
            with pytest.raises(RuntimeError, match="after 2 attempts"):
                extractor._call_with_retry(fn, is_write=False, op_name="test")


class TestOpenAIOperations:
    """Tests for individual OpenAI API operations."""

    def test_upload_file_success(self, tmp_path):
        """_upload_file() uploads and returns file_id."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            test_file = tmp_path / "test.pdf"
            test_file.write_text("content")
            
            mock_response = MagicMock(id="file_123")
            extractor.client.files.create = MagicMock(return_value=mock_response)
            
            file_id = extractor._upload_file(test_file)
            assert file_id == "file_123"

    def test_create_assistant_success(self):
        """_create_assistant() creates and returns assistant_id."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            mock_response = MagicMock(id="asst_123")
            extractor.client.beta.assistants.create = MagicMock(return_value=mock_response)
            
            asst_id = extractor._create_assistant("test prompt")
            assert asst_id == "asst_123"

    def test_create_thread_success(self):
        """_create_thread() creates and returns thread_id."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            mock_response = MagicMock(id="thread_123")
            extractor.client.beta.threads.create = MagicMock(return_value=mock_response)
            
            thread_id = extractor._create_thread()
            assert thread_id == "thread_123"

    def test_create_message_success(self):
        """_create_message() creates message without error."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            extractor.client.beta.threads.messages.create = MagicMock()
            
            extractor._create_message(thread_id="t_123", user_prompt="test", file_id="f_123")
            extractor.client.beta.threads.messages.create.assert_called_once()

    def test_create_run_success(self):
        """_create_run() creates and returns run_id."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            mock_response = MagicMock(id="run_123")
            extractor.client.beta.threads.runs.create = MagicMock(return_value=mock_response)
            
            run_id = extractor._create_run(thread_id="t_123", assistant_id="a_123")
            assert run_id == "run_123"

    def test_delete_assistant_gracefully_handles_error(self):
        """_delete_assistant() doesn't raise on cleanup errors."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            extractor.client.beta.assistants.delete = MagicMock(side_effect=Exception("delete failed"))
            
            # Should not raise
            extractor._delete_assistant("a_123")

    def test_delete_file_gracefully_handles_error(self):
        """_delete_file() doesn't raise on cleanup errors."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            extractor.client.files.delete = MagicMock(side_effect=Exception("delete failed"))
            
            # Should not raise
            extractor._delete_file("f_123")


class TestPolling:
    """Tests for run polling with adaptive backoff."""

    def test_wait_for_run_completed_immediately(self):
        """_wait_for_run() returns immediately when run is completed."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            mock_sleep = MagicMock()
            mock_time = MagicMock(side_effect=[0.0, 1.0])
            extractor = OpenAICVExtractor(_sleep=mock_sleep, _time=mock_time)
            
            run = MagicMock(status="completed")
            extractor._retrieve_run = MagicMock(return_value=run)
            
            result = extractor._wait_for_run(thread_id="t_123", run_id="r_123")
            assert result.status == "completed"

    def test_wait_for_run_polls_until_completed(self):
        """_wait_for_run() polls multiple times until completed."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            mock_sleep = MagicMock()
            mock_time = MagicMock(side_effect=[0.0, 1.0, 2.0, 3.0])
            extractor = OpenAICVExtractor(_sleep=mock_sleep, _time=mock_time)
            
            runs = [
                MagicMock(status="in_progress"),
                MagicMock(status="in_progress"),
                MagicMock(status="completed"),
            ]
            extractor._retrieve_run = MagicMock(side_effect=runs)
            
            result = extractor._wait_for_run(thread_id="t_123", run_id="r_123")
            assert result.status == "completed"
            assert extractor._retrieve_run.call_count == 3

    def test_wait_for_run_timeout(self):
        """_wait_for_run() raises RuntimeError on timeout."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            mock_sleep = MagicMock()
            mock_time = MagicMock(side_effect=[0.0, 100.0, 200.0])  # Exceeds default 180s timeout
            extractor = OpenAICVExtractor(run_timeout_s=180.0, _sleep=mock_sleep, _time=mock_time)
            
            extractor._retrieve_run = MagicMock(return_value=MagicMock(status="in_progress"))
            
            with pytest.raises(RuntimeError, match="timed out"):
                extractor._wait_for_run(thread_id="t_123", run_id="r_123")


class TestMessageExtraction:
    """Tests for extracting text from assistant messages."""

    def test_extract_text_from_assistant_message(self):
        """_extract_text_from_messages() extracts text from assistant message."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            
            text_obj = MagicMock(value="Extracted text")
            content_part = MagicMock(type="text", text=text_obj)
            message = MagicMock(role="assistant", content=[content_part])
            messages = MagicMock(data=[message])
            
            result = extractor._extract_text_from_messages(messages)
            assert result == "Extracted text"

    def test_extract_text_handles_no_data(self):
        """_extract_text_from_messages() handles missing data gracefully."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            messages = MagicMock(data=None)
            
            result = extractor._extract_text_from_messages(messages)
            assert result == ""

    def test_extract_text_skips_non_assistant_messages(self):
        """_extract_text_from_messages() only extracts from assistant messages."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            
            text_obj = MagicMock(value="Assistant text")
            content_part = MagicMock(type="text", text=text_obj)
            
            user_msg = MagicMock(role="user", content=[content_part])
            asst_msg = MagicMock(role="assistant", content=[content_part])
            messages = MagicMock(data=[user_msg, asst_msg])
            
            result = extractor._extract_text_from_messages(messages)
            assert result == "Assistant text"


class TestParseAndValidate:
    """Tests for response parsing and schema validation."""

    def test_parse_plain_json(self):
        """_parse_and_validate() parses plain JSON."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            schema = extractor._load_cv_schema()
            
            response = json.dumps({
                "identity": {"title": "Dev", "full_name": "John Doe", "first_name": "John", "last_name": "Doe"},
                "sidebar": {}, "overview": "Test", "experiences": []
            })
            
            with patch('cvextract.extractors.openai_extractor.get_verifier') as mock_get_verifier:
                mock_verifier = MagicMock()
                mock_verifier.verify.return_value = MagicMock(ok=True)
                mock_get_verifier.return_value = mock_verifier
                
                result = extractor._parse_and_validate(response, schema)
                assert result['identity']['full_name'] == 'John Doe'

    def test_parse_json_with_code_fence_json(self):
        """_parse_and_validate() strips ```json code fence."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            schema = extractor._load_cv_schema()
            
            response = '''```json
{"identity": {"title": "Dev", "full_name": "John", "first_name": "John", "last_name": "D"},
"sidebar": {}, "overview": "Test", "experiences": []}
```'''
            
            with patch('cvextract.extractors.openai_extractor.get_verifier') as mock_get_verifier:
                mock_verifier = MagicMock()
                mock_verifier.verify.return_value = MagicMock(ok=True)
                mock_get_verifier.return_value = mock_verifier
                
                result = extractor._parse_and_validate(response, schema)
                assert result['identity']['full_name'] == 'John'

    def test_parse_json_with_plain_code_fence(self):
        """_parse_and_validate() strips plain ``` code fence."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            schema = extractor._load_cv_schema()
            
            response = '''```
{"identity": {"title": "Dev", "full_name": "Jane", "first_name": "Jane", "last_name": "D"},
"sidebar": {}, "overview": "Test", "experiences": []}
```'''
            
            with patch('cvextract.extractors.openai_extractor.get_verifier') as mock_get_verifier:
                mock_verifier = MagicMock()
                mock_verifier.verify.return_value = MagicMock(ok=True)
                mock_get_verifier.return_value = mock_verifier
                
                result = extractor._parse_and_validate(response, schema)
                assert result['identity']['full_name'] == 'Jane'

    def test_parse_invalid_json_raises_error(self):
        """_parse_and_validate() raises ValueError for invalid JSON."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            schema = extractor._load_cv_schema()
            
            response = '{invalid json}'
            
            with pytest.raises(ValueError, match="Failed to parse response as JSON"):
                extractor._parse_and_validate(response, schema)

    def test_parse_schema_validation_failure(self):
        """_parse_and_validate() raises ValueError on schema validation failure."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            schema = extractor._load_cv_schema()
            
            response = json.dumps({"identity": {"title": "missing_required"}})  # Missing fields
            
            with patch('cvextract.extractors.openai_extractor.get_verifier') as mock_get_verifier:
                mock_verifier = MagicMock()
                mock_verifier.verify.return_value = MagicMock(ok=False, errors=["missing full_name"])
                mock_get_verifier.return_value = mock_verifier
                
                with pytest.raises(ValueError, match="Response does not match schema"):
                    extractor._parse_and_validate(response, schema)


class TestLoadCVSchema:
    """Tests for loading CV schema."""

    def test_load_cv_schema_returns_dict(self):
        """_load_cv_schema() returns valid schema dict."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            schema = extractor._load_cv_schema()
            
            assert isinstance(schema, dict)
            assert 'properties' in schema
            assert 'identity' in schema['properties']
            assert 'sidebar' in schema['properties']
            assert 'overview' in schema['properties']
            assert 'experiences' in schema['properties']


class TestFullExtractionFlow:
    """Tests for the complete extraction flow."""

    def test_extract_with_openai_full_success(self, tmp_path):
        """_extract_with_openai() successfully completes full flow."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            test_file = tmp_path / "test.docx"
            test_file.write_text("test content")
            schema = extractor._load_cv_schema()
            
            # Mock all the operations
            with patch('cvextract.extractors.openai_extractor.load_prompt', return_value="system prompt"):
                with patch('cvextract.extractors.openai_extractor.format_prompt', return_value="user prompt"):
                    extractor._upload_file = MagicMock(return_value="file_123")
                    extractor._create_assistant = MagicMock(return_value="asst_123")
                    extractor._create_thread = MagicMock(return_value="thread_123")
                    extractor._create_message = MagicMock()
                    extractor._create_run = MagicMock(return_value="run_123")
                    
                    # Mock successful run completion
                    run = MagicMock(status="completed")
                    extractor._wait_for_run = MagicMock(return_value=run)
                    
                    # Mock message retrieval
                    text_obj = MagicMock(value='{"identity": {"title": "Dev", "full_name": "Test", "first_name": "T", "last_name": "U"}, "sidebar": {}, "overview": "Test", "experiences": []}')
                    content_part = MagicMock(type="text", text=text_obj)
                    message = MagicMock(role="assistant", content=[content_part])
                    messages = MagicMock(data=[message])
                    extractor._list_messages = MagicMock(return_value=messages)
                    
                    extractor._delete_assistant = MagicMock()
                    extractor._delete_file = MagicMock()
                    
                    with patch('cvextract.extractors.openai_extractor.get_verifier') as mock_get_verifier:
                        mock_verifier = MagicMock()
                        mock_verifier.verify.return_value = MagicMock(ok=True)
                        mock_get_verifier.return_value = mock_verifier
                        
                        result = extractor._extract_with_openai(test_file, schema)
                        
                        assert result
                        extractor._upload_file.assert_called_once()
                        extractor._create_assistant.assert_called_once()
                        extractor._create_thread.assert_called_once()
                        extractor._create_message.assert_called_once()
                        extractor._create_run.assert_called_once()
                        extractor._wait_for_run.assert_called_once()
                        extractor._delete_assistant.assert_called_once()
                        extractor._delete_file.assert_called_once()

    def test_extract_with_openai_cleanup_on_upload_failure(self, tmp_path):
        """_extract_with_openai() cleans up even when upload fails."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            test_file = tmp_path / "test.docx"
            test_file.write_text("test content")
            schema = extractor._load_cv_schema()
            
            with patch('cvextract.extractors.openai_extractor.load_prompt', return_value="system prompt"):
                with patch('cvextract.extractors.openai_extractor.format_prompt', return_value="user prompt"):
                    extractor._upload_file = MagicMock(side_effect=Exception("Upload failed"))
                    extractor._delete_assistant = MagicMock()
                    extractor._delete_file = MagicMock()
                    
                    with pytest.raises(Exception, match="Upload failed"):
                        extractor._extract_with_openai(test_file, schema)
                    
                    # Cleanup should not be called since upload failed before creating resources
                    extractor._delete_assistant.assert_not_called()
                    extractor._delete_file.assert_not_called()

    def test_extract_with_openai_cleanup_on_assistant_failure(self, tmp_path):
        """_extract_with_openai() cleans up file when assistant creation fails."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            test_file = tmp_path / "test.docx"
            test_file.write_text("test content")
            schema = extractor._load_cv_schema()
            
            with patch('cvextract.extractors.openai_extractor.load_prompt', return_value="system prompt"):
                with patch('cvextract.extractors.openai_extractor.format_prompt', return_value="user prompt"):
                    extractor._upload_file = MagicMock(return_value="file_123")
                    extractor._create_assistant = MagicMock(side_effect=Exception("Assistant creation failed"))
                    extractor._delete_assistant = MagicMock()
                    extractor._delete_file = MagicMock()
                    
                    with pytest.raises(Exception, match="Assistant creation failed"):
                        extractor._extract_with_openai(test_file, schema)
                    
                    # Should clean up the file that was uploaded
                    extractor._delete_file.assert_called_once_with("file_123")
                    # Assistant was never created, so cleanup shouldn't be called for it
                    extractor._delete_assistant.assert_not_called()


class TestBackoffWithMultiplier:
    """Tests for backoff behavior with write multiplier."""

    def test_write_operation_uses_multiplier(self):
        """_sleep_with_backoff() applies write_multiplier for write operations."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            mock_sleep = MagicMock()
            config = _RetryConfig(base_delay_s=1.0, max_delay_s=100.0, write_multiplier=2.0, deterministic=True)
            extractor = OpenAICVExtractor(retry_config=config, _sleep=mock_sleep)
            
            exc = MagicMock(status_code=429, headers={})
            
            # Write operation: base * 2^0 * 2.0 = 1.0 * 1 * 2.0 = 2.0
            extractor._sleep_with_backoff(0, is_write=True, exc=exc)
            mock_sleep.assert_called_with(2.0)

    def test_read_operation_no_multiplier(self):
        """_sleep_with_backoff() doesn't apply multiplier for read operations."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            mock_sleep = MagicMock()
            config = _RetryConfig(base_delay_s=1.0, max_delay_s=100.0, write_multiplier=2.0, deterministic=True)
            extractor = OpenAICVExtractor(retry_config=config, _sleep=mock_sleep)
            
            exc = MagicMock(status_code=429, headers={})
            
            # Read operation: base * 2^0 * 1.0 = 1.0
            extractor._sleep_with_backoff(0, is_write=False, exc=exc)
            mock_sleep.assert_called_with(1.0)


class TestPollingSchedule:
    """Tests for adaptive polling schedule."""

    def test_polling_follows_schedule(self):
        """_wait_for_run() follows the adaptive polling schedule."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            mock_sleep = MagicMock()
            mock_time = MagicMock(side_effect=[0.0, 1.0, 2.0, 3.0, 5.0, 8.0])
            extractor = OpenAICVExtractor(_sleep=mock_sleep, _time=mock_time)
            
            runs = [
                MagicMock(status="in_progress"),  # First check
                MagicMock(status="in_progress"),  # After 1st sleep
                MagicMock(status="in_progress"),  # After 2nd sleep
                MagicMock(status="in_progress"),  # After 3rd sleep
                MagicMock(status="completed"),    # After 4th sleep
            ]
            extractor._retrieve_run = MagicMock(side_effect=runs)
            
            result = extractor._wait_for_run(thread_id="t_123", run_id="r_123")
            
            assert result.status == "completed"
            # Verify schedule: [1.0, 1.0, 1.0, 2.0, 3.0] - initial sleep + 4 loop iterations
            expected_sleeps = [1.0, 1.0, 1.0, 2.0, 3.0]
            actual_sleeps = [call[0][0] for call in mock_sleep.call_args_list]
            assert actual_sleeps == expected_sleeps


class TestMessageExtractionEdgeCases:
    """Tests for edge cases in message extraction."""

    def test_extract_text_with_multiple_assistant_messages(self):
        """_extract_text_from_messages() uses latest assistant message."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            
            # Create multiple messages - first one is the latest
            text_obj_1 = MagicMock(value="Latest message")
            content_1 = MagicMock(type="text", text=text_obj_1)
            msg_1 = MagicMock(role="assistant", content=[content_1])
            
            text_obj_2 = MagicMock(value="Earlier message")
            content_2 = MagicMock(type="text", text=text_obj_2)
            msg_2 = MagicMock(role="assistant", content=[content_2])
            
            messages = MagicMock(data=[msg_1, msg_2])
            
            result = extractor._extract_text_from_messages(messages)
            # Should get the first (latest) assistant message
            assert result == "Latest message"

    def test_extract_text_with_missing_text_value(self):
        """_extract_text_from_messages() handles missing text.value gracefully."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            
            text_obj = MagicMock(value=None)  # Missing value
            content_part = MagicMock(type="text", text=text_obj)
            message = MagicMock(role="assistant", content=[content_part])
            messages = MagicMock(data=[message])
            
            result = extractor._extract_text_from_messages(messages)
            assert result == ""

    def test_extract_text_with_empty_content_list(self):
        """_extract_text_from_messages() handles empty content gracefully."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            
            message = MagicMock(role="assistant", content=[])
            messages = MagicMock(data=[message])
            
            result = extractor._extract_text_from_messages(messages)
            assert result == ""

    def test_extract_text_mixed_content_types(self):
        """_extract_text_from_messages() handles mixed content types."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            
            # Text part
            text_obj = MagicMock(value="Text content")
            text_part = MagicMock(type="text", text=text_obj)
            
            # Non-text part
            other_part = MagicMock(type="file_citation")
            
            message = MagicMock(role="assistant", content=[text_part, other_part])
            messages = MagicMock(data=[message])
            
            result = extractor._extract_text_from_messages(messages)
            assert result == "Text content"


class TestGetStatusCode:
    """Tests for status code extraction from exceptions."""

    def test_get_status_code_direct_attribute(self):
        """_get_status_code() extracts status_code attribute."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            exc = Exception("Test error")
            exc.status_code = 429
            
            status = extractor._get_status_code(exc)
            assert status == 429

    def test_get_status_code_nested_in_response(self):
        """_get_status_code() extracts status from nested response object."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            
            response = MagicMock(status_code=503)
            exc = Exception("Test error")
            exc.response = response
            
            status = extractor._get_status_code(exc)
            assert status == 503

    def test_get_status_code_missing(self):
        """_get_status_code() returns None when status not found."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            exc = Exception("Test error")
            
            status = extractor._get_status_code(exc)
            assert status is None


class TestDeterministicBackoff:
    """Tests for deterministic backoff mode."""

    def test_deterministic_mode_no_jitter(self):
        """_sleep_with_backoff() removes jitter in deterministic mode."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            mock_sleep = MagicMock()
            # Run test multiple times to ensure consistent sleep values
            config = _RetryConfig(base_delay_s=1.0, max_delay_s=10.0, deterministic=True)
            extractor = OpenAICVExtractor(retry_config=config, _sleep=mock_sleep)
            
            exc = MagicMock(status_code=429, headers={})
            
            # Call multiple times and collect sleep values
            sleep_values = []
            for i in range(3):
                mock_sleep.reset_mock()
                extractor._sleep_with_backoff(0, is_write=False, exc=exc)
                sleep_values.append(mock_sleep.call_args[0][0])
            
            # All should be exactly 1.0 (no jitter in deterministic mode)
            assert sleep_values == [1.0, 1.0, 1.0]

    def test_non_deterministic_mode_has_jitter(self):
        """_sleep_with_backoff() adds jitter in non-deterministic mode."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            mock_sleep = MagicMock()
            config = _RetryConfig(base_delay_s=1.0, max_delay_s=10.0, deterministic=False)
            extractor = OpenAICVExtractor(retry_config=config, _sleep=mock_sleep)
            
            exc = MagicMock(status_code=429, headers={})
            
            # Call multiple times and collect sleep values
            sleep_values = []
            for i in range(5):
                mock_sleep.reset_mock()
                extractor._sleep_with_backoff(0, is_write=False, exc=exc)
                sleep_values.append(mock_sleep.call_args[0][0])
            
            # Should have variation in values (jitter applied)
            # All should be between 0.25 and 1.0
            assert all(0.25 <= v <= 1.0 for v in sleep_values)
            # With 5 random values, at least some should be different
            assert len(set(sleep_values)) > 1


class TestPromptLoadingAndFormatting:
    """Tests for prompt loading and formatting in _extract_with_openai()."""

    def test_extract_with_openai_fails_when_system_prompt_not_found(self, tmp_path):
        """_extract_with_openai() raises RuntimeError when system prompt fails to load."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            test_file = tmp_path / "test.txt"
            test_file.write_text("test")
            
            # Mock load_prompt to return None for system prompt
            with patch('cvextract.extractors.openai_extractor.load_prompt', return_value=None):
                with pytest.raises(RuntimeError, match="Failed to load system prompt"):
                    cv_schema = {
                        "identity": {"title": "", "full_name": "", "first_name": "", "last_name": ""},
                        "sidebar": {}, "overview": "", "experiences": []
                    }
                    extractor._extract_with_openai(test_file, cv_schema)

    def test_extract_with_openai_fails_when_user_prompt_format_fails(self, tmp_path):
        """_extract_with_openai() raises RuntimeError when user prompt formatting fails."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            test_file = tmp_path / "test.txt"
            test_file.write_text("test")
            
            # Mock load_prompt to return valid system prompt
            # But format_prompt returns None
            with patch('cvextract.extractors.openai_extractor.load_prompt', return_value="system prompt"):
                with patch('cvextract.extractors.openai_extractor.format_prompt', return_value=None):
                    with pytest.raises(RuntimeError, match="Failed to format user prompt"):
                        cv_schema = {
                            "identity": {"title": "", "full_name": "", "first_name": "", "last_name": ""},
                            "sidebar": {}, "overview": "", "experiences": []
                        }
                        extractor._extract_with_openai(test_file, cv_schema)


class TestRetryAfterExceptionHandling:
    """Tests for _get_retry_after_s() exception handling paths."""

    def test_retry_after_headers_exception(self):
        """_get_retry_after_s() returns None when headers.get() raises exception."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            
            # Create headers object that raises on .get()
            headers = MagicMock()
            headers.get.side_effect = Exception("Unexpected error")
            
            exc = Exception("Test error")
            exc.headers = headers
            
            result = extractor._get_retry_after_s(exc)
            assert result is None

    def test_retry_after_float_conversion_failure(self):
        """_get_retry_after_s() returns None when float() conversion fails."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            
            headers = {"retry-after": "not-a-number"}
            exc = Exception("Test error")
            exc.headers = headers
            
            result = extractor._get_retry_after_s(exc)
            assert result is None

    def test_retry_after_from_response_headers(self):
        """_get_retry_after_s() extracts retry-after from response.headers."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            
            response = MagicMock()
            response.headers = {"Retry-After": "2.5"}
            exc = Exception("Test error")
            exc.response = response
            
            result = extractor._get_retry_after_s(exc)
            assert result == 2.5


class TestMessageExtractionFallbacks:
    """Tests for fallback paths in _extract_text_from_messages()."""

    def test_extract_text_fallback_any_message_content(self):
        """_extract_text_from_messages() falls back to any message with text content."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            
            # Create messages where type != "text" but text_obj is a string
            part = MagicMock()
            part.type = "image_file"  # Not "text"
            part.text = "Fallback text content"
            
            msg = MagicMock()
            msg.role = "assistant"
            msg.content = [part]
            
            messages = MagicMock()
            messages.data = [msg]
            
            result = extractor._extract_text_from_messages(messages)
            assert result == "Fallback text content"

    def test_extract_text_fallback_with_missing_text_attribute(self):
        """_extract_text_from_messages() handles missing text attribute in fallback."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            
            # Part with no text attribute
            part = MagicMock(spec=[])
            part.type = "image_file"
            
            msg = MagicMock()
            msg.role = "assistant"
            msg.content = [part]
            
            messages = MagicMock()
            messages.data = [msg]
            
            result = extractor._extract_text_from_messages(messages)
            assert result == ""

    def test_extract_text_fallback_with_none_text_value(self):
        """_extract_text_from_messages() handles None text_obj.value."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            
            text_obj = MagicMock()
            text_obj.value = None
            
            part = MagicMock()
            part.type = "text"
            part.text = text_obj
            
            msg = MagicMock()
            msg.role = "assistant"
            msg.content = [part]
            
            messages = MagicMock()
            messages.data = [msg]
            
            result = extractor._extract_text_from_messages(messages)
            assert result == ""

    def test_extract_text_with_whitespace_only_content(self):
        """_extract_text_from_messages() skips whitespace-only content."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            
            text_obj = MagicMock()
            text_obj.value = "   \n\t   "
            
            part = MagicMock()
            part.type = "text"
            part.text = text_obj
            
            msg = MagicMock()
            msg.role = "assistant"
            msg.content = [part]
            
            messages = MagicMock()
            messages.data = [msg]
            
            result = extractor._extract_text_from_messages(messages)
            assert result == ""

    def test_extract_text_no_content_list(self):
        """_extract_text_from_messages() skips messages with no content list."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            
            msg = MagicMock()
            msg.role = "assistant"
            msg.content = None
            
            messages = MagicMock()
            messages.data = [msg]
            
            result = extractor._extract_text_from_messages(messages)
            assert result == ""


class TestCleanupErrorHandling:
    """Tests for graceful error handling in cleanup operations."""

    def test_delete_assistant_catches_exception(self):
        """_delete_assistant() catches and suppresses exceptions."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            
            # Mock _call_with_retry to raise an exception
            extractor._call_with_retry = MagicMock(side_effect=RuntimeError("Cleanup failed"))
            
            # Should not raise
            extractor._delete_assistant("assistant_123")

    def test_delete_file_catches_exception(self):
        """_delete_file() catches and suppresses exceptions."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = OpenAICVExtractor()
            
            # Mock _call_with_retry to raise an exception
            extractor._call_with_retry = MagicMock(side_effect=RuntimeError("Cleanup failed"))
            
            # Should not raise
            extractor._delete_file("file_123")



