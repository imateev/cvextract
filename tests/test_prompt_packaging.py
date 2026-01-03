"""
Tests for verifying prompts are included in package and can be loaded after installation.

This test ensures prompts are properly packaged and accessible via the Path(__file__).parent
pattern (the platform-independent way for Python packages to include data files).
"""

import sys
from pathlib import Path
import tempfile
import subprocess
import pytest


class TestPromptPackaging:
    """Tests to verify prompts are included in the installed package."""

    def test_prompts_accessible_via_pathlib(self):
        """Test that prompts are accessible via Path(__file__).parent pattern."""
        # Import the prompt_loader module
        from cvextract.ml_adjustment import prompt_loader
        
        # Get the prompts directory path
        module_path = Path(prompt_loader.__file__).parent
        prompts_dir = module_path / "prompts"
        
        # Verify directory exists
        assert prompts_dir.exists(), f"Prompts directory not found at {prompts_dir}"
        assert prompts_dir.is_dir(), f"Prompts path is not a directory: {prompts_dir}"
        
        # Verify all expected prompt files exist
        expected_prompts = [
            "system_prompt.md",
            "website_analysis_prompt.md",
            "cv_extraction_system.md",
            "cv_extraction_user.md",
        ]
        
        for prompt_file in expected_prompts:
            prompt_path = prompts_dir / prompt_file
            assert prompt_path.exists(), f"Prompt file not found: {prompt_file}"
            assert prompt_path.is_file(), f"Prompt path is not a file: {prompt_file}"
            
            # Verify file is readable and has content
            content = prompt_path.read_text(encoding="utf-8")
            assert len(content) > 0, f"Prompt file is empty: {prompt_file}"
        
        # Also verify the job-specific prompt is in the adjusters directory
        from cvextract.adjusters import openai_job_specific_adjuster
        adjuster_module_path = Path(openai_job_specific_adjuster.__file__).parent
        adjuster_prompts_dir = adjuster_module_path / "prompts"
        
        adjuster_expected_prompts = [
            "adjuster_promp_for_a_company.md",
            "adjuster_promp_for_specific_job.md",
        ]
        
        for prompt_file in adjuster_expected_prompts:
            prompt_path = adjuster_prompts_dir / prompt_file
            assert prompt_path.exists(), f"Adjuster prompt file not found: {prompt_file}"
            assert prompt_path.is_file(), f"Adjuster prompt path is not a file: {prompt_file}"
            
            # Verify file is readable and has content
            content = prompt_path.read_text(encoding="utf-8")
            assert len(content) > 0, f"Adjuster prompt file is empty: {prompt_file}"

    def test_all_prompts_loadable(self):
        """Test that all prompt files can be loaded via load_prompt function."""
        from cvextract.ml_adjustment.prompt_loader import load_prompt
        
        prompts_to_test = [
            "system_prompt",
            "website_analysis_prompt",
            "adjuster_promp_for_specific_job",
            "cv_extraction_system",
            "cv_extraction_user",
        ]
        
        for prompt_name in prompts_to_test:
            result = load_prompt(prompt_name)
            assert result is not None, f"Failed to load prompt: {prompt_name}"
            assert isinstance(result, str), f"Prompt is not a string: {prompt_name}"
            assert len(result) > 0, f"Prompt is empty: {prompt_name}"

    @pytest.mark.slow
    def test_prompts_in_built_distribution(self):
        """
        Test that prompts are included when building a distribution.
        
        This test builds a wheel package and verifies prompt files are included.
        Marked as slow since it involves building the package.
        """
        # Get project root
        project_root = Path(__file__).parent.parent
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Build wheel
            result = subprocess.run(
                [sys.executable, "-m", "pip", "wheel", str(project_root), "--no-deps", "-w", str(tmpdir_path)],
                capture_output=True,
                text=True,
            )
            
            # Check build succeeded
            if result.returncode != 0:
                pytest.skip(f"Package build failed: {result.stderr}")
            
            # Find the wheel file
            wheel_files = list(tmpdir_path.glob("*.whl"))
            assert len(wheel_files) > 0, "No wheel file created"
            
            wheel_file = wheel_files[0]
            
            # Extract wheel contents and check for prompt files
            # Wheels are just zip files
            import zipfile
            with zipfile.ZipFile(wheel_file) as zf:
                namelist = zf.namelist()
                
                # Check that prompt files are included
                expected_prompts = [
                    "cvextract/ml_adjustment/prompts/system_prompt.md",
                    "cvextract/ml_adjustment/prompts/website_analysis_prompt.md",
                    "cvextract/ml_adjustment/prompts/cv_extraction_system.md",
                    "cvextract/ml_adjustment/prompts/cv_extraction_user.md",
                    "cvextract/adjusters/prompts/adjuster_promp_for_a_company.md",
                    "cvextract/adjusters/prompts/adjuster_promp_for_specific_job.md",
                ]
                
                for expected_prompt in expected_prompts:
                    assert expected_prompt in namelist, f"Prompt not in wheel: {expected_prompt}"
