"""Tests for cli_execute_extract verification behavior."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from cvextract.cli_config import ExtractStage, UserConfig
from cvextract.cli_execute_extract import execute
from cvextract.shared import StepName, UnitOfWork


def _write_output(work: UnitOfWork, payload: dict) -> UnitOfWork:
    work.ensure_step_status(StepName.Extract)
    work.output.write_text(json.dumps(payload), encoding="utf-8")
    return work


def test_execute_verifies_extracted_output(tmp_path: Path):
    """execute should verify extracted output after extraction."""
    source = tmp_path / "input.docx"
    source.touch()

    config = UserConfig(target_dir=tmp_path, extract=ExtractStage(source=source))
    work = UnitOfWork(config=config, input=source, output=None)

    verifier = MagicMock()
    verifier.verify.side_effect = (
        lambda w: w.add_error(StepName.Extract, "bad data")
        or w.add_warning(StepName.Extract, "warn data")
        or w
    )

    with patch(
        "cvextract.cli_execute_extract.extract_single",
        side_effect=lambda w: _write_output(w, {"identity": {}}),
    ), patch(
        "cvextract.cli_execute_extract.get_verifier",
        return_value=verifier,
    ):
        result = execute(work)

    extract_status = result.step_statuses[StepName.Extract]
    assert "bad data" in extract_status.errors
    assert "warn data" in extract_status.warnings
    verifier.verify.assert_called_once()


def test_execute_skips_verification_when_global_skip_all_verify(tmp_path: Path):
    """execute should skip verification when skip_all_verify is set."""
    source = tmp_path / "input.docx"
    source.touch()

    config = UserConfig(
        target_dir=tmp_path,
        extract=ExtractStage(source=source),
        skip_all_verify=True,
    )
    work = UnitOfWork(config=config, input=source, output=None)

    def fail_if_called(_name):
        raise AssertionError("verifier should not be called")

    with patch(
        "cvextract.cli_execute_extract.extract_single",
        side_effect=lambda w: _write_output(w, {"identity": {}}),
    ), patch(
        "cvextract.cli_execute_extract.get_verifier",
        side_effect=fail_if_called,
    ):
        result = execute(work)

    extract_status = result.step_statuses[StepName.Extract]
    assert extract_status.errors == []
    assert extract_status.warnings == []


def test_execute_unknown_verifier_adds_error(tmp_path: Path):
    """execute should add an error for unknown verifiers."""
    source = tmp_path / "input.docx"
    source.touch()

    config = UserConfig(
        target_dir=tmp_path,
        extract=ExtractStage(source=source, verifier="unknown-verifier"),
    )
    work = UnitOfWork(config=config, input=source, output=None)

    with patch(
        "cvextract.cli_execute_extract.extract_single",
        side_effect=lambda w: _write_output(w, {"identity": {}}),
    ), patch(
        "cvextract.cli_execute_extract.get_verifier",
        return_value=None,
    ):
        result = execute(work)

    extract_status = result.step_statuses[StepName.Extract]
    assert any("unknown verifier" in e for e in extract_status.errors)


def test_execute_returns_work_when_extract_missing(tmp_path: Path):
    """execute should return unchanged work when extract stage is missing."""
    source = tmp_path / "input.docx"
    source.touch()

    config = UserConfig(target_dir=tmp_path)
    work = UnitOfWork(config=config, input=source, output=None)

    result = execute(work)

    assert result is work


def test_execute_reports_missing_output_for_verification(tmp_path: Path):
    """execute should add an error when output JSON is missing for verification."""
    source = tmp_path / "input.docx"
    source.touch()

    config = UserConfig(target_dir=tmp_path, extract=ExtractStage(source=source))
    work = UnitOfWork(config=config, input=source, output=None)

    with patch(
        "cvextract.cli_execute_extract.extract_single",
        side_effect=lambda w: w,
    ):
        result = execute(work)

    extract_status = result.step_statuses[StepName.Extract]
    assert any("output JSON not found for verification" in e for e in extract_status.errors)


def test_execute_handles_verifier_exception(tmp_path: Path):
    """execute should surface verifier exceptions as errors."""
    source = tmp_path / "input.docx"
    source.touch()

    config = UserConfig(target_dir=tmp_path, extract=ExtractStage(source=source))
    work = UnitOfWork(config=config, input=source, output=None)

    verifier = MagicMock()
    verifier.verify.side_effect = ValueError("boom")

    with patch(
        "cvextract.cli_execute_extract.extract_single",
        side_effect=lambda w: _write_output(w, {"identity": {}}),
    ), patch(
        "cvextract.cli_execute_extract.get_verifier",
        return_value=verifier,
    ):
        result = execute(work)

    extract_status = result.step_statuses[StepName.Extract]
    assert any("verify failed" in e for e in extract_status.errors)
