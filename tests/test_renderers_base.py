"""
Tests for CVRenderer abstract base class.

Tests that the abstract interface is properly defined and enforces
correct implementation patterns for concrete renderers.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from cvextract.renderers.base import CVRenderer
from cvextract.shared import StepName, UnitOfWork


def _make_work(
    make_render_work,
    tmp_path: Path,
    cv_data: dict | None = None,
    template_path: Path | None = None,
    output_path: Path | None = None,
) -> UnitOfWork:
    template_path = template_path or (tmp_path / "template.docx")
    output_path = output_path or (tmp_path / "output.docx")
    cv_data = cv_data or {}
    return make_render_work(cv_data, template_path, output_path)


def _load_cv_data(work: UnitOfWork) -> dict:
    input_path = work.get_step_input(StepName.Render)
    with input_path.open("r", encoding="utf-8") as f:
        return json.load(f)


class TestCVRendererAbstract:
    """Tests for CVRenderer abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that CVRenderer cannot be instantiated directly."""
        with pytest.raises(TypeError) as exc_info:
            CVRenderer()
        assert "abstract" in str(exc_info.value).lower()

    def test_render_method_must_be_implemented(self):
        """Test that render() is an abstract method requiring implementation."""

        class IncompleteRenderer(CVRenderer):
            """Renderer missing render() implementation."""

        with pytest.raises(TypeError):
            IncompleteRenderer()

    def test_render_method_can_be_implemented(self, tmp_path, make_render_work):
        """Test that render() can be properly implemented in concrete class."""

        class ConcreteRenderer(CVRenderer):
            """Concrete implementation of CVRenderer."""

            def render(self, work: UnitOfWork) -> UnitOfWork:
                return work

        renderer = ConcreteRenderer()
        work = _make_work(make_render_work, tmp_path)
        result = renderer.render(work)
        assert isinstance(result, UnitOfWork)
        assert result.get_step_output(StepName.Render) == work.get_step_output(
            StepName.Render
        )

    def test_render_method_signature_accepts_all_parameters(
        self, tmp_path, make_render_work
    ):
        """Test that render() accepts UnitOfWork."""

        class TestRenderer(CVRenderer):
            def render(self, work: UnitOfWork) -> UnitOfWork:
                assert isinstance(work, UnitOfWork)
                assert isinstance(work.config.render.template, Path)
                assert isinstance(work.get_step_output(StepName.Render), Path)
                return work

        renderer = TestRenderer()
        cv_data = {"identity": {"full_name": "John"}}
        template = tmp_path / "template.docx"
        output = tmp_path / "output.docx"
        work = make_render_work(cv_data, template, output)

        result = renderer.render(work)
        assert result.get_step_output(StepName.Render) == output

    def test_render_method_returns_unit_of_work(self, tmp_path, make_render_work):
        """Test that render() returns a UnitOfWork object."""

        class TestRenderer(CVRenderer):
            def render(self, work: UnitOfWork) -> UnitOfWork:
                return work

        renderer = TestRenderer()
        work = _make_work(make_render_work, tmp_path)
        result = renderer.render(work)
        assert isinstance(result, UnitOfWork)

    def test_render_method_can_raise_file_not_found_for_template(
        self, tmp_path, make_render_work
    ):
        """Test that render() can raise FileNotFoundError for missing template."""

        class TestRenderer(CVRenderer):
            def render(self, work: UnitOfWork) -> UnitOfWork:
                template_path = work.config.render.template
                if not template_path.exists():
                    raise FileNotFoundError(f"Template not found: {template_path}")
                return work

        renderer = TestRenderer()
        missing_template = tmp_path / "missing.docx"
        work = _make_work(
            make_render_work,
            tmp_path,
            template_path=missing_template,
            output_path=tmp_path / "output.docx",
        )
        with pytest.raises(FileNotFoundError):
            renderer.render(work)

    def test_render_method_can_raise_generic_exception(
        self, tmp_path, make_render_work
    ):
        """Test that render() can raise generic Exception for rendering errors."""

        class TestRenderer(CVRenderer):
            def render(self, work: UnitOfWork) -> UnitOfWork:
                raise Exception("Rendering failed")

        renderer = TestRenderer()
        work = _make_work(make_render_work, tmp_path)
        with pytest.raises(Exception) as exc_info:
            renderer.render(work)
        assert "Rendering failed" in str(exc_info.value)

    def test_concrete_implementation_processes_cv_data(
        self, tmp_path, make_render_work
    ):
        """Test concrete implementation can process CV data from work.input."""

        class DataAwareRenderer(CVRenderer):
            def render(self, work: UnitOfWork) -> UnitOfWork:
                cv_data = _load_cv_data(work)
                if "identity" in cv_data:
                    _ = cv_data["identity"].get("full_name", "Unknown")
                return work

        renderer = DataAwareRenderer()
        cv_data = {
            "identity": {
                "full_name": "Jane Smith",
                "title": "Engineer",
            }
        }
        work = _make_work(make_render_work, tmp_path, cv_data=cv_data)
        result = renderer.render(work)
        assert result.get_step_output(StepName.Render) == work.get_step_output(
            StepName.Render
        )

    def test_concrete_implementation_with_full_schema(self, tmp_path, make_render_work):
        """Test concrete implementation with full CV schema."""

        class FullRenderer(CVRenderer):
            def render(self, work: UnitOfWork) -> UnitOfWork:
                cv_data = _load_cv_data(work)
                _ = cv_data.get("identity", {})
                _ = cv_data.get("sidebar", {})
                _ = cv_data.get("overview", "")
                _ = cv_data.get("experiences", [])
                return work

        renderer = FullRenderer()
        cv_data = {
            "identity": {
                "title": "Senior Engineer",
                "full_name": "Alice Brown",
                "first_name": "Alice",
                "last_name": "Brown",
            },
            "sidebar": {
                "languages": ["Python"],
                "tools": ["Git"],
                "certifications": ["AWS"],
                "industries": ["Tech"],
                "spoken_languages": ["English"],
                "academic_background": ["BS CS"],
            },
            "overview": "Experienced engineer",
            "experiences": [
                {
                    "heading": "Engineer",
                    "description": "Built systems",
                    "bullets": ["Led team"],
                    "environment": ["Python"],
                }
            ],
        }
        work = _make_work(make_render_work, tmp_path, cv_data=cv_data)
        result = renderer.render(work)
        assert result.get_step_output(StepName.Render) == work.get_step_output(
            StepName.Render
        )

    def test_multiple_renderers_can_coexist(self, tmp_path, make_render_work):
        """Test that multiple concrete renderers can be defined independently."""

        class DocxRenderer(CVRenderer):
            def render(self, work: UnitOfWork) -> UnitOfWork:
                return work

        class PDFRenderer(CVRenderer):
            def render(self, work: UnitOfWork) -> UnitOfWork:
                status = work.ensure_step_status(StepName.Render)
                status.output = status.output.with_suffix(".pdf")
                return work

        docx = DocxRenderer()
        pdf = PDFRenderer()

        work_docx = _make_work(
            make_render_work, tmp_path, output_path=tmp_path / "output.docx"
        )
        work_pdf = _make_work(
            make_render_work, tmp_path, output_path=tmp_path / "output"
        )

        result_docx = docx.render(work_docx)
        result_pdf = pdf.render(work_pdf)

        assert result_docx.get_step_output(StepName.Render).suffix == ".docx"
        assert result_pdf.get_step_output(StepName.Render).suffix == ".pdf"

    def test_render_creates_output_path_object(self, tmp_path, make_render_work):
        """Test that render() can create and return new Path objects."""

        class PathCreatorRenderer(CVRenderer):
            def render(self, work: UnitOfWork) -> UnitOfWork:
                status = work.ensure_step_status(StepName.Render)
                status.output = Path(status.output.parent) / status.output.name
                return work

        renderer = PathCreatorRenderer()
        work = _make_work(
            make_render_work,
            tmp_path,
            output_path=tmp_path / "output" / "result.docx",
        )
        result = renderer.render(work)

        assert isinstance(result, UnitOfWork)
        assert result.get_step_output(StepName.Render).name == "result.docx"

    def test_render_with_empty_cv_data(self, tmp_path, make_render_work):
        """Test that render() can handle empty CV data."""

        class TestRenderer(CVRenderer):
            def render(self, work: UnitOfWork) -> UnitOfWork:
                cv_data = _load_cv_data(work)
                if not cv_data:
                    return work
                return work

        renderer = TestRenderer()
        work = _make_work(make_render_work, tmp_path, cv_data={})
        result = renderer.render(work)
        assert result.get_step_output(StepName.Render) == work.get_step_output(
            StepName.Render
        )

    def test_render_method_override_works(self, tmp_path, make_render_work):
        """Test that render() method can be properly overridden."""

        class BaseRenderer(CVRenderer):
            def render(self, work: UnitOfWork) -> UnitOfWork:
                return work

        class DerivedRenderer(BaseRenderer):
            def render(self, work: UnitOfWork) -> UnitOfWork:
                base_output = super().render(work).get_step_output(StepName.Render)
                status = work.ensure_step_status(StepName.Render)
                status.output = Path(str(base_output).replace(".docx", "_derived.docx"))
                return work

        renderer = DerivedRenderer()
        work = _make_work(make_render_work, tmp_path)
        result = renderer.render(work)
        assert "_derived" in str(result.get_step_output(StepName.Render))

    def test_is_abstract_base_class(self):
        """Test that CVRenderer is an abstract base class."""
        from abc import ABC

        assert issubclass(CVRenderer, ABC)

    def test_render_is_abstractmethod(self):
        """Test that render is marked as abstract."""
        from inspect import isabstract

        assert isabstract(CVRenderer)
        assert hasattr(CVRenderer.render, "__isabstractmethod__")
        assert CVRenderer.render.__isabstractmethod__

    def test_render_can_handle_absolute_paths(self, tmp_path, make_render_work):
        """Test that render() can handle absolute paths."""

        class TestRenderer(CVRenderer):
            def render(self, work: UnitOfWork) -> UnitOfWork:
                status = work.ensure_step_status(StepName.Render)
                status.output = status.output.resolve()
                return work

        renderer = TestRenderer()
        output = Path("/tmp/output.docx")
        work = _make_work(
            make_render_work,
            tmp_path,
            template_path=Path("/tmp/template.docx"),
            output_path=output,
        )
        result = renderer.render(work)

        assert isinstance(result, UnitOfWork)
        assert str(result.get_step_output(StepName.Render)).startswith("/")

    def test_render_can_handle_relative_paths(self, tmp_path, make_render_work):
        """Test that render() can handle relative paths."""

        class TestRenderer(CVRenderer):
            def render(self, work: UnitOfWork) -> UnitOfWork:
                return work

        renderer = TestRenderer()
        work = _make_work(
            make_render_work,
            tmp_path,
            template_path=Path("templates/cv.docx"),
            output_path=Path("outputs/my_cv.docx"),
        )
        result = renderer.render(work)

        assert str(result.get_step_output(StepName.Render)) == "outputs/my_cv.docx"

    def test_render_implementations_are_independent(self, tmp_path, make_render_work):
        """Test that different implementations don't interfere."""

        class Impl1(CVRenderer):
            def render(self, work: UnitOfWork) -> UnitOfWork:
                status = work.ensure_step_status(StepName.Render)
                status.output = Path("format1.docx")
                return work

        class Impl2(CVRenderer):
            def render(self, work: UnitOfWork) -> UnitOfWork:
                status = work.ensure_step_status(StepName.Render)
                status.output = Path("format2.docx")
                return work

        impl1 = Impl1()
        impl2 = Impl2()

        work1 = _make_work(make_render_work, tmp_path)
        work2 = _make_work(make_render_work, tmp_path)
        result1 = impl1.render(work1)
        result2 = impl2.render(work2)

        assert str(result1.get_step_output(StepName.Render)) == "format1.docx"
        assert str(result2.get_step_output(StepName.Render)) == "format2.docx"

    def test_render_with_mocked_implementation(self, tmp_path, make_render_work):
        """Test that render() works correctly when mocked."""

        class TestRenderer(CVRenderer):
            def render(self, work: UnitOfWork) -> UnitOfWork:
                return work

        renderer = TestRenderer()
        work = _make_work(make_render_work, tmp_path)
        with patch.object(renderer, "render") as mock_render:
            mock_render.return_value = work
            result = renderer.render(work)

            assert result == work
            mock_render.assert_called_once_with(work)
