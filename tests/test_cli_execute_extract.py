"""Tests for cli_execute_extract behavior."""

import json
from pathlib import Path
from unittest.mock import patch

from cvextract.cli_config import ExtractStage, UserConfig
from cvextract.cli_execute_extract import execute
from cvextract.shared import StepName, UnitOfWork


def _write_output(work: UnitOfWork, payload: dict) -> UnitOfWork:
    work.ensure_step_status(StepName.Extract)
    output_path = work.get_step_output(StepName.Extract)
    output_path.write_text(json.dumps(payload), encoding="utf-8")
    return work


def test_execute_runs_extract_without_verification(tmp_path: Path):
    """execute should run extract and skip verification here."""
    source = tmp_path / "input.docx"
    source.touch()

    config = UserConfig(target_dir=tmp_path, extract=ExtractStage(source=source))
    work = UnitOfWork(config=config, initial_input=source)
    work.set_step_paths(StepName.Extract, input_path=source)

    with patch(
        "cvextract.cli_execute_extract.extract_single",
        side_effect=lambda w: _write_output(w, {"identity": {}}),
    ):
        result = execute(work)

    extract_status = result.step_states[StepName.Extract]
    assert extract_status.errors == []
    assert extract_status.warnings == []


def test_execute_ignores_skip_all_verify_flag(tmp_path: Path):
    """execute should ignore skip_all_verify here; verification happens later."""
    source = tmp_path / "input.docx"
    source.touch()

    config = UserConfig(
        target_dir=tmp_path,
        extract=ExtractStage(source=source),
        skip_all_verify=True,
    )
    work = UnitOfWork(config=config, initial_input=source)
    work.set_step_paths(StepName.Extract, input_path=source)

    with patch(
        "cvextract.cli_execute_extract.extract_single",
        side_effect=lambda w: _write_output(w, {"identity": {}}),
    ):
        result = execute(work)

    extract_status = result.step_states[StepName.Extract]
    assert extract_status.errors == []
    assert extract_status.warnings == []


def test_execute_ignores_verifier_config(tmp_path: Path):
    """execute should ignore verifier config; verification happens later."""
    source = tmp_path / "input.docx"
    source.touch()

    config = UserConfig(
        target_dir=tmp_path,
        extract=ExtractStage(source=source, verifier="unknown-verifier"),
    )
    work = UnitOfWork(config=config, initial_input=source)
    work.set_step_paths(StepName.Extract, input_path=source)

    with patch(
        "cvextract.cli_execute_extract.extract_single",
        side_effect=lambda w: _write_output(w, {"identity": {}}),
    ):
        result = execute(work)

    extract_status = result.step_states[StepName.Extract]
    assert extract_status.errors == []


def test_execute_returns_work_when_extract_missing(tmp_path: Path):
    """execute should return unchanged work when extract stage is missing."""
    source = tmp_path / "input.docx"
    source.touch()

    config = UserConfig(target_dir=tmp_path)
    work = UnitOfWork(config=config, initial_input=source)
    work.set_step_paths(StepName.Extract, input_path=source)

    result = execute(work)

    assert result is work


def test_execute_does_not_require_output_for_verification(tmp_path: Path):
    """execute should not verify output here; missing output should not error."""
    source = tmp_path / "input.docx"
    source.touch()

    config = UserConfig(target_dir=tmp_path, extract=ExtractStage(source=source))
    work = UnitOfWork(config=config, initial_input=source)
    work.set_step_paths(StepName.Extract, input_path=source)

    with patch(
        "cvextract.cli_execute_extract.extract_single",
        side_effect=lambda w: w,
    ):
        result = execute(work)

    extract_status = result.step_states[StepName.Extract]
    assert extract_status.errors == []


def test_execute_does_not_handle_verifier_exception(tmp_path: Path):
    """execute does not verify, so verifier exceptions are not raised here."""
    source = tmp_path / "input.docx"
    source.touch()

    config = UserConfig(target_dir=tmp_path, extract=ExtractStage(source=source))
    work = UnitOfWork(config=config, initial_input=source)
    work.set_step_paths(StepName.Extract, input_path=source)

    with patch(
        "cvextract.cli_execute_extract.extract_single",
        side_effect=lambda w: _write_output(w, {"identity": {}}),
    ):
        result = execute(work)

    extract_status = result.step_states[StepName.Extract]
    assert extract_status.errors == []
