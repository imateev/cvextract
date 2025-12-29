"""Tests for cli_prepare module to achieve 91% coverage."""

import os
import pytest
from pathlib import Path
from cvextract.cli_prepare import _collect_inputs, prepare_execution_environment
from cvextract.cli_config import UserConfig, ExtractStage, ApplyStage
from cvextract.logging_utils import LOG


class TestCollectInputs:
    """Tests for _collect_inputs function."""

    def test_collect_inputs_valid_docx_extraction(self, tmp_path):
        """Test _collect_inputs returns single DOCX file for extraction."""
        test_file = tmp_path / "test.docx"
        test_file.touch()
        
        result = _collect_inputs(test_file, is_extraction=True, template_path=None)
        
        assert result == [test_file]

    def test_collect_inputs_valid_json_apply(self, tmp_path):
        """Test _collect_inputs returns single JSON file for apply."""
        test_file = tmp_path / "data.json"
        test_file.touch()
        
        result = _collect_inputs(test_file, is_extraction=False, template_path=None)
        
        assert result == [test_file]

    def test_collect_inputs_nonexistent_file(self, tmp_path):
        """Test _collect_inputs raises error for nonexistent file."""
        nonexistent = tmp_path / "nonexistent.docx"
        
        with pytest.raises(FileNotFoundError, match="Path not found"):
            _collect_inputs(nonexistent, is_extraction=True, template_path=None)

    def test_collect_inputs_directory_not_supported(self, tmp_path):
        """Test _collect_inputs raises error for directory input."""
        with pytest.raises(ValueError, match="Directories are not supported"):
            _collect_inputs(tmp_path, is_extraction=True, template_path=None)

    def test_collect_inputs_wrong_extension_extraction(self, tmp_path):
        """Test _collect_inputs raises error for non-DOCX file during extraction."""
        test_file = tmp_path / "test.json"
        test_file.touch()
        
        with pytest.raises(ValueError, match="Input file must be a DOCX file"):
            _collect_inputs(test_file, is_extraction=True, template_path=None)

    def test_collect_inputs_wrong_extension_apply(self, tmp_path):
        """Test _collect_inputs raises error for non-JSON file during apply."""
        test_file = tmp_path / "test.docx"
        test_file.touch()
        
        with pytest.raises(ValueError, match="Input file must be a JSON file"):
            _collect_inputs(test_file, is_extraction=False, template_path=None)

    def test_collect_inputs_case_insensitive_extensions(self, tmp_path):
        """Test _collect_inputs handles uppercase extensions."""
        test_file = tmp_path / "test.DOCX"
        test_file.touch()
        
        result = _collect_inputs(test_file, is_extraction=True, template_path=None)
        
        assert result == [test_file]

    def test_collect_inputs_json_uppercase(self, tmp_path):
        """Test _collect_inputs handles uppercase JSON extension."""
        test_file = tmp_path / "test.JSON"
        test_file.touch()
        
        result = _collect_inputs(test_file, is_extraction=False, template_path=None)
        
        assert result == [test_file]

    def test_collect_inputs_symlink_treated_as_file(self, tmp_path):
        """Test _collect_inputs handles symlinks as files."""
        real_file = tmp_path / "real.docx"
        real_file.touch()
        symlink = tmp_path / "link.docx"
        symlink.symlink_to(real_file)
        
        result = _collect_inputs(symlink, is_extraction=True, template_path=None)
        
        assert result == [symlink]

    def test_collect_inputs_path_exists_but_not_file(self, tmp_path):
        """Test _collect_inputs raises error if path exists but isn't a file."""
        # Create a directory
        test_dir = tmp_path / "subdir"
        test_dir.mkdir()
        
        # Try to treat it as a file (should fail because is_dir returns True first)
        with pytest.raises(ValueError, match="Directories are not supported"):
            _collect_inputs(test_dir, is_extraction=True, template_path=None)

    def test_collect_inputs_special_file_not_regular(self, tmp_path):
        """Non-regular filesystem nodes (e.g., FIFOs) should trip the not-a-file branch."""
        fifo_path = tmp_path / "pipe.docx"
        os.mkfifo(fifo_path)
        with pytest.raises(FileNotFoundError, match="Path is not a file"):
            _collect_inputs(fifo_path, is_extraction=True, template_path=None)


class TestPrepareExecutionEnvironment:
    """Tests for prepare_execution_environment function."""

    def test_prepare_execution_environment_without_apply(self, tmp_path):
        """Test prepare_execution_environment without apply stage."""
        target = tmp_path / "output"
        config = UserConfig(target_dir=target)
        
        result = prepare_execution_environment(config)
        
        assert result == config
        assert target.is_dir()

    def test_prepare_execution_environment_with_valid_apply(self, tmp_path):
        """Test prepare_execution_environment with valid apply stage."""
        target = tmp_path / "output"
        template = tmp_path / "template.docx"
        template.touch()
        
        config = UserConfig(
            target_dir=target,
            apply=ApplyStage(template=template)
        )
        
        result = prepare_execution_environment(config)
        
        assert result == config
        assert target.is_dir()

    def test_prepare_execution_environment_template_not_found(self, tmp_path):
        """Test prepare_execution_environment raises error for missing template."""
        target = tmp_path / "output"
        template = tmp_path / "nonexistent.docx"
        
        config = UserConfig(
            target_dir=target,
            apply=ApplyStage(template=template)
        )
        
        with pytest.raises(ValueError, match="Invalid template"):
            prepare_execution_environment(config)

    def test_prepare_execution_environment_template_not_docx(self, tmp_path):
        """Test prepare_execution_environment raises error for non-DOCX template."""
        target = tmp_path / "output"
        template = tmp_path / "template.txt"
        template.touch()
        
        config = UserConfig(
            target_dir=target,
            apply=ApplyStage(template=template)
        )
        
        with pytest.raises(ValueError, match="Invalid template"):
            prepare_execution_environment(config)

    def test_prepare_execution_environment_creates_nested_target(self, tmp_path):
        """Test prepare_execution_environment creates nested target directories."""
        target = tmp_path / "level1" / "level2" / "output"
        config = UserConfig(target_dir=target)
        
        result = prepare_execution_environment(config)
        
        assert target.is_dir()

    def test_prepare_execution_environment_template_is_directory(self, tmp_path):
        """Test prepare_execution_environment handles template as directory."""
        target = tmp_path / "output"
        template = tmp_path / "template_dir"
        template.mkdir()
        
        config = UserConfig(
            target_dir=target,
            apply=ApplyStage(template=template)
        )
        
        with pytest.raises(ValueError, match="Invalid template"):
            prepare_execution_environment(config)

    def test_prepare_execution_environment_target_fails_is_dir_check(self, tmp_path, monkeypatch):
        """Simulate target_dir reporting False for is_dir to hit the validation branch."""
        target = tmp_path / "output"
        config = UserConfig(target_dir=target)

        original_is_dir = Path.is_dir

        def fake_is_dir(self):
            if self == target:
                return False
            return original_is_dir(self)

        monkeypatch.setattr(Path, "is_dir", fake_is_dir)

        with pytest.raises(ValueError, match="Target is not a directory"):
            prepare_execution_environment(config)

