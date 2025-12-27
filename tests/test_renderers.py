"""Tests for CV renderer interfaces and implementations."""

import pytest
import json
from pathlib import Path
from cvextract.renderers import CVRenderer, DocxCVRenderer


class TestCVRendererInterface:
    """Tests for the CVRenderer abstract interface."""

    def test_cv_renderer_is_abstract(self):
        """CVRenderer cannot be instantiated directly."""
        with pytest.raises(TypeError):
            CVRenderer()

    def test_cv_renderer_requires_render_method(self):
        """Subclasses must implement the render method."""
        class IncompleteCVRenderer(CVRenderer):
            pass

        with pytest.raises(TypeError):
            IncompleteCVRenderer()


class TestDocxCVRenderer:
    """Tests for DocxCVRenderer implementation."""

    def test_docx_renderer_instantiation(self):
        """DocxCVRenderer can be instantiated."""
        renderer = DocxCVRenderer()
        assert isinstance(renderer, CVRenderer)
        assert isinstance(renderer, DocxCVRenderer)

    def test_render_raises_file_not_found_for_missing_template(self, tmp_path):
        """render() raises FileNotFoundError for non-existent template."""
        renderer = DocxCVRenderer()
        cv_data = {
            "identity": {
                "title": "Engineer",
                "full_name": "Test User",
                "first_name": "Test",
                "last_name": "User"
            },
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        with pytest.raises(FileNotFoundError):
            renderer.render(cv_data, Path("/nonexistent/template.docx"), tmp_path / "out.docx")

    def test_render_raises_value_error_for_non_docx_template(self, tmp_path):
        """render() raises ValueError for non-.docx template files."""
        renderer = DocxCVRenderer()
        txt_file = tmp_path / "template.txt"
        txt_file.write_text("test")
        cv_data = {
            "identity": {
                "title": "Engineer",
                "full_name": "Test User",
                "first_name": "Test",
                "last_name": "User"
            },
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        with pytest.raises(ValueError, match="must be a .docx file"):
            renderer.render(cv_data, txt_file, tmp_path / "out.docx")

    def test_docx_renderer_implements_cv_renderer(self):
        """DocxCVRenderer properly implements CVRenderer interface."""
        renderer = DocxCVRenderer()
        assert hasattr(renderer, "render")
        assert callable(renderer.render)


class TestRendererPluggability:
    """Tests for renderer pluggability and interchangeability."""

    def test_custom_renderer_can_be_created(self, tmp_path):
        """Custom renderers can be created by implementing CVRenderer."""
        
        class MockCVRenderer(CVRenderer):
            def __init__(self):
                self.last_render = None
            
            def render(self, cv_data, template_path, output_path):
                self.last_render = {
                    "cv_data": cv_data,
                    "template": template_path,
                    "output": output_path
                }
                # Create a mock output file
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text("Mock rendered content")
                return output_path

        renderer = MockCVRenderer()
        cv_data = {
            "identity": {
                "title": "Mock Title",
                "full_name": "Mock Name",
                "first_name": "Mock",
                "last_name": "Name"
            },
            "sidebar": {},
            "overview": "Mock overview",
            "experiences": []
        }
        output = renderer.render(cv_data, tmp_path / "template.docx", tmp_path / "output.docx")
        assert renderer.last_render["cv_data"] == cv_data
        assert output.exists()
        assert output.read_text() == "Mock rendered content"


class TestRendererWithExternalParameters:
    """Tests for passing template and data as external parameters."""

    def test_renderer_accepts_external_cv_data(self, tmp_path):
        """Renderer can accept CV data from external sources."""
        
        class MockCVRenderer(CVRenderer):
            def render(self, cv_data, template_path, output_path):
                # Verify data is passed correctly
                assert "identity" in cv_data
                assert "sidebar" in cv_data
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(json.dumps(cv_data))
                return output_path

        # Simulate external data source
        external_data = {
            "identity": {
                "title": "Senior Developer",
                "full_name": "Jane Doe",
                "first_name": "Jane",
                "last_name": "Doe"
            },
            "sidebar": {
                "languages": ["Python", "JavaScript"],
                "tools": ["Docker"],
                "industries": ["Tech"],
                "spoken_languages": ["English"],
                "academic_background": ["BS CS"]
            },
            "overview": "Experienced developer",
            "experiences": []
        }

        renderer = MockCVRenderer()
        output = renderer.render(external_data, tmp_path / "template.docx", tmp_path / "output.docx")
        
        # Verify output contains the external data
        rendered_data = json.loads(output.read_text())
        assert rendered_data["identity"]["full_name"] == "Jane Doe"
        assert "Python" in rendered_data["sidebar"]["languages"]

    def test_renderer_accepts_external_template_path(self, tmp_path):
        """Renderer can accept template path from external source."""
        
        class MockCVRenderer(CVRenderer):
            def render(self, cv_data, template_path, output_path):
                # Verify template path is passed correctly
                assert template_path.name == "custom_template.docx"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(f"Used template: {template_path}")
                return output_path

        cv_data = {
            "identity": {"title": "", "full_name": "", "first_name": "", "last_name": ""},
            "sidebar": {},
            "overview": "",
            "experiences": []
        }

        # Simulate external template path
        custom_template = tmp_path / "templates" / "custom_template.docx"

        renderer = MockCVRenderer()
        output = renderer.render(cv_data, custom_template, tmp_path / "output.docx")
        
        assert "custom_template.docx" in output.read_text()
