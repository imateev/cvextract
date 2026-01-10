"""Tests for CLI customer adjustment features."""

from pathlib import Path

import cvextract.cli as cli


class TestCustomerAdjustmentConfiguration:
    """Tests for CLI customer adjustment and OpenAI model configuration."""

    def test_extract_apply_with_adjust_creates_correct_mode(self, tmp_path: Path):
        """When adjust-for-customer is provided in extract-apply mode, should set EXTRACT_ADJUST_RENDER mode."""
        config = cli.gather_user_requirements(
            [
                "--extract",
                f"source={tmp_path / 'test.docx'}",
                "--adjust",
                "name=openai-company-research",
                f"customer-url=https://example.com/customer",
                "openai-model=gpt-4o-mini",
                "--render",
                f"template={tmp_path / 'template.docx'}",
                "--target",
                str(tmp_path / "output"),
            ]
        )

        assert config.extract is not None
        assert config.adjust is not None
        assert config.render is not None
        assert (
            config.adjust.adjusters[0].params.get("customer-url")
            == "https://example.com/customer"
        )
        assert config.adjust.adjusters[0].openai_model == "gpt-4o-mini"

    def test_apply_with_adjust_creates_correct_mode(self, tmp_path: Path):
        """When adjust-for-customer is provided in apply mode, should set ADJUST_RENDER mode."""
        config = cli.gather_user_requirements(
            [
                "--adjust",
                "name=openai-company-research",
                f"data={tmp_path / 'data.json'}",
                f"customer-url=https://example.com/customer",
                "openai-model=gpt-4o-mini",
                "--render",
                f"template={tmp_path / 'template.docx'}",
                "--target",
                str(tmp_path / "output"),
            ]
        )

        assert config.extract is None
        assert config.adjust is not None
        assert config.render is not None
        assert (
            config.adjust.adjusters[0].params.get("customer-url")
            == "https://example.com/customer"
        )
        assert config.adjust.adjusters[0].openai_model == "gpt-4o-mini"
