"""
Tests for cli_execute_adjust module to achieve 91% coverage.

These tests cover error paths, validation logic, and edge cases.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from cvextract.cli_config import UserConfig, AdjustStage, AdjusterConfig, ExtractStage, RenderStage
from cvextract.cli_execute_adjust import execute
from cvextract.shared import UnitOfWork


class TestCliExecuteAdjustCoverage:
    """Tests for cli_execute_adjust.execute function."""
    
    def test_execute_returns_work_when_adjust_missing(self, tmp_path):
        """Test execute returns work unchanged when config.adjust is None."""
        config = UserConfig(target_dir=tmp_path)
        work = UnitOfWork(config=config, input=tmp_path / "input.json", output=tmp_path / "output.json")
        
        result = execute(work)
        
        assert result == work
    
    def test_execute_returns_work_when_output_missing(self, tmp_path):
        """Test execute returns work when work.output is None."""
        config = UserConfig(
            target_dir=tmp_path,
            adjust=AdjustStage(
                data=tmp_path / "data.json",
                adjusters=[AdjusterConfig(name="test", params={})]
            )
        )
        work = UnitOfWork(config=config, input=tmp_path / "input.json", output=None)
        
        result = execute(work)
        
        assert result == work
    
    def test_execute_handles_source_from_extract(self, tmp_path):
        """Test execute resolves source_base from extract.source."""
        # Create valid JSON file
        json_file = tmp_path / "subdir" / "test.json"
        json_file.parent.mkdir(parents=True, exist_ok=True)
        cv_data = {
            "identity": {"title": "Dev", "full_name": "Test", "first_name": "T", "last_name": "Test"},
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        json_file.write_text(json.dumps(cv_data))
        
        source_file = tmp_path / "source.docx"
        source_file.touch()
        
        config = UserConfig(
            target_dir=tmp_path,
            extract=ExtractStage(source=source_file),
            adjust=AdjustStage(
                data=json_file,
                adjusters=[AdjusterConfig(name="test-adjuster", params={})]
            )
        )
        
        work = UnitOfWork(
            config=config,
            initial_input=json_file,
            input=json_file,
            output=json_file
        )
        
        with patch('cvextract.cli_execute_adjust.get_adjuster') as mock_get:
            mock_adjuster = MagicMock()
            mock_adjuster.validate_params = MagicMock()
            mock_adjuster.adjust = MagicMock(return_value=work)
            mock_get.return_value = mock_adjuster
            
            result = execute(work)
            
            # Should have called the adjuster
            mock_adjuster.adjust.assert_called_once()
    
    def test_execute_handles_source_from_adjust_data(self, tmp_path):
        """Test execute resolves source_base from adjust.data when no extract."""
        # Create valid JSON file
        json_file = tmp_path / "subdir" / "test.json"
        json_file.parent.mkdir(parents=True, exist_ok=True)
        cv_data = {
            "identity": {"title": "Dev", "full_name": "Test", "first_name": "T", "last_name": "Test"},
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        json_file.write_text(json.dumps(cv_data))
        
        config = UserConfig(
            target_dir=tmp_path,
            adjust=AdjustStage(
                data=json_file,
                adjusters=[AdjusterConfig(name="test-adjuster", params={})]
            )
        )
        
        work = UnitOfWork(
            config=config,
            initial_input=json_file,
            input=json_file,
            output=json_file
        )
        
        with patch('cvextract.cli_execute_adjust.get_adjuster') as mock_get:
            mock_adjuster = MagicMock()
            mock_adjuster.validate_params = MagicMock()
            mock_adjuster.adjust = MagicMock(return_value=work)
            mock_get.return_value = mock_adjuster
            
            result = execute(work)
            
            # Should have called the adjuster
            mock_adjuster.adjust.assert_called_once()
    
    def test_execute_handles_source_from_render_data(self, tmp_path):
        """Test execute resolves source_base from render.data when no extract/adjust."""
        # Create valid JSON file
        json_file = tmp_path / "subdir" / "test.json"
        json_file.parent.mkdir(parents=True, exist_ok=True)
        cv_data = {
            "identity": {"title": "Dev", "full_name": "Test", "first_name": "T", "last_name": "Test"},
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        json_file.write_text(json.dumps(cv_data))
        
        template = tmp_path / "template.docx"
        template.touch()
        
        config = UserConfig(
            target_dir=tmp_path,
            render=RenderStage(template=template, data=json_file),
            adjust=AdjustStage(
                data=None,
                adjusters=[AdjusterConfig(name="test-adjuster", params={})]
            )
        )
        
        work = UnitOfWork(
            config=config,
            initial_input=json_file,
            input=json_file,
            output=json_file
        )
        
        with patch('cvextract.cli_execute_adjust.get_adjuster') as mock_get:
            mock_adjuster = MagicMock()
            mock_adjuster.validate_params = MagicMock()
            mock_adjuster.adjust = MagicMock(return_value=work)
            mock_get.return_value = mock_adjuster
            
            result = execute(work)
            
            # Should have called the adjuster
            mock_adjuster.adjust.assert_called_once()
    
    def test_execute_handles_no_source_fallback(self, tmp_path):
        """Test execute falls back to base_input.parent when no source available."""
        # Create valid JSON file
        json_file = tmp_path / "subdir" / "test.json"
        json_file.parent.mkdir(parents=True, exist_ok=True)
        cv_data = {
            "identity": {"title": "Dev", "full_name": "Test", "first_name": "T", "last_name": "Test"},
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        json_file.write_text(json.dumps(cv_data))
        
        config = UserConfig(
            target_dir=tmp_path,
            adjust=AdjustStage(
                data=None,
                adjusters=[AdjusterConfig(name="test-adjuster", params={})]
            )
        )
        
        work = UnitOfWork(
            config=config,
            initial_input=json_file,
            input=json_file,
            output=json_file
        )
        
        with patch('cvextract.cli_execute_adjust.get_adjuster') as mock_get:
            mock_adjuster = MagicMock()
            mock_adjuster.validate_params = MagicMock()
            mock_adjuster.adjust = MagicMock(return_value=work)
            mock_get.return_value = mock_adjuster
            
            result = execute(work)
            
            # Should have called the adjuster
            mock_adjuster.adjust.assert_called_once()
    
    def test_execute_handles_relative_to_value_error(self, tmp_path):
        """Test execute handles ValueError from relative_to."""
        # Create JSON file in completely different path
        other_dir = tmp_path / "other"
        other_dir.mkdir()
        json_file = other_dir / "test.json"
        cv_data = {
            "identity": {"title": "Dev", "full_name": "Test", "first_name": "T", "last_name": "Test"},
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        json_file.write_text(json.dumps(cv_data))
        
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        
        config = UserConfig(
            target_dir=tmp_path,
            input_dir=source_dir,
            adjust=AdjustStage(
                data=json_file,
                adjusters=[AdjusterConfig(name="test-adjuster", params={})]
            )
        )
        
        work = UnitOfWork(
            config=config,
            initial_input=json_file,
            input=json_file,
            output=json_file
        )
        
        with patch('cvextract.cli_execute_adjust.get_adjuster') as mock_get:
            mock_adjuster = MagicMock()
            mock_adjuster.validate_params = MagicMock()
            mock_adjuster.adjust = MagicMock(return_value=work)
            mock_get.return_value = mock_adjuster
            
            result = execute(work)
            
            # Should have handled the ValueError and continued
            mock_adjuster.adjust.assert_called_once()
    
    def test_execute_applies_delay_between_adjusters(self, tmp_path):
        """Test execute applies delay between multiple adjusters."""
        json_file = tmp_path / "test.json"
        cv_data = {
            "identity": {"title": "Dev", "full_name": "Test", "first_name": "T", "last_name": "Test"},
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        json_file.write_text(json.dumps(cv_data))
        
        config = UserConfig(
            target_dir=tmp_path,
            adjust=AdjustStage(
                data=json_file,
                adjusters=[
                    AdjusterConfig(name="adjuster1", params={}),
                    AdjusterConfig(name="adjuster2", params={})
                ]
            )
        )
        
        work = UnitOfWork(
            config=config,
            initial_input=json_file,
            input=json_file,
            output=json_file
        )
        
        with patch('cvextract.cli_execute_adjust.get_adjuster') as mock_get, \
             patch('cvextract.cli_execute_adjust.time.sleep') as mock_sleep:
            mock_adjuster = MagicMock()
            mock_adjuster.validate_params = MagicMock()
            mock_adjuster.adjust = MagicMock(return_value=work)
            mock_get.return_value = mock_adjuster
            
            result = execute(work)
            
            # Should have called sleep once (between adjusters)
            mock_sleep.assert_called_once_with(3.0)
            # Should have called adjust twice
            assert mock_adjuster.adjust.call_count == 2
    
    def test_execute_skips_unknown_adjuster(self, tmp_path):
        """Test execute skips unknown adjuster and continues."""
        json_file = tmp_path / "test.json"
        cv_data = {
            "identity": {"title": "Dev", "full_name": "Test", "first_name": "T", "last_name": "Test"},
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        json_file.write_text(json.dumps(cv_data))
        
        config = UserConfig(
            target_dir=tmp_path,
            adjust=AdjustStage(
                data=json_file,
                adjusters=[AdjusterConfig(name="unknown-adjuster", params={})]
            )
        )
        
        work = UnitOfWork(
            config=config,
            initial_input=json_file,
            input=json_file,
            output=json_file
        )
        
        with patch('cvextract.cli_execute_adjust.get_adjuster') as mock_get:
            mock_get.return_value = None  # Simulate unknown adjuster
            
            result = execute(work)
            
            # Should return work without error
            assert result is not None
    
    def test_execute_handles_validation_error(self, tmp_path):
        """Test execute handles ValueError when adjuster validation fails and returns work."""
        json_file = tmp_path / "test.json"
        cv_data = {
            "identity": {"title": "Dev", "full_name": "Test", "first_name": "T", "last_name": "Test"},
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        json_file.write_text(json.dumps(cv_data))
        
        config = UserConfig(
            target_dir=tmp_path,
            adjust=AdjustStage(
                data=json_file,
                adjusters=[AdjusterConfig(name="test-adjuster", params={"invalid": "param"})]
            )
        )
        
        work = UnitOfWork(
            config=config,
            initial_input=json_file,
            input=json_file,
            output=json_file
        )
        
        with patch('cvextract.cli_execute_adjust.get_adjuster') as mock_get:
            mock_adjuster = MagicMock()
            mock_adjuster.validate_params = MagicMock(side_effect=ValueError("Invalid params"))
            mock_get.return_value = mock_adjuster
            
            # The execute function catches exceptions and returns base_work
            result = execute(work)
            
            # Should return work without raising
            assert result == work
    
    def test_execute_handles_exception_with_debug(self, tmp_path):
        """Test execute handles exception and returns base work when debug enabled."""
        json_file = tmp_path / "test.json"
        cv_data = {
            "identity": {"title": "Dev", "full_name": "Test", "first_name": "T", "last_name": "Test"},
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        json_file.write_text(json.dumps(cv_data))
        
        config = UserConfig(
            target_dir=tmp_path,
            verbosity="debug",  # Set verbosity to "debug" instead of debug=True
            adjust=AdjustStage(
                data=json_file,
                adjusters=[AdjusterConfig(name="test-adjuster", params={})]
            )
        )
        
        work = UnitOfWork(
            config=config,
            initial_input=json_file,
            input=json_file,
            output=json_file
        )
        
        with patch('cvextract.cli_execute_adjust.get_adjuster') as mock_get:
            mock_adjuster = MagicMock()
            mock_adjuster.validate_params = MagicMock()
            mock_adjuster.adjust = MagicMock(side_effect=RuntimeError("Test error"))
            mock_get.return_value = mock_adjuster
            
            result = execute(work)
            
            # Should return base work without raising
            assert result == work
