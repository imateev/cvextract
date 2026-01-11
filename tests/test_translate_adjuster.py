"""Tests for the OpenAI translate adjuster."""

import json
from pathlib import Path
from unittest.mock import MagicMock

from cvextract.adjusters.openai_translate_adjuster import OpenAITranslateAdjuster
from cvextract.cli_config import ExtractStage, UserConfig
from cvextract.shared import StepName, UnitOfWork


def _load_fixture(name: str) -> dict:
    fixture_path = Path(__file__).parent / "fixtures" / name
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def _make_work(tmp_path: Path, cv_data: dict) -> UnitOfWork:
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "output.json"
    input_path.write_text(json.dumps(cv_data, indent=2), encoding="utf-8")
    work = UnitOfWork(
        config=UserConfig(target_dir=tmp_path, extract=ExtractStage(source=input_path)),
        initial_input=input_path,
    )
    work.set_step_paths(StepName.Adjust, input_path=input_path, output_path=output_path)
    return work


def _mock_openai(monkeypatch, response_content: str) -> MagicMock:
    import cvextract.adjusters.openai_translate_adjuster as translate_module

    mock_completion = MagicMock()
    mock_completion.choices = [
        MagicMock(message=MagicMock(content=response_content), finish_reason="stop")
    ]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion

    mock_openai = MagicMock(return_value=mock_client)
    monkeypatch.setattr(translate_module, "OpenAI", mock_openai)
    return mock_client


def test_translate_adjuster_golden_fixture(tmp_path: Path, monkeypatch):
    cv_data = _load_fixture("translate_input.json")
    expected = _load_fixture("translate_expected_de.json")

    mock_client = _mock_openai(monkeypatch, json.dumps(expected, ensure_ascii=False))

    adjuster = OpenAITranslateAdjuster(api_key="test-key")
    work = _make_work(tmp_path, cv_data)
    result = adjuster.adjust(work, language="de")

    output_path = result.get_step_output(StepName.Adjust)
    assert output_path is not None
    output = json.loads(output_path.read_text(encoding="utf-8"))
    assert output == expected

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["temperature"] == 0.0


def test_translate_adjuster_schema_failure_returns_original(
    tmp_path: Path, monkeypatch
):
    cv_data = _load_fixture("translate_input.json")
    bad_output = {"overview": "Oops", "experiences": []}
    _mock_openai(monkeypatch, json.dumps(bad_output, ensure_ascii=False))

    adjuster = OpenAITranslateAdjuster(api_key="test-key")
    work = _make_work(tmp_path, cv_data)
    result = adjuster.adjust(work, language="de")

    output_path = result.get_step_output(StepName.Adjust)
    assert output_path is not None
    output = json.loads(output_path.read_text(encoding="utf-8"))
    assert output == cv_data
