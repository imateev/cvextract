"""Coverage tests for cli_execute_single."""

from unittest.mock import patch

from cvextract.cli_config import (
    AdjusterConfig,
    AdjustStage,
    ExtractStage,
    RenderStage,
    UserConfig,
)
from cvextract.cli_execute_single import (
    adjust_verify,
    execute_single,
    extract_verify,
    roundtrip_verify,
)
from cvextract.shared import StepName, StepStatus, UnitOfWork


def test_execute_single_skips_render_when_adjust_fails(tmp_path):
    """execute_single should skip render when adjust has errors."""
    source = tmp_path / "input.docx"
    source.touch()
    template = tmp_path / "template.docx"
    template.touch()

    config = UserConfig(
        target_dir=tmp_path,
        extract=ExtractStage(source=source),
        adjust=AdjustStage(
            data=None,
            adjusters=[AdjusterConfig(name="noop", params={})],
        ),
        render=RenderStage(template=template),
    )

    extracted = UnitOfWork(config=config, initial_input=source)
    extracted.set_step_paths(
        StepName.Extract, input_path=source, output_path=tmp_path / "out.json"
    )
    extracted.step_states[StepName.Extract] = StepStatus(step=StepName.Extract)

    adjusted = UnitOfWork(config=config, initial_input=source)
    adjusted_output = extracted.get_step_output(StepName.Extract)
    adjusted.set_step_paths(
        StepName.Adjust, input_path=adjusted_output, output_path=adjusted_output
    )
    adjusted.step_states[StepName.Adjust] = StepStatus(
        step=StepName.Adjust, errors=["adjust failed"]
    )

    with patch(
        "cvextract.cli_execute_single.execute_extract", return_value=extracted
    ), patch(
        "cvextract.cli_execute_single.extract_verify", side_effect=lambda w: w
    ), patch(
        "cvextract.cli_execute_single.execute_adjust", return_value=adjusted
    ), patch(
        "cvextract.cli_execute_single.execute_render"
    ) as mock_render:
        rc, work = execute_single(config)

    mock_render.assert_not_called()
    assert rc == 1
    assert work is adjusted


def test_execute_single_returns_error_when_no_source(tmp_path):
    """execute_single should fail fast when no input source is provided."""
    config = UserConfig(target_dir=tmp_path)
    rc, work = execute_single(config)
    assert rc == 1
    assert work is None


def test_execute_single_stops_on_unknown_extractor(tmp_path):
    """execute_single should stop when extractor is unavailable."""
    source = tmp_path / "input.docx"
    source.touch()
    template = tmp_path / "template.docx"
    template.touch()

    config = UserConfig(
        target_dir=tmp_path,
        extract=ExtractStage(source=source),
        render=RenderStage(template=template),
    )

    extracted = UnitOfWork(config=config, initial_input=source)
    extracted.set_step_paths(
        StepName.Extract, input_path=source, output_path=tmp_path / "out.json"
    )
    extracted.step_states[StepName.Extract] = StepStatus(
        step=StepName.Extract,
        ConfiguredExecutorAvailable=False,
    )

    with patch(
        "cvextract.cli_execute_single.execute_extract", return_value=extracted
    ), patch(
        "cvextract.cli_execute_single.extract_verify"
    ) as mock_verify, patch(
        "cvextract.cli_execute_single.execute_render"
    ) as mock_render:
        rc, work = execute_single(config)

    assert rc == 1
    assert work is extracted
    mock_verify.assert_not_called()
    mock_render.assert_not_called()


def test_execute_single_calls_extract_verify_on_success(tmp_path):
    """execute_single should invoke extract_verify after a successful extract."""
    source = tmp_path / "input.docx"
    source.touch()
    output_path = tmp_path / "out.json"
    output_path.write_text("{}", encoding="utf-8")

    config = UserConfig(target_dir=tmp_path, extract=ExtractStage(source=source))

    extracted = UnitOfWork(config=config, initial_input=source)
    extracted.set_step_paths(
        StepName.Extract, input_path=source, output_path=output_path
    )
    extracted.step_states[StepName.Extract] = StepStatus(step=StepName.Extract)

    with patch(
        "cvextract.cli_execute_single.execute_extract", return_value=extracted
    ), patch(
        "cvextract.cli_execute_single.extract_verify",
        side_effect=lambda w: w.add_error(StepName.Extract, "bad") or w,
    ) as mock_verify:
        rc, work = execute_single(config)

    assert rc == 1
    assert work is extracted
    mock_verify.assert_called_once()


def test_extract_verify_handles_unknown_verifier(tmp_path):
    """extract_verify should record an error for unknown verifiers."""
    source = tmp_path / "input.docx"
    source.touch()
    output_path = tmp_path / "out.json"
    output_path.write_text("{}", encoding="utf-8")

    config = UserConfig(
        target_dir=tmp_path,
        extract=ExtractStage(source=source, verifier="missing-verifier"),
    )
    work = UnitOfWork(config=config, initial_input=source)
    work.set_step_paths(
        StepName.Extract, input_path=source, output_path=output_path
    )

    with patch(
        "cvextract.cli_execute_single.get_verifier", return_value=None
    ):
        result = extract_verify(work)

    extract_status = result.step_states[StepName.Extract]
    assert any("unknown verifier" in e for e in extract_status.errors)


def test_extract_verify_records_verifier_exception(tmp_path):
    """extract_verify should record verifier failures as errors."""
    source = tmp_path / "input.docx"
    source.touch()
    output_path = tmp_path / "out.json"
    output_path.write_text("{}", encoding="utf-8")

    config = UserConfig(target_dir=tmp_path, extract=ExtractStage(source=source))
    work = UnitOfWork(config=config, initial_input=source)
    work.set_step_paths(
        StepName.Extract, input_path=source, output_path=output_path
    )

    verifier = patch(
        "cvextract.cli_execute_single.get_verifier",
        return_value=type(
            "Verifier",
            (),
            {"verify": staticmethod(lambda _w: (_ for _ in ()).throw(ValueError("boom")))},
        )(),
    )

    with verifier:
        result = extract_verify(work)

    extract_status = result.step_states[StepName.Extract]
    assert any("verify failed" in e for e in extract_status.errors)


def test_execute_single_calls_adjust_verify_on_success(tmp_path):
    """execute_single should invoke adjust_verify after a successful adjust."""
    source = tmp_path / "input.docx"
    source.touch()
    output_path = tmp_path / "adjusted.json"
    output_path.write_text("{}", encoding="utf-8")

    config = UserConfig(
        target_dir=tmp_path,
        extract=ExtractStage(source=source),
        adjust=AdjustStage(adjusters=[AdjusterConfig(name="noop", params={})]),
    )

    extracted = UnitOfWork(config=config, initial_input=source)
    extracted.set_step_paths(
        StepName.Extract, input_path=source, output_path=tmp_path / "out.json"
    )
    extracted.step_states[StepName.Extract] = StepStatus(step=StepName.Extract)

    adjusted = UnitOfWork(config=config, initial_input=source)
    adjusted.set_step_paths(
        StepName.Adjust, input_path=tmp_path / "out.json", output_path=output_path
    )
    adjusted.step_states[StepName.Adjust] = StepStatus(step=StepName.Adjust)

    with patch(
        "cvextract.cli_execute_single.execute_extract", return_value=extracted
    ), patch(
        "cvextract.cli_execute_single.extract_verify", side_effect=lambda w: w
    ), patch(
        "cvextract.cli_execute_single.execute_adjust", return_value=adjusted
    ), patch(
        "cvextract.cli_execute_single.adjust_verify",
        side_effect=lambda w: w.add_error(StepName.Adjust, "bad") or w,
    ) as mock_verify:
        rc, work = execute_single(config)

    assert rc == 1
    assert work is adjusted
    mock_verify.assert_called_once()


def test_adjust_verify_handles_unknown_verifier(tmp_path):
    """adjust_verify should record an error for unknown verifiers."""
    json_file = tmp_path / "adjusted.json"
    json_file.write_text("{}", encoding="utf-8")

    config = UserConfig(
        target_dir=tmp_path,
        adjust=AdjustStage(
            adjusters=[AdjusterConfig(name="noop", params={})],
            verifier="missing-verifier",
        ),
    )
    work = UnitOfWork(config=config, initial_input=json_file)
    work.set_step_paths(
        StepName.Adjust, input_path=json_file, output_path=json_file
    )

    with patch("cvextract.cli_execute_single.get_verifier", return_value=None):
        result = adjust_verify(work)

    adjust_status = result.step_states[StepName.Adjust]
    assert any("unknown verifier" in e for e in adjust_status.errors)


def test_adjust_verify_records_verifier_exception(tmp_path):
    """adjust_verify should record verifier failures as errors."""
    json_file = tmp_path / "adjusted.json"
    json_file.write_text("{}", encoding="utf-8")

    config = UserConfig(
        target_dir=tmp_path,
        adjust=AdjustStage(adjusters=[AdjusterConfig(name="noop", params={})]),
    )
    work = UnitOfWork(config=config, initial_input=json_file)
    work.set_step_paths(
        StepName.Adjust, input_path=json_file, output_path=json_file
    )

    verifier = patch(
        "cvextract.cli_execute_single.get_verifier",
        return_value=type(
            "Verifier",
            (),
            {"verify": staticmethod(lambda _w: (_ for _ in ()).throw(ValueError("boom")))},
        )(),
    )

    with verifier:
        result = adjust_verify(work)

    adjust_status = result.step_states[StepName.Adjust]
    assert any("verify failed" in e for e in adjust_status.errors)


def test_roundtrip_verify_skips_without_render_status(tmp_path):
    """roundtrip_verify should no-op when render status is missing."""
    config = UserConfig(target_dir=tmp_path)
    work = UnitOfWork(config=config)

    result = roundtrip_verify(work)

    assert result is work
    assert StepName.RoundtripComparer not in result.step_states


def test_roundtrip_verify_adds_error_when_extract_missing(tmp_path):
    """roundtrip_verify should report missing extract output."""
    source = tmp_path / "input.docx"
    source.touch()
    render_output = tmp_path / "rendered.docx"
    render_output.touch()

    config = UserConfig(target_dir=tmp_path)
    work = UnitOfWork(config=config, initial_input=source)
    work.set_step_paths(
        StepName.Render, input_path=tmp_path / "input.json", output_path=render_output
    )
    work.set_step_paths(
        StepName.Extract,
        input_path=source,
        output_path=tmp_path / "missing.json",
    )

    result = roundtrip_verify(work)

    errors = result.step_states[StepName.RoundtripComparer].errors
    assert any("extract output unavailable" in e for e in errors)


def test_roundtrip_verify_records_extract_failure(tmp_path):
    """roundtrip_verify should record errors when extract_cv_data fails."""
    source = tmp_path / "input.docx"
    source.touch()
    render_output = tmp_path / "rendered.docx"
    render_output.touch()
    extract_output = tmp_path / "original.json"
    extract_output.write_text("{}", encoding="utf-8")

    config = UserConfig(target_dir=tmp_path)
    work = UnitOfWork(config=config, initial_input=source)
    work.set_step_paths(
        StepName.Render, input_path=tmp_path / "input.json", output_path=render_output
    )
    work.set_step_paths(
        StepName.Extract, input_path=source, output_path=extract_output
    )

    with patch(
        "cvextract.cli_execute_single.extract_cv_data",
        side_effect=RuntimeError("boom"),
    ):
        result = roundtrip_verify(work)

    errors = result.step_states[StepName.RoundtripComparer].errors
    assert any("extract failed" in e for e in errors)


def test_roundtrip_verify_sets_comparer_input(tmp_path):
    """roundtrip_verify should set comparer input to the roundtrip JSON."""
    source = tmp_path / "input.docx"
    source.touch()
    render_output = tmp_path / "rendered.docx"
    render_output.touch()
    extract_output = tmp_path / "original.json"
    extract_output.write_text("{}", encoding="utf-8")

    config = UserConfig(target_dir=tmp_path)
    work = UnitOfWork(config=config, initial_input=source)
    work.set_step_paths(
        StepName.Render, input_path=tmp_path / "input.json", output_path=render_output
    )
    work.set_step_paths(
        StepName.Extract, input_path=source, output_path=extract_output
    )

    expected_roundtrip = config.workspace.verification_dir / "rendered.json"

    def _fake_extract(roundtrip_work: UnitOfWork) -> UnitOfWork:
        output_path = roundtrip_work.get_step_output(StepName.Extract)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("{}", encoding="utf-8")
        return roundtrip_work

    class DummyVerifier:
        def __init__(self) -> None:
            self.called = False

        def verify(self, verify_work: UnitOfWork) -> UnitOfWork:
            self.called = True
            return verify_work

    dummy = DummyVerifier()

    with patch(
        "cvextract.cli_execute_single.extract_cv_data", side_effect=_fake_extract
    ), patch("cvextract.cli_execute_single.get_verifier", return_value=dummy):
        result = roundtrip_verify(work)

    comparer_status = result.step_states[StepName.RoundtripComparer]
    assert comparer_status.input == expected_roundtrip
    assert dummy.called
