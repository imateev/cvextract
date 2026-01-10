"""Additional tests for CLI and pipeline edge cases."""

import zipfile
from pathlib import Path

import cvextract.cli as cli
import cvextract.pipeline as pipeline


class TestCliEdgeCases:
    """Tests for CLI edge cases not covered."""

    def test_main_no_matching_inputs(self, monkeypatch, tmp_path: Path):
        """Test main when no matching input files found."""
        template = tmp_path / "tpl.docx"
        with zipfile.ZipFile(template, "w") as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        # Create a file that won't match (.txt instead of .docx or .json)
        (src_dir / "file.txt").write_text("content")

        rc = cli.main(
            ["--extract", f"source={src_dir}", "--target", str(tmp_path / "out")]
        )

        assert rc == 1

    def test_main_source_not_found(self, tmp_path: Path):
        """Test main when source path does not exist."""
        template = tmp_path / "tpl.docx"
        with zipfile.ZipFile(template, "w") as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")

        rc = cli.main(
            [
                "--extract",
                f"source={tmp_path / 'nonexistent'}",
                "--target",
                str(tmp_path / "out"),
            ]
        )

        assert rc == 1

    def test_main_template_not_found(self, tmp_path: Path):
        """Test main when template file does not exist."""
        src = tmp_path / "src.docx"
        with zipfile.ZipFile(src, "w") as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")

        rc = cli.main(
            [
                "--extract",
                f"source={src}",
                "--render",
                f"template={tmp_path / 'nonexistent.docx'}",
                "--target",
                str(tmp_path / "out"),
            ]
        )

        assert rc == 1


class TestPipelineEdgeCases:
    """Tests for pipeline edge cases."""

    def test_infer_source_root_empty_list(self):
        """Test infer_source_root with empty list."""
        root = pipeline.infer_source_root([])
        assert root.is_absolute()

    def test_infer_source_root_single_file(self, tmp_path):
        """Test infer_source_root with a single file."""
        file_path = tmp_path / "data.json"
        file_path.touch()

        root = pipeline.infer_source_root([file_path])

        assert root == tmp_path.resolve()

    def test_infer_source_root_multiple_files(self, tmp_path):
        """Test infer_source_root with multiple files."""
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        dir_a.mkdir()
        dir_b.mkdir()
        file_a = dir_a / "one.json"
        file_b = dir_b / "two.json"
        file_a.touch()
        file_b.touch()

        root = pipeline.infer_source_root([file_a, file_b])

        assert root == tmp_path.resolve()

    def test_safe_relpath_exception_handling(self):
        """Test safe_relpath when relative_to raises exception."""
        # Create a path that will fail relative_to
        p = Path("/some/absolute/path")
        root = Path("/different/path")

        result = pipeline.safe_relpath(p, root)
        # Should fall back to just the name
        assert result == "path"
