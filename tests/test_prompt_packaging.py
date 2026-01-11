"""
Tests for verifying prompts are included in package and can be loaded after installation.

This test ensures prompts are properly packaged and accessible via the Path(__file__).parent
pattern (the platform-independent way for Python packages to include data files).
"""

from pathlib import Path


class TestPromptPackaging:
    """Tests to verify prompts are included in the installed package."""

    def test_prompts_accessible_via_pathlib(self):
        """Test that prompts are accessible via Path(__file__).parent pattern."""
        # Check extractor prompts
        from cvextract.extractors import openai_extractor

        extractor_module_path = Path(openai_extractor.__file__).parent
        extractor_prompts_dir = extractor_module_path / "prompts"

        assert (
            extractor_prompts_dir.exists()
        ), f"Extractor prompts directory not found at {extractor_prompts_dir}"
        assert (
            extractor_prompts_dir.is_dir()
        ), f"Extractor prompts path is not a directory: {extractor_prompts_dir}"

        extractor_expected_prompts = [
            "cv_extraction_system.md",
            "cv_extraction_user.md",
        ]

        for prompt_file in extractor_expected_prompts:
            prompt_path = extractor_prompts_dir / prompt_file
            assert (
                prompt_path.exists()
            ), f"Extractor prompt file not found: {prompt_file}"
            assert (
                prompt_path.is_file()
            ), f"Extractor prompt path is not a file: {prompt_file}"
            content = prompt_path.read_text(encoding="utf-8")
            assert len(content) > 0, f"Extractor prompt file is empty: {prompt_file}"

        # Also verify the adjuster prompts are in the adjusters directory
        from cvextract.adjusters import openai_job_specific_adjuster

        adjuster_module_path = Path(openai_job_specific_adjuster.__file__).parent
        adjuster_prompts_dir = adjuster_module_path / "prompts"

        adjuster_expected_prompts = [
            "adjuster_promp_for_a_company.md",
            "adjuster_promp_for_specific_job.md",
            "adjuster_prompt_translate_cv.md",
            "website_analysis_prompt.md",
        ]

        for prompt_file in adjuster_expected_prompts:
            prompt_path = adjuster_prompts_dir / prompt_file
            assert (
                prompt_path.exists()
            ), f"Adjuster prompt file not found: {prompt_file}"
            assert (
                prompt_path.is_file()
            ), f"Adjuster prompt path is not a file: {prompt_file}"

            # Verify file is readable and has content
            content = prompt_path.read_text(encoding="utf-8")
            assert len(content) > 0, f"Adjuster prompt file is empty: {prompt_file}"

    def test_all_prompts_loadable(self):
        """Test that all prompt files can be loaded via load_prompt function."""
        from cvextract.shared import load_prompt

        prompts_to_test = [
            "website_analysis_prompt",
            "adjuster_promp_for_specific_job",
            "adjuster_prompt_translate_cv",
            "cv_extraction_system",
            "cv_extraction_user",
        ]

        for prompt_name in prompts_to_test:
            result = load_prompt(prompt_name)
            assert result is not None, f"Failed to load prompt: {prompt_name}"
            assert isinstance(result, str), f"Prompt is not a string: {prompt_name}"
            assert len(result) > 0, f"Prompt is empty: {prompt_name}"
