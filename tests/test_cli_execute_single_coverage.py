"""Coverage tests for cli_execute_single."""

from unittest.mock import patch

from cvextract.cli_config import (
    AdjusterConfig,
    AdjustStage,
    ExtractStage,
    RenderStage,
    UserConfig,
)
from cvextract.cli_execute_single import execute_single
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
        "cvextract.cli_execute_single.execute_adjust", return_value=adjusted
    ), patch(
        "cvextract.cli_execute_single.execute_render"
    ) as mock_render:
        rc, work = execute_single(config)

    mock_render.assert_not_called()
    assert rc == 1
    assert work is adjusted
