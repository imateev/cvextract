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


def _mock_openai_with_completion(monkeypatch, completion: object) -> MagicMock:
    import cvextract.adjusters.openai_translate_adjuster as translate_module

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = completion

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


def test_translate_adjuster_invalid_temperature_uses_default(
    tmp_path: Path, monkeypatch
):
    cv_data = _load_fixture("translate_input.json")
    expected = _load_fixture("translate_expected_de.json")

    mock_client = _mock_openai(monkeypatch, json.dumps(expected, ensure_ascii=False))

    adjuster = OpenAITranslateAdjuster(api_key="test-key")
    work = _make_work(tmp_path, cv_data)
    result = adjuster.adjust(work, language="de", temperature="bad")

    output_path = result.get_step_output(StepName.Adjust)
    assert output_path is not None
    output = json.loads(output_path.read_text(encoding="utf-8"))
    assert output == expected

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["temperature"] == 0.0


def test_translate_adjuster_finish_reason_not_stop_returns_original(
    tmp_path: Path, monkeypatch
):
    cv_data = _load_fixture("translate_input.json")
    expected = _load_fixture("translate_expected_de.json")

    completion = MagicMock()
    completion.choices = [
        MagicMock(
            message=MagicMock(content=json.dumps(expected, ensure_ascii=False)),
            finish_reason="length",
        )
    ]
    _mock_openai_with_completion(monkeypatch, completion)

    adjuster = OpenAITranslateAdjuster(api_key="test-key")
    work = _make_work(tmp_path, cv_data)
    result = adjuster.adjust(work, language="de")

    output_path = result.get_step_output(StepName.Adjust)
    assert output_path is not None
    output = json.loads(output_path.read_text(encoding="utf-8"))
    assert output == cv_data


def test_translate_adjuster_empty_completion_returns_original(
    tmp_path: Path, monkeypatch
):
    cv_data = _load_fixture("translate_input.json")

    completion = MagicMock()
    completion.choices = [
        MagicMock(message=MagicMock(content=""), finish_reason="stop")
    ]
    _mock_openai_with_completion(monkeypatch, completion)

    adjuster = OpenAITranslateAdjuster(api_key="test-key")
    work = _make_work(tmp_path, cv_data)
    result = adjuster.adjust(work, language="de")

    output_path = result.get_step_output(StepName.Adjust)
    assert output_path is not None
    output = json.loads(output_path.read_text(encoding="utf-8"))
    assert output == cv_data


def test_translate_adjuster_invalid_json_returns_original(
    tmp_path: Path, monkeypatch
):
    cv_data = _load_fixture("translate_input.json")

    completion = MagicMock()
    completion.choices = [
        MagicMock(message=MagicMock(content="not-json"), finish_reason="stop")
    ]
    _mock_openai_with_completion(monkeypatch, completion)

    adjuster = OpenAITranslateAdjuster(api_key="test-key")
    work = _make_work(tmp_path, cv_data)
    result = adjuster.adjust(work, language="de")

    output_path = result.get_step_output(StepName.Adjust)
    assert output_path is not None
    output = json.loads(output_path.read_text(encoding="utf-8"))
    assert output == cv_data


def test_translate_adjuster_completion_choices_error_returns_original(
    tmp_path: Path, monkeypatch
):
    class ExplodingCompletion:
        @property
        def choices(self):
            raise RuntimeError("boom")

    cv_data = _load_fixture("translate_input.json")
    _mock_openai_with_completion(monkeypatch, ExplodingCompletion())

    adjuster = OpenAITranslateAdjuster(api_key="test-key")
    work = _make_work(tmp_path, cv_data)
    result = adjuster.adjust(work, language="de")

    output_path = result.get_step_output(StepName.Adjust)
    assert output_path is not None
    output = json.loads(output_path.read_text(encoding="utf-8"))
    assert output == cv_data


def test_translate_adjuster_openai_error_returns_original(
    tmp_path: Path, monkeypatch
):
    cv_data = _load_fixture("translate_input.json")

    class ExplodingRetry:
        def __init__(self, **_kwargs):
            pass

        def call(self, _fn, **_kwargs):
            raise RuntimeError("boom")

    import cvextract.adjusters.openai_translate_adjuster as translate_module

    monkeypatch.setattr(translate_module, "_OpenAIRetry", ExplodingRetry)
    monkeypatch.setattr(translate_module, "OpenAI", MagicMock())

    adjuster = OpenAITranslateAdjuster(api_key="test-key")
    work = _make_work(tmp_path, cv_data)
    result = adjuster.adjust(work, language="de")

    output_path = result.get_step_output(StepName.Adjust)
    assert output_path is not None
    output = json.loads(output_path.read_text(encoding="utf-8"))
    assert output == cv_data


def test_translate_adjuster_missing_api_key_returns_original(
    tmp_path: Path, monkeypatch
):
    cv_data = _load_fixture("translate_input.json")

    import cvextract.adjusters.openai_translate_adjuster as translate_module

    monkeypatch.setattr(translate_module, "OpenAI", MagicMock())

    adjuster = OpenAITranslateAdjuster(api_key=None)
    work = _make_work(tmp_path, cv_data)
    result = adjuster.adjust(work, language="de")

    output_path = result.get_step_output(StepName.Adjust)
    assert output_path is not None
    output = json.loads(output_path.read_text(encoding="utf-8"))
    assert output == cv_data


def test_translate_adjuster_schema_unavailable_returns_original(
    tmp_path: Path, monkeypatch
):
    cv_data = _load_fixture("translate_input.json")

    import cvextract.adjusters.openai_translate_adjuster as translate_module

    monkeypatch.setattr(translate_module, "_load_cv_schema", lambda: None)
    monkeypatch.setattr(translate_module, "OpenAI", MagicMock())

    adjuster = OpenAITranslateAdjuster(api_key="test-key")
    work = _make_work(tmp_path, cv_data)
    result = adjuster.adjust(work, language="de")

    output_path = result.get_step_output(StepName.Adjust)
    assert output_path is not None
    output = json.loads(output_path.read_text(encoding="utf-8"))
    assert output == cv_data


def test_translate_adjuster_prompt_missing_returns_original(
    tmp_path: Path, monkeypatch
):
    cv_data = _load_fixture("translate_input.json")

    import cvextract.adjusters.openai_translate_adjuster as translate_module

    monkeypatch.setattr(translate_module, "format_prompt", lambda *args, **kwargs: None)
    monkeypatch.setattr(translate_module, "OpenAI", MagicMock())

    adjuster = OpenAITranslateAdjuster(api_key="test-key")
    work = _make_work(tmp_path, cv_data)
    result = adjuster.adjust(work, language="de")

    output_path = result.get_step_output(StepName.Adjust)
    assert output_path is not None
    output = json.loads(output_path.read_text(encoding="utf-8"))
    assert output == cv_data
