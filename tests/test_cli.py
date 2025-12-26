"""Tests for CLI module."""

import pytest
from pathlib import Path
import cvextract.cli as cli


def test_parse_args_extract_mode():
    """Test parsing extract mode arguments."""
    args = cli.parse_args([
        "--mode", "extract",
        "--source", "/path/to/cvs",
        "--template", "/path/to/template.docx",
        "--target", "/path/to/output"
    ])
    assert args.mode == "extract"
    assert args.source == "/path/to/cvs"  # Returns string, not Path
    assert args.template == "/path/to/template.docx"
    assert args.target == "/path/to/output"
    assert args.strict is False
    assert args.debug is False


def test_parse_args_extract_apply_mode():
    """Test parsing extract-apply mode arguments."""
    args = cli.parse_args([
        "--mode", "extract-apply",
        "--source", "/path/to/cvs",
        "--template", "/path/to/template.docx",
        "--target", "/path/to/output"
    ])
    assert args.mode == "extract-apply"


def test_parse_args_apply_mode():
    """Test parsing apply mode arguments."""
    args = cli.parse_args([
        "--mode", "apply",
        "--source", "/path/to/json",
        "--template", "/path/to/template.docx",
        "--target", "/path/to/output"
    ])
    assert args.mode == "apply"


def test_parse_args_with_strict():
    """Test parsing with strict flag."""
    args = cli.parse_args([
        "--mode", "extract",
        "--source", "/path/to/cvs",
        "--template", "/path/to/template.docx",
        "--target", "/path/to/output",
        "--strict"
    ])
    assert args.strict is True


def test_parse_args_with_debug():
    """Test parsing with debug flag."""
    args = cli.parse_args([
        "--mode", "extract",
        "--source", "/path/to/cvs",
        "--template", "/path/to/template.docx",
        "--target", "/path/to/output",
        "--debug"
    ])
    assert args.debug is True


def test_parse_args_with_log_file():
    """Test parsing with log file."""
    args = cli.parse_args([
        "--mode", "extract",
        "--source", "/path/to/cvs",
        "--template", "/path/to/template.docx",
        "--target", "/path/to/output",
        "--log-file", "/path/to/log.txt"
    ])
    assert args.log_file == "/path/to/log.txt"  # Returns string, not Path


def test_collect_inputs_extract_mode_single_file(tmp_path: Path):
    """Test collecting inputs for extract mode with single file."""
    docx = tmp_path / "test.docx"
    docx.write_text("x")
    template = tmp_path / "template.docx"
    
    inputs = cli.collect_inputs(docx, mode="extract", template_path=template)
    assert len(inputs) == 1
    assert inputs[0] == docx


def test_collect_inputs_extract_mode_directory(tmp_path: Path):
    """Test collecting inputs for extract mode with directory."""
    (tmp_path / "a.docx").write_text("x")
    (tmp_path / "b.docx").write_text("y")
    template = tmp_path / "template.docx"
    template.write_text("t")
    
    inputs = cli.collect_inputs(tmp_path, mode="extract", template_path=template)
    assert len(inputs) == 2
    assert template not in inputs  # Template should be excluded


def test_collect_inputs_apply_mode_json_files(tmp_path: Path):
    """Test collecting inputs for apply mode with JSON files."""
    (tmp_path / "a.json").write_text("{}")
    (tmp_path / "b.json").write_text("{}")
    template = tmp_path / "template.docx"
    
    inputs = cli.collect_inputs(tmp_path, mode="apply", template_path=template)
    assert len(inputs) == 2


def test_collect_inputs_nested_directories(tmp_path: Path):
    """Test collecting inputs from nested directories."""
    sub1 = tmp_path / "sub1"
    sub2 = tmp_path / "sub2"
    sub1.mkdir()
    sub2.mkdir()
    
    (sub1 / "a.docx").write_text("x")
    (sub2 / "b.docx").write_text("y")
    template = tmp_path / "template.docx"
    template.write_text("t")
    
    inputs = cli.collect_inputs(tmp_path, mode="extract", template_path=template)
    assert len(inputs) == 2


def test_main_extract_mode(monkeypatch, tmp_path: Path):
    """Test main function with extract mode."""
    import zipfile
    
    docx = tmp_path / "test.docx"
    # Create minimal valid DOCX (it's just a ZIP file)
    with zipfile.ZipFile(docx, 'w') as zf:
        zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")
    
    template = tmp_path / "template.docx"
    with zipfile.ZipFile(template, 'w') as zf:
        zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")
    
    target = tmp_path / "output"
    
    call_count = {"count": 0}
    
    def fake_run_extract(inputs, target_dir, strict, debug):
        call_count["count"] += 1
        return 0
    
    # Patch in cli module namespace, not pipeline
    monkeypatch.setattr(cli, "run_extract_mode", fake_run_extract)
    
    rc = cli.main([
        "--mode", "extract",
        "--source", str(docx),
        "--template", str(template),
        "--target", str(target)
    ])
    assert rc == 0
    assert call_count["count"] == 1


def test_main_extract_apply_mode(monkeypatch, tmp_path: Path):
    """Test main function with extract-apply mode."""
    import zipfile
    
    docx = tmp_path / "test.docx"
    with zipfile.ZipFile(docx, 'w') as zf:
        zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")
    
    template = tmp_path / "template.docx"
    with zipfile.ZipFile(template, 'w') as zf:
        zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")
    
    target = tmp_path / "output"
    
    call_count = {"count": 0}
    
    def fake_run_extract_apply(inputs, template_path, target_dir, strict, debug):
        call_count["count"] += 1
        return 0
    
    # Patch in cli module namespace
    monkeypatch.setattr(cli, "run_extract_apply_mode", fake_run_extract_apply)
    
    rc = cli.main([
        "--mode", "extract-apply",
        "--source", str(docx),
        "--template", str(template),
        "--target", str(target)
    ])
    assert rc == 0
    assert call_count["count"] == 1


def test_main_apply_mode(monkeypatch, tmp_path: Path, caplog):
    """Test main function with apply mode."""
    import zipfile
    import logging
    
    json_file = tmp_path / "test.json"
    json_file.write_text("{}")
    
    template = tmp_path / "template.docx"
    with zipfile.ZipFile(template, 'w') as zf:
        zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")
    
    target = tmp_path / "output"
    
    call_count = {"count": 0}
    
    def fake_run_apply(inputs, template_path, target_dir, debug):
        call_count["count"] += 1
        return 0
    
    # Patch in cli module namespace
    monkeypatch.setattr(cli, "run_apply_mode", fake_run_apply)
    
    with caplog.at_level(logging.DEBUG):
        rc = cli.main([
            "--mode", "apply",
            "--source", str(json_file),
            "--template", str(template),
            "--target", str(target)
        ])
    
    if rc != 0:
        print(f"Return code: {rc}")
        print(f"Logs: {caplog.text}")
    
    assert rc == 0
    assert call_count["count"] == 1


def test_main_creates_log_directory(monkeypatch, tmp_path: Path):
    """Test that main creates parent directory for log file."""
    import zipfile
    
    docx = tmp_path / "test.docx"
    with zipfile.ZipFile(docx, 'w') as zf:
        zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")
    
    template = tmp_path / "template.docx"
    with zipfile.ZipFile(template, 'w') as zf:
        zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")
    
    target = tmp_path / "output"
    log_file = tmp_path / "logs" / "run.log"
    
    def fake_run_extract(inputs, target_dir, strict, debug):
        return 0
    
    # Patch in cli module namespace
    monkeypatch.setattr(cli, "run_extract_mode", fake_run_extract)
    
    cli.main([
        "--mode", "extract",
        "--source", str(docx),
        "--template", str(template),
        "--target", str(target),
        "--log-file", str(log_file)
    ])
    
    assert log_file.parent.exists()
