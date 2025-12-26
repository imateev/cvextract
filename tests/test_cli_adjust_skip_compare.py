import zipfile
import os
from pathlib import Path
import cvextract.cli as cli


def test_cli_sets_skip_compare_extract_apply(monkeypatch, tmp_path: Path):
    docx = tmp_path / "test.docx"
    with zipfile.ZipFile(docx, 'w') as zf:
        zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")

    template = tmp_path / "template.docx"
    with zipfile.ZipFile(template, 'w') as zf:
        zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")

    target = tmp_path / "output"

    def fake_run_extract_apply(inputs, template_path, target_dir, strict, debug):
        # Assert environment variables set by CLI when adjust is requested
        assert os.environ.get("CVEXTRACT_SKIP_COMPARE") == "1"
        assert os.environ.get("CVEXTRACT_ADJUST_URL") == "https://example.com/customer"
        assert os.environ.get("OPENAI_MODEL") == "gpt-4o-mini"
        # Clean up env to avoid leaking into other tests
        os.environ.pop("CVEXTRACT_SKIP_COMPARE", None)
        os.environ.pop("CVEXTRACT_ADJUST_URL", None)
        os.environ.pop("OPENAI_MODEL", None)
        return 0

    monkeypatch.setattr(cli, "run_extract_apply_mode", fake_run_extract_apply)

    rc = cli.main([
        "--mode", "extract-apply",
        "--source", str(docx),
        "--template", str(template),
        "--target", str(target),
        "--adjust-for-customer", "https://example.com/customer",
        "--openai-model", "gpt-4o-mini",
    ])
    assert rc == 0


def test_cli_sets_skip_compare_apply(monkeypatch, tmp_path: Path):
    json_file = tmp_path / "data.json"
    json_file.write_text("{}", encoding="utf-8")

    template = tmp_path / "template.docx"
    with zipfile.ZipFile(template, 'w') as zf:
        zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")

    target = tmp_path / "output"

    def fake_run_apply(inputs, template_path, target_dir, debug):
        assert os.environ.get("CVEXTRACT_SKIP_COMPARE") == "1"
        assert os.environ.get("CVEXTRACT_ADJUST_URL") == "https://example.com/customer"
        assert os.environ.get("OPENAI_MODEL") == "gpt-4o-mini"
        os.environ.pop("CVEXTRACT_SKIP_COMPARE", None)
        os.environ.pop("CVEXTRACT_ADJUST_URL", None)
        os.environ.pop("OPENAI_MODEL", None)
        return 0

    monkeypatch.setattr(cli, "run_apply_mode", fake_run_apply)

    rc = cli.main([
        "--mode", "apply",
        "--source", str(json_file),
        "--template", str(template),
        "--target", str(target),
        "--adjust-for-customer", "https://example.com/customer",
        "--openai-model", "gpt-4o-mini",
    ])
    assert rc == 0
