import pytest

from pathlib import Path
import cvextract.pipeline as p

def test_infer_source_root_single_file(tmp_path: Path):
    f = tmp_path / "a.docx"
    f.write_text("x")
    assert p.infer_source_root([f]) == tmp_path

def test_infer_source_root_multiple_files_common_parent(tmp_path: Path):
    d1 = tmp_path / "x"
    d2 = tmp_path / "y"
    d1.mkdir()
    d2.mkdir()
    f1 = d1 / "a.docx"
    f2 = d2 / "b.docx"
    f1.write_text("x")
    f2.write_text("y")

    root = p.infer_source_root([f1, f2])
    assert root == tmp_path

