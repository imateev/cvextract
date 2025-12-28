"""Tests for CLI customer adjustment features."""

import zipfile
from pathlib import Path
import cvextract.cli as cli


class TestCustomerAdjustmentConfiguration:
    """Tests for CLI customer adjustment and OpenAI model configuration."""

    def test_extract_apply_with_adjust_creates_correct_mode(self, tmp_path: Path):
        """When adjust-for-customer is provided in extract-apply mode, should set EXTRACT_ADJUST_RENDER mode."""
        config = cli.gather_user_requirements([
            "--mode", "extract-apply",
            "--source", str(tmp_path / "test.docx"),
            "--template", str(tmp_path / "template.docx"),
            "--target", str(tmp_path / "output"),
            "--adjust-for-customer", "https://example.com/customer",
            "--openai-model", "gpt-4o-mini",
        ])
        
        assert config.mode == cli.ExecutionMode.EXTRACT_ADJUST_RENDER
        assert config.adjust_url == "https://example.com/customer"
        assert config.openai_model == "gpt-4o-mini"

    def test_apply_with_adjust_creates_correct_mode(self, tmp_path: Path):
        """When adjust-for-customer is provided in apply mode, should set ADJUST_RENDER mode."""
        config = cli.gather_user_requirements([
            "--mode", "apply",
            "--source", str(tmp_path / "data.json"),
            "--template", str(tmp_path / "template.docx"),
            "--target", str(tmp_path / "output"),
            "--adjust-for-customer", "https://example.com/customer",
            "--openai-model", "gpt-4o-mini",
        ])
        
        assert config.mode == cli.ExecutionMode.ADJUST_RENDER
        assert config.adjust_url == "https://example.com/customer"
        assert config.openai_model == "gpt-4o-mini"
    
    def test_extract_apply_with_adjust_dry_run_creates_extract_adjust_mode(self, tmp_path: Path):
        """When adjust-for-customer and dry-run are provided, should set EXTRACT_ADJUST mode."""
        config = cli.gather_user_requirements([
            "--mode", "extract-apply",
            "--source", str(tmp_path / "test.docx"),
            "--template", str(tmp_path / "template.docx"),
            "--target", str(tmp_path / "output"),
            "--adjust-for-customer", "https://example.com/customer",
            "--adjust-dry-run",
        ])
        
        assert config.mode == cli.ExecutionMode.EXTRACT_ADJUST
        assert config.adjust_dry_run is True
    
    def test_apply_with_adjust_dry_run_creates_adjust_mode(self, tmp_path: Path):
        """When adjust-for-customer and dry-run are provided in apply mode, should set ADJUST mode."""
        config = cli.gather_user_requirements([
            "--mode", "apply",
            "--source", str(tmp_path / "data.json"),
            "--template", str(tmp_path / "template.docx"),
            "--target", str(tmp_path / "output"),
            "--adjust-for-customer", "https://example.com/customer",
            "--adjust-dry-run",
        ])
        
        assert config.mode == cli.ExecutionMode.ADJUST
        assert config.adjust_dry_run is True
