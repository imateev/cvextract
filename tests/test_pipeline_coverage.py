"""Tests for improved coverage of pipeline module critical paths."""

import json
from unittest.mock import patch, MagicMock
from cvextract.pipeline_helpers import (
    extract_single,
    categorize_result,
    render_and_verify,
    infer_source_root,
)
from cvextract.shared import StepName, StepStatus, UnitOfWork, get_status_icons
from cvextract.cli_config import UserConfig, ExtractStage, RenderStage, AdjustStage
from cvextract.verifiers import get_verifier
from cvextract.shared import VerificationResult


class TestExtractSingle:
    """Tests for extract_single function."""

    def testextract_single_success(self, tmp_path):
        """Test successful extraction."""
        docx_path = tmp_path / "test.docx"
        out_json = tmp_path / "out.json"
        docx_path.touch()
        
        # Mock the extraction pipeline
        mock_data = {
            "identity": {"title": "Engineer", "full_name": "John Doe", "first_name": "John", "last_name": "Doe"},
            "sidebar": {"languages": ["EN"]},
            "overview": "Text",
            "experiences": [{"heading": "Job", "description": "Work", "bullets": ["Item"]}],
        }
        
        mock_verifier = MagicMock()
        mock_verifier.verify.return_value = VerificationResult(ok=True, errors=[], warnings=[])
        
        with patch("cvextract.pipeline_helpers.process_single_docx") as mock_extract, \
             patch("cvextract.pipeline_helpers.get_verifier") as mock_get_verifier:
            
            mock_extract.return_value = mock_data
            mock_get_verifier.return_value = mock_verifier
            
            work = UnitOfWork(
                config=UserConfig(target_dir=tmp_path, extract=ExtractStage(source=docx_path)),
                input=docx_path,
                output=out_json,
            )
            result = extract_single(work)
            extract_status = result.step_statuses[StepName.Extract]

            assert extract_status.errors == []
            assert extract_status.warnings == []

    def testextract_single_invalid_data(self, tmp_path):
        """Test verification failure with invalid data."""
        docx_path = tmp_path / "test.docx"
        out_json = tmp_path / "out.json"
        docx_path.touch()
        
        mock_data = {"identity": {}}  # Missing required fields
        
        with patch("cvextract.pipeline_helpers.process_single_docx") as mock_extract:
            
            mock_extract.return_value = mock_data
            
            work = UnitOfWork(
                config=UserConfig(target_dir=tmp_path, extract=ExtractStage(source=docx_path)),
                input=docx_path,
                output=out_json,
            )
            result = extract_single(work)

            # The actual verifier will catch these errors
            extract_status = result.step_statuses[StepName.Extract]
            # Check that there are errors for missing fields
            assert len(extract_status.errors) > 0

    def testextract_single_exception_no_debug(self, tmp_path):
        """Test exception handling without debug mode."""
        docx_path = tmp_path / "test.docx"
        out_json = tmp_path / "out.json"
        docx_path.touch()
        
        with patch("cvextract.pipeline_helpers.process_single_docx") as mock_extract:
            mock_extract.side_effect = ValueError("Bad file")
            
            work = UnitOfWork(
                config=UserConfig(target_dir=tmp_path, extract=ExtractStage(source=docx_path)),
                input=docx_path,
                output=out_json,
            )
            result = extract_single(work)
            extract_status = result.step_statuses[StepName.Extract]

            assert any("exception" in e.lower() or "ValueError" in e for e in extract_status.errors)

    def testextract_single_exception_with_debug(self, tmp_path):
        """Test exception logging with debug mode enabled."""
        docx_path = tmp_path / "test.docx"
        out_json = tmp_path / "out.json"
        docx_path.touch()
        
        with patch("cvextract.pipeline_helpers.process_single_docx") as mock_extract, \
             patch("cvextract.pipeline_helpers.dump_body_sample"):
            
            mock_extract.side_effect = ValueError("Bad file")
            
            work = UnitOfWork(
                config=UserConfig(target_dir=tmp_path, extract=ExtractStage(source=docx_path), verbosity="debug"),
                input=docx_path,
                output=out_json,
            )
            result = extract_single(work)
            extract_status = result.step_statuses[StepName.Extract]

            assert extract_status.errors

    def testextract_single_with_warnings(self, tmp_path):
        """Test that warnings are preserved."""
        docx_path = tmp_path / "test.docx"
        out_json = tmp_path / "out.json"
        docx_path.touch()
        
        mock_data = {
            "identity": {"title": "T", "full_name": "A B", "first_name": "A", "last_name": "B"},
            "sidebar": {"languages": ["EN"]},
            "overview": "Text",
            "experiences": [],
        }
        
        mock_verifier = MagicMock()
        mock_verifier.verify.return_value = VerificationResult(
            ok=True,
            errors=[],
            warnings=["Warning message"]
        )
        
        with patch("cvextract.pipeline_helpers.process_single_docx") as mock_extract, \
             patch("cvextract.pipeline_helpers.get_verifier") as mock_get_verifier:
            
            mock_extract.return_value = mock_data
            mock_get_verifier.return_value = mock_verifier
            
            work = UnitOfWork(
                config=UserConfig(target_dir=tmp_path, extract=ExtractStage(source=docx_path)),
                input=docx_path,
                output=out_json,
            )
            result = extract_single(work)
            extract_status = result.step_statuses[StepName.Extract]

            assert "Warning message" in extract_status.warnings


class TestRenderAndVerify:
    """Tests for render_and_verify function."""

    def testrender_and_verify_success(self, tmp_path):
        """Test successful render and verify."""
        json_path = tmp_path / "test.json"
        template_path = tmp_path / "template.docx"
        out_dir = tmp_path / "out"
        
        json_path.write_text(json.dumps({
            "identity": {"title": "T", "full_name": "A B", "first_name": "A", "last_name": "B"},
            "sidebar": {},
            "overview": "",
            "experiences": [],
        }))
        template_path.touch()
        
        rendered_docx = out_dir / "test_NEW.docx"
        
        mock_verifier = MagicMock()
        mock_verifier.verify.return_value = VerificationResult(ok=True, errors=[], warnings=[])
        
        with patch("cvextract.pipeline_helpers.render_cv_data") as mock_render, \
             patch("cvextract.pipeline_helpers.process_single_docx") as mock_process, \
             patch("cvextract.pipeline_helpers.get_verifier") as mock_get_verifier:
            
            mock_render.side_effect = lambda work: work
            mock_process.return_value = json.loads(json_path.read_text())
            mock_get_verifier.return_value = mock_verifier
            
            config = UserConfig(
                target_dir=out_dir,
                render=RenderStage(template=template_path, data=json_path, output=rendered_docx),
            )
            work = UnitOfWork(
                config=config,
                input=json_path,
                output=json_path,
                initial_input=json_path,
            )
            result = render_and_verify(work)
            render_status = result.step_statuses[StepName.Render]
            verify_status = result.step_statuses[StepName.RoundtripComparer]
            
            assert render_status.errors == []
            assert render_status.warnings == []
            assert verify_status.errors == []

    def testrender_and_verify_skip_compare(self, tmp_path):
        """Test compare skipped when adjust stage is present."""
        json_path = tmp_path / "test.json"
        template_path = tmp_path / "template.docx"
        out_dir = tmp_path / "out"
        
        json_path.write_text(json.dumps({
            "identity": {"title": "T", "full_name": "A B", "first_name": "A", "last_name": "B"},
            "sidebar": {},
            "overview": "",
            "experiences": [],
        }))
        template_path.touch()
        
        with patch("cvextract.pipeline_helpers.render_cv_data") as mock_render:
            mock_render.side_effect = lambda work: work
            
            config = UserConfig(
                target_dir=out_dir,
                render=RenderStage(template=template_path, data=json_path),
                adjust=AdjustStage(adjusters=[], data=json_path),
            )
            work = UnitOfWork(
                config=config,
                input=json_path,
                output=json_path,
                initial_input=json_path,
            )
            result = render_and_verify(work)
            render_status = result.step_statuses[StepName.Render]
            
            assert render_status.errors == []
            assert StepName.RoundtripComparer not in result.step_statuses  # Not executed

    def testrender_and_verify_with_roundtrip_dir(self, tmp_path):
        """Test roundtrip verification directory is created."""
        json_path = tmp_path / "test.json"
        template_path = tmp_path / "template.docx"
        out_dir = tmp_path / "out"
        test_data = {
            "identity": {"title": "T", "full_name": "A B", "first_name": "A", "last_name": "B"},
            "sidebar": {},
            "overview": "",
            "experiences": [],
        }
        json_path.write_text(json.dumps(test_data))
        template_path.touch()
        
        rendered_docx = out_dir / "test_NEW.docx"
        
        mock_verifier = MagicMock()
        mock_verifier.verify.return_value = VerificationResult(ok=True, errors=[], warnings=[])
        
        with patch("cvextract.pipeline_helpers.render_cv_data") as mock_render, \
             patch("cvextract.pipeline_helpers.process_single_docx") as mock_process, \
             patch("cvextract.pipeline_helpers.get_verifier") as mock_get_verifier:
            
            mock_render.side_effect = lambda work: work
            mock_process.return_value = test_data
            mock_get_verifier.return_value = mock_verifier
            
            config = UserConfig(
                target_dir=out_dir,
                render=RenderStage(template=template_path, data=json_path, output=rendered_docx),
            )
            work = UnitOfWork(
                config=config,
                input=json_path,
                output=json_path,
                initial_input=json_path,
            )
            result = render_and_verify(work)
            render_status = result.step_statuses[StepName.Render]
            
            assert render_status.errors == []
            # Verify roundtrip_dir was created
            expected_dir = out_dir / "verification_structured_data"
            assert expected_dir.exists()

    def testrender_and_verify_compare_failure(self, tmp_path):
        """Test when comparison finds differences."""
        json_path = tmp_path / "test.json"
        template_path = tmp_path / "template.docx"
        out_dir = tmp_path / "out"
        
        json_path.write_text(json.dumps({
            "identity": {"title": "T", "full_name": "A B", "first_name": "A", "last_name": "B"},
            "sidebar": {},
            "overview": "",
            "experiences": [],
        }))
        template_path.touch()
        
        rendered_docx = out_dir / "test_NEW.docx"
        
        mock_verifier = MagicMock()
        mock_verifier.verify.return_value = VerificationResult(
            ok=False,
            errors=["Mismatch detected"],
            warnings=[]
        )
        
        with patch("cvextract.pipeline_helpers.render_cv_data") as mock_render, \
             patch("cvextract.pipeline_helpers.process_single_docx") as mock_process, \
             patch("cvextract.pipeline_helpers.get_verifier") as mock_get_verifier:
            
            mock_render.side_effect = lambda work: work
            mock_process.return_value = {"identity": {"title": "Different"}, "sidebar": {}, "overview": "", "experiences": []}
            mock_get_verifier.return_value = mock_verifier
            
            config = UserConfig(
                target_dir=out_dir,
                render=RenderStage(template=template_path, data=json_path, output=rendered_docx),
            )
            work = UnitOfWork(
                config=config,
                input=json_path,
                output=json_path,
                initial_input=json_path,
            )
            result = render_and_verify(work)
            render_status = result.step_statuses[StepName.Render]
            verify_status = result.step_statuses[StepName.RoundtripComparer]
            
            assert render_status.errors == []
            assert "Mismatch detected" in verify_status.errors

    def testrender_and_verify_render_exception(self, tmp_path):
        """Test exception during rendering."""
        json_path = tmp_path / "test.json"
        template_path = tmp_path / "template.docx"
        out_dir = tmp_path / "out"
        
        json_path.write_text(json.dumps({}))
        template_path.touch()
        
        with patch("cvextract.pipeline_helpers.render_cv_data") as mock_render:
            mock_render.side_effect = RuntimeError("Render failed")
            
            config = UserConfig(
                target_dir=out_dir,
                render=RenderStage(template=template_path, data=json_path),
            )
            work = UnitOfWork(
                config=config,
                input=json_path,
                output=json_path,
                initial_input=json_path,
            )
            result = render_and_verify(work)
            render_status = result.step_statuses[StepName.Render]
            
            assert render_status.errors == []
            assert any("RuntimeError" in w for w in render_status.warnings)
            assert StepName.RoundtripComparer not in result.step_statuses


class TestCategorizeResult:
    """Tests for categorize_result function."""

    def test_categorize_extract_failed(self):
        """Test when extraction failed."""
        fully_ok, partial_ok, failed = categorize_result(extract_ok=False, has_warns=False, apply_ok=None)
        assert (fully_ok, partial_ok, failed) == (0, 0, 1)

    def test_categorize_apply_failed(self):
        """Test when apply failed."""
        fully_ok, partial_ok, failed = categorize_result(extract_ok=True, has_warns=False, apply_ok=False)
        assert (fully_ok, partial_ok, failed) == (0, 1, 0)

    def test_categorize_with_warnings(self):
        """Test when result has warnings."""
        fully_ok, partial_ok, failed = categorize_result(extract_ok=True, has_warns=True, apply_ok=True)
        assert (fully_ok, partial_ok, failed) == (0, 1, 0)

    def test_categorize_fully_ok(self):
        """Test fully successful result."""
        fully_ok, partial_ok, failed = categorize_result(extract_ok=True, has_warns=False, apply_ok=True)
        assert (fully_ok, partial_ok, failed) == (1, 0, 0)

    def test_categorize_apply_none_with_warns(self):
        """Test when apply is None but has warnings."""
        fully_ok, partial_ok, failed = categorize_result(extract_ok=True, has_warns=True, apply_ok=None)
        assert (fully_ok, partial_ok, failed) == (0, 1, 0)


class TestGetStatusIcons:
    """Tests for get_status_icons function."""

    def test_extract_ok_with_warnings(self, tmp_path):
        """Test extract ok but with warnings."""
        work = UnitOfWork(
            config=UserConfig(target_dir=tmp_path),
            input=tmp_path / "input.json",
            output=tmp_path / "output.json",
        )
        work.step_statuses[StepName.Extract] = StepStatus(
            step=StepName.Extract,
            warnings=["warning"],
        )
        work.step_statuses[StepName.Render] = StepStatus(step=StepName.Render)
        work.step_statuses[StepName.RoundtripComparer] = StepStatus(step=StepName.RoundtripComparer)
        icons = get_status_icons(work)
        assert "❎" in icons[StepName.Extract]  # Warning icon for extract

    def test_extract_ok_no_warnings(self, tmp_path):
        """Test extract ok without warnings."""
        work = UnitOfWork(
            config=UserConfig(target_dir=tmp_path),
            input=tmp_path / "input.json",
            output=tmp_path / "output.json",
        )
        work.step_statuses[StepName.Extract] = StepStatus(step=StepName.Extract)
        work.step_statuses[StepName.Render] = StepStatus(step=StepName.Render)
        work.step_statuses[StepName.RoundtripComparer] = StepStatus(step=StepName.RoundtripComparer)
        icons = get_status_icons(work)
        assert "🟢" in icons[StepName.Extract]  # Green icon

    def test_extract_failed(self, tmp_path):
        """Test extract failed."""
        work = UnitOfWork(
            config=UserConfig(target_dir=tmp_path),
            input=tmp_path / "input.json",
            output=tmp_path / "output.json",
        )
        work.step_statuses[StepName.Extract] = StepStatus(
            step=StepName.Extract,
            errors=["error"],
        )
        work.step_statuses[StepName.Render] = StepStatus(
            step=StepName.Render,
            errors=["render error"],
        )
        work.step_statuses[StepName.RoundtripComparer] = StepStatus(
            step=StepName.RoundtripComparer,
            errors=["compare error"],
        )
        icons = get_status_icons(work)
        assert "❌" in icons[StepName.Extract]  # Fail icon

    def test_apply_none(self, tmp_path):
        """Test apply not executed."""
        work = UnitOfWork(
            config=UserConfig(target_dir=tmp_path),
            input=tmp_path / "input.json",
            output=tmp_path / "output.json",
        )
        work.step_statuses[StepName.Extract] = StepStatus(step=StepName.Extract)
        icons = get_status_icons(work)
        assert "➖" in icons[StepName.Render]  # Neutral icon for apply

    def test_compare_ok(self, tmp_path):
        """Test compare successful."""
        work = UnitOfWork(
            config=UserConfig(target_dir=tmp_path),
            input=tmp_path / "input.json",
            output=tmp_path / "output.json",
        )
        work.step_statuses[StepName.Extract] = StepStatus(step=StepName.Extract)
        work.step_statuses[StepName.Render] = StepStatus(step=StepName.Render)
        work.step_statuses[StepName.RoundtripComparer] = StepStatus(step=StepName.RoundtripComparer)
        icons = get_status_icons(work)
        assert "✅" in icons[StepName.RoundtripComparer] or "✓" in icons[StepName.RoundtripComparer]

    def test_compare_failed(self, tmp_path):
        """Test compare found differences."""
        work = UnitOfWork(
            config=UserConfig(target_dir=tmp_path),
            input=tmp_path / "input.json",
            output=tmp_path / "output.json",
        )
        work.step_statuses[StepName.Extract] = StepStatus(step=StepName.Extract)
        work.step_statuses[StepName.Render] = StepStatus(step=StepName.Render)
        work.step_statuses[StepName.RoundtripComparer] = StepStatus(
            step=StepName.RoundtripComparer,
            errors=["compare mismatch"],
        )
        icons = get_status_icons(work)
        assert "❌" in icons[StepName.RoundtripComparer]  # Error for compare mismatch

    def test_compare_none(self, tmp_path):
        """Test compare not executed."""
        work = UnitOfWork(
            config=UserConfig(target_dir=tmp_path),
            input=tmp_path / "input.json",
            output=tmp_path / "output.json",
        )
        work.step_statuses[StepName.Extract] = StepStatus(step=StepName.Extract)
        work.step_statuses[StepName.Render] = StepStatus(step=StepName.Render)
        icons = get_status_icons(work)
        assert "➖" in icons[StepName.RoundtripComparer]


class TestInferSourceRoot:
    """Tests for infer_source_root function."""

    def test_infer_from_single_file(self, tmp_path):
        """Test inferring root from single JSON file."""
        json_file = tmp_path / "data.json"
        json_file.touch()
        
        root = infer_source_root([json_file])
        assert root == tmp_path

    def test_infer_from_nested_files(self, tmp_path):
        """Test inferring root from nested JSON files."""
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()
        
        file1 = dir1 / "data1.json"
        file2 = dir2 / "data2.json"
        file1.touch()
        file2.touch()
        
        root = infer_source_root([file1, file2])
        assert root == tmp_path

    def test_infer_with_deeply_nested_files(self, tmp_path):
        """Test inferring root with deeply nested files."""
        deep_dir = tmp_path / "a" / "b" / "c"
        deep_dir.mkdir(parents=True)
        
        file1 = tmp_path / "file1.json"
        file2 = deep_dir / "file2.json"
        file1.touch()
        file2.touch()
        
        root = infer_source_root([file1, file2])
        assert root == tmp_path
