"""Tests for the OpenAI translate adjuster."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cvextract.adjusters.openai_translate_adjuster import (
    OpenAITranslateAdjuster,
    _TextProtector,
    _collect_protected_terms,
    _load_cv_schema,
    _map_strings,
    _restore_protected_fields,
    _validate_cv_data,
)
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


def test_translate_adjuster_openai_unavailable_returns_original(
    tmp_path: Path, monkeypatch
):
    cv_data = _load_fixture("translate_input.json")

    import cvextract.adjusters.openai_translate_adjuster as translate_module

    monkeypatch.setattr(translate_module, "OpenAI", None)

    adjuster = OpenAITranslateAdjuster(api_key="test-key")
    work = _make_work(tmp_path, cv_data)
    result = adjuster.adjust(work, language="de")

    output_path = result.get_step_output(StepName.Adjust)
    assert output_path is not None
    output = json.loads(output_path.read_text(encoding="utf-8"))
    assert output == cv_data


def test_translate_adjuster_requires_language_param(tmp_path: Path):
    adjuster = OpenAITranslateAdjuster(api_key="test-key")
    work = _make_work(tmp_path, _load_fixture("translate_input.json"))

    with pytest.raises(ValueError, match="requires non-empty 'language'"):
        adjuster.adjust(work)


def test_text_protector_skips_empty_and_duplicate_terms():
    protector = _TextProtector(["Python", "", "Python", "Go"])

    assert len(protector._term_patterns) == 2


def test_validate_cv_data_experiences_errors():
    schema_path = (
        Path(__file__).resolve().parents[1]
        / "cvextract"
        / "contracts"
        / "cv_schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    data = {
        "identity": {
            "title": "Engineer",
            "full_name": "Ada Lovelace",
            "first_name": "Ada",
            "last_name": "Lovelace",
        },
        "sidebar": {},
        "overview": "Summary",
        "experiences": [
            "not-a-dict",
            {"heading": 123, "description": 456},
            {"description": "ok"},
            {"heading": "Head"},
            {"heading": "Head", "description": "Desc", "bullets": "nope"},
            {"heading": "Head", "description": "Desc", "bullets": [1, "ok"]},
        ],
    }

    errs = _validate_cv_data(data, schema)
    expected = [
        "experiences[0] must be an object",
        "experiences[1].heading must be a string",
        "experiences[1].description must be a string",
        "experiences[2] missing required field: heading",
        "experiences[3] missing required field: description",
        "experiences[4].bullets must be an array",
        "experiences[5].bullets items must be strings",
    ]
    for message in expected:
        assert message in errs


def test_validate_cv_data_sidebar_overview_and_experiences_type_errors():
    schema_path = (
        Path(__file__).resolve().parents[1]
        / "cvextract"
        / "contracts"
        / "cv_schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    data = {
        "identity": {
            "title": "Engineer",
            "full_name": "Ada Lovelace",
            "first_name": "Ada",
            "last_name": "Lovelace",
        },
        "sidebar": "not-a-dict",
        "overview": ["not", "a", "string"],
        "experiences": "not-a-list",
    }

    errs = _validate_cv_data(data, schema)
    assert "sidebar must be an object" in errs
    assert "overview must be a string" in errs
    assert "experiences must be an array" in errs


def test_validate_cv_data_identity_required_and_non_empty():
    schema_path = (
        Path(__file__).resolve().parents[1]
        / "cvextract"
        / "contracts"
        / "cv_schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    data = {
        "identity": {"title": "", "full_name": "Ada Lovelace", "first_name": "Ada"},
        "sidebar": {},
        "overview": "Summary",
        "experiences": [],
    }

    errs = _validate_cv_data(data, schema)
    assert "identity missing required field: last_name" in errs
    assert "identity.title must be a non-empty string" in errs


def test_validate_cv_data_non_object_returns_error():
    schema_path = (
        Path(__file__).resolve().parents[1]
        / "cvextract"
        / "contracts"
        / "cv_schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    errs = _validate_cv_data(["not", "an", "object"], schema)
    assert errs == ["translated JSON must be an object"]


def test_load_cv_schema_without_path_returns_none(monkeypatch):
    import cvextract.adjusters.openai_translate_adjuster as translate_module

    monkeypatch.setattr(translate_module, "_SCHEMA_PATH", None)
    monkeypatch.setattr(translate_module, "_CV_SCHEMA", None)

    assert _load_cv_schema() is None


def test_load_cv_schema_bad_json_returns_none(tmp_path: Path, monkeypatch):
    import cvextract.adjusters.openai_translate_adjuster as translate_module

    schema_path = tmp_path / "bad_schema.json"
    schema_path.write_text("not-json", encoding="utf-8")

    monkeypatch.setattr(translate_module, "_SCHEMA_PATH", schema_path)
    monkeypatch.setattr(translate_module, "_CV_SCHEMA", None)

    assert _load_cv_schema() is None


def test_validate_cv_data_environment_errors():
    schema_path = (
        Path(__file__).resolve().parents[1]
        / "cvextract"
        / "contracts"
        / "cv_schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    data = {
        "identity": {
            "title": "Engineer",
            "full_name": "Ada Lovelace",
            "first_name": "Ada",
            "last_name": "Lovelace",
        },
        "sidebar": {},
        "overview": "Summary",
        "experiences": [
            {"heading": "Head", "description": "Desc", "environment": "oops"},
            {"heading": "Head", "description": "Desc", "environment": [1, "ok"]},
        ],
    }

    errs = _validate_cv_data(data, schema)
    assert "experiences[0].environment must be an array or null" in errs
    assert "experiences[1].environment items must be strings" in errs


def test_collect_protected_terms_skips_non_dict_experiences():
    cv_data = {
        "identity": {},
        "sidebar": {},
        "overview": "",
        "experiences": ["not-a-dict", {"environment": ["Python"]}],
    }

    terms = _collect_protected_terms(cv_data)
    assert terms == ["Python"]


def test_map_strings_returns_unmodified_non_string():
    assert _map_strings(5, lambda s: s.upper()) == 5


def test_restore_protected_fields_skips_invalid_experiences():
    original = {
        "identity": {"full_name": "Ada"},
        "sidebar": {},
        "experiences": ["not-a-dict"],
    }
    translated = {
        "identity": {"full_name": "Translated"},
        "sidebar": {},
        "experiences": ["still-not-a-dict"],
    }

    restored = _restore_protected_fields(original, translated)
    assert restored["experiences"] == ["still-not-a-dict"]


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
