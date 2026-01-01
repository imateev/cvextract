"""
Tests for CVRenderer abstract base class.

Tests that the abstract interface is properly defined and enforces
correct implementation patterns for concrete renderers.
"""

from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from cvextract.renderers.base import CVRenderer


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
            pass
        
        with pytest.raises(TypeError):
            IncompleteRenderer()

    def test_render_method_can_be_implemented(self):
        """Test that render() can be properly implemented in concrete class."""
        
        class ConcreteRenderer(CVRenderer):
            """Concrete implementation of CVRenderer."""
            
            def render(self, cv_data: Dict[str, Any], template_path: Path, output_path: Path) -> Path:
                return output_path
        
        renderer = ConcreteRenderer()
        result = renderer.render({}, Path("template.docx"), Path("output.docx"))
        assert isinstance(result, Path)
        assert result == Path("output.docx")

    def test_render_method_signature_accepts_all_parameters(self):
        """Test that render() accepts cv_data, template_path, and output_path."""
        
        class TestRenderer(CVRenderer):
            def render(self, cv_data: Dict[str, Any], template_path: Path, output_path: Path) -> Path:
                assert isinstance(cv_data, dict)
                assert isinstance(template_path, Path)
                assert isinstance(output_path, Path)
                return output_path
        
        renderer = TestRenderer()
        cv_data = {"identity": {"full_name": "John"}}
        template = Path("template.docx")
        output = Path("output.docx")
        
        result = renderer.render(cv_data, template, output)
        assert result == output

    def test_render_method_returns_path(self):
        """Test that render() returns a Path object."""
        
        class TestRenderer(CVRenderer):
            def render(self, cv_data: Dict[str, Any], template_path: Path, output_path: Path) -> Path:
                return output_path
        
        renderer = TestRenderer()
        result = renderer.render({}, Path("template.docx"), Path("output.docx"))
        assert isinstance(result, Path)

    def test_render_method_can_raise_file_not_found_for_template(self):
        """Test that render() can raise FileNotFoundError for missing template."""
        
        class TestRenderer(CVRenderer):
            def render(self, cv_data: Dict[str, Any], template_path: Path, output_path: Path) -> Path:
                if not template_path.exists():
                    raise FileNotFoundError(f"Template not found: {template_path}")
                return output_path
        
        renderer = TestRenderer()
        with pytest.raises(FileNotFoundError):
            renderer.render({}, Path("/nonexistent/template.docx"), Path("output.docx"))

    def test_render_method_can_raise_generic_exception(self):
        """Test that render() can raise generic Exception for rendering errors."""
        
        class TestRenderer(CVRenderer):
            def render(self, cv_data: Dict[str, Any], template_path: Path, output_path: Path) -> Path:
                raise Exception("Rendering failed")
        
        renderer = TestRenderer()
        with pytest.raises(Exception) as exc_info:
            renderer.render({}, Path("template.docx"), Path("output.docx"))
        assert "Rendering failed" in str(exc_info.value)

    def test_concrete_implementation_processes_cv_data(self):
        """Test concrete implementation can process cv_data parameter."""
        
        class DataAwareRenderer(CVRenderer):
            def render(self, cv_data: Dict[str, Any], template_path: Path, output_path: Path) -> Path:
                # Verify we can access cv_data structure
                if "identity" in cv_data:
                    full_name = cv_data["identity"].get("full_name", "Unknown")
                else:
                    full_name = "Unknown"
                
                return output_path
        
        renderer = DataAwareRenderer()
        cv_data = {
            "identity": {
                "full_name": "Jane Smith",
                "title": "Engineer"
            }
        }
        result = renderer.render(cv_data, Path("template.docx"), Path("output.docx"))
        assert result == Path("output.docx")

    def test_concrete_implementation_with_full_schema(self):
        """Test concrete implementation with full CV schema."""
        
        class FullRenderer(CVRenderer):
            def render(self, cv_data: Dict[str, Any], template_path: Path, output_path: Path) -> Path:
                # Verify full schema structure is accessible
                identity = cv_data.get("identity", {})
                sidebar = cv_data.get("sidebar", {})
                overview = cv_data.get("overview", "")
                experiences = cv_data.get("experiences", [])
                
                return output_path
        
        renderer = FullRenderer()
        cv_data = {
            "identity": {
                "title": "Senior Engineer",
                "full_name": "Alice Brown",
                "first_name": "Alice",
                "last_name": "Brown"
            },
            "sidebar": {
                "languages": ["Python"],
                "tools": ["Git"],
                "certifications": ["AWS"],
                "industries": ["Tech"],
                "spoken_languages": ["English"],
                "academic_background": ["BS CS"]
            },
            "overview": "Experienced engineer",
            "experiences": [
                {
                    "heading": "Engineer",
                    "description": "Built systems",
                    "bullets": ["Led team"],
                    "environment": ["Python"]
                }
            ]
        }
        result = renderer.render(cv_data, Path("template.docx"), Path("output.docx"))
        assert result == Path("output.docx")

    def test_multiple_renderers_can_coexist(self):
        """Test that multiple concrete renderers can be defined independently."""
        
        class DocxRenderer(CVRenderer):
            def render(self, cv_data: Dict[str, Any], template_path: Path, output_path: Path) -> Path:
                return output_path
        
        class PDFRenderer(CVRenderer):
            def render(self, cv_data: Dict[str, Any], template_path: Path, output_path: Path) -> Path:
                return output_path.with_suffix(".pdf")
        
        docx = DocxRenderer()
        pdf = PDFRenderer()
        
        result_docx = docx.render({}, Path("template.docx"), Path("output.docx"))
        result_pdf = pdf.render({}, Path("template.pdf"), Path("output"))
        
        assert result_docx.suffix == ".docx"
        assert result_pdf.suffix == ".pdf"

    def test_render_creates_output_path_object(self):
        """Test that render() can create and return new Path objects."""
        
        class PathCreatorRenderer(CVRenderer):
            def render(self, cv_data: Dict[str, Any], template_path: Path, output_path: Path) -> Path:
                # Create output directory if needed and return path
                return Path(output_path.parent) / output_path.name
        
        renderer = PathCreatorRenderer()
        result = renderer.render({}, Path("template.docx"), Path("output/result.docx"))
        
        assert isinstance(result, Path)
        assert result.name == "result.docx"

    def test_render_with_empty_cv_data(self):
        """Test that render() can handle empty cv_data."""
        
        class TestRenderer(CVRenderer):
            def render(self, cv_data: Dict[str, Any], template_path: Path, output_path: Path) -> Path:
                # Should handle empty dict gracefully
                if not cv_data:
                    return output_path
                return output_path
        
        renderer = TestRenderer()
        result = renderer.render({}, Path("template.docx"), Path("output.docx"))
        assert result == Path("output.docx")

    def test_render_method_override_works(self):
        """Test that render() method can be properly overridden."""
        
        class BaseRenderer(CVRenderer):
            def render(self, cv_data: Dict[str, Any], template_path: Path, output_path: Path) -> Path:
                return output_path
        
        class DerivedRenderer(BaseRenderer):
            def render(self, cv_data: Dict[str, Any], template_path: Path, output_path: Path) -> Path:
                # Call parent and potentially modify
                return Path(str(super().render(cv_data, template_path, output_path)).replace(".docx", "_derived.docx"))
        
        renderer = DerivedRenderer()
        result = renderer.render({}, Path("template.docx"), Path("output.docx"))
        assert "_derived" in str(result)

    def test_is_abstract_base_class(self):
        """Test that CVRenderer is an abstract base class."""
        from abc import ABC
        assert issubclass(CVRenderer, ABC)

    def test_render_is_abstractmethod(self):
        """Test that render is marked as abstract."""
        from inspect import isabstract
        
        # Check that the class is abstract
        assert isabstract(CVRenderer)
        
        # Check that render method has abstractmethod marker
        assert hasattr(CVRenderer.render, "__isabstractmethod__")
        assert CVRenderer.render.__isabstractmethod__

    def test_render_can_handle_absolute_paths(self):
        """Test that render() can handle absolute paths."""
        
        class TestRenderer(CVRenderer):
            def render(self, cv_data: Dict[str, Any], template_path: Path, output_path: Path) -> Path:
                return output_path.resolve()
        
        renderer = TestRenderer()
        output = Path("/tmp/output.docx")
        result = renderer.render({}, Path("/tmp/template.docx"), output)
        
        assert isinstance(result, Path)
        assert str(result).startswith("/")

    def test_render_can_handle_relative_paths(self):
        """Test that render() can handle relative paths."""
        
        class TestRenderer(CVRenderer):
            def render(self, cv_data: Dict[str, Any], template_path: Path, output_path: Path) -> Path:
                return output_path
        
        renderer = TestRenderer()
        result = renderer.render({}, Path("templates/cv.docx"), Path("outputs/my_cv.docx"))
        
        assert str(result) == "outputs/my_cv.docx"

    def test_render_implementations_are_independent(self):
        """Test that different implementations don't interfere."""
        
        class Impl1(CVRenderer):
            def render(self, cv_data: Dict[str, Any], template_path: Path, output_path: Path) -> Path:
                return Path("format1.docx")
        
        class Impl2(CVRenderer):
            def render(self, cv_data: Dict[str, Any], template_path: Path, output_path: Path) -> Path:
                return Path("format2.docx")
        
        impl1 = Impl1()
        impl2 = Impl2()
        
        result1 = impl1.render({}, Path("x"), Path("x"))
        result2 = impl2.render({}, Path("x"), Path("x"))
        
        assert str(result1) == "format1.docx"
        assert str(result2) == "format2.docx"

    def test_render_with_mocked_implementation(self):
        """Test that render() works correctly when mocked."""
        
        class TestRenderer(CVRenderer):
            def render(self, cv_data: Dict[str, Any], template_path: Path, output_path: Path) -> Path:
                return output_path
        
        renderer = TestRenderer()
        with patch.object(renderer, "render") as mock_render:
            mock_render.return_value = Path("mocked.docx")
            result = renderer.render({}, Path("template.docx"), Path("output.docx"))
            
            assert result == Path("mocked.docx")
            mock_render.assert_called_once()
