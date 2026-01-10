"""Tests for CLI extractor name parameter parsing."""

import pytest

from cvextract.cli_gather import gather_user_requirements


class TestCLIExtractorNameParsing:
    """Tests for extractor name parameter in CLI."""

    def test_extract_without_name_uses_default(self, tmp_path):
        """--extract without name= uses default extractor."""
        target = tmp_path / "output"
        source = tmp_path / "cv.docx"
        source.touch()

        config = gather_user_requirements(
            ["--extract", f"source={source}", "--target", str(target)]
        )

        assert config.extract is not None
        assert config.extract.name == "default-docx-cv-extractor"

    def test_extract_with_private_internal_name(self, tmp_path):
        """--extract with name=default-docx-cv-extractor."""
        target = tmp_path / "output"
        source = tmp_path / "cv.docx"
        source.touch()

        config = gather_user_requirements(
            [
                "--extract",
                f"source={source}",
                "name=default-docx-cv-extractor",
                "--target",
                str(target),
            ]
        )

        assert config.extract is not None
        assert config.extract.name == "default-docx-cv-extractor"

    def test_extract_with_openai_name(self, tmp_path):
        """--extract with name=openai-extractor."""
        target = tmp_path / "output"
        source = tmp_path / "cv.pdf"
        source.touch()

        config = gather_user_requirements(
            [
                "--extract",
                f"source={source}",
                "name=openai-extractor",
                "--target",
                str(target),
            ]
        )

        assert config.extract is not None
        assert config.extract.name == "openai-extractor"

    def test_extract_with_name_and_output(self, tmp_path):
        """--extract with both name= and output= parameters."""
        target = tmp_path / "output"
        source = tmp_path / "cv.txt"
        source.touch()

        config = gather_user_requirements(
            [
                "--extract",
                f"source={source}",
                "name=openai-extractor",
                "output=custom.json",
                "--target",
                str(target),
            ]
        )

        assert config.extract is not None
        assert config.extract.name == "openai-extractor"
        assert config.extract.output == target / "custom.json"

    def test_list_extractors_flag(self):
        """--list extractors shows available extractors."""
        # This should exit with 0, but we test it doesn't raise an error
        with pytest.raises(SystemExit) as exc_info:
            gather_user_requirements(["--list", "extractors"])

        assert exc_info.value.code == 0

    def test_extract_name_in_parallel_mode(self, tmp_path):
        """--extract name= works in parallel mode."""
        target = tmp_path / "output"
        source_dir = tmp_path / "cvs"
        source_dir.mkdir()

        config = gather_user_requirements(
            [
                "--parallel",
                f"source={source_dir}",
                "n=5",
                "--extract",
                "name=openai-extractor",
                "--target",
                str(target),
            ]
        )

        assert config.extract is not None
        assert config.extract.name == "openai-extractor"
        assert config.parallel is not None
        assert config.parallel.n == 5
