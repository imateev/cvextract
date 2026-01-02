"""
Tests for CVExtractor abstract base class.

Tests that the abstract interface is properly defined and enforces
correct implementation patterns for concrete extractors.
"""

from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pytest

from cvextract.extractors.base import CVExtractor


class TestCVExtractorAbstract:
    """Tests for CVExtractor abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that CVExtractor cannot be instantiated directly."""
        with pytest.raises(TypeError) as exc_info:
            CVExtractor()
        assert "abstract" in str(exc_info.value).lower()

    def test_extract_method_must_be_implemented(self):
        """Test that extract() is an abstract method requiring implementation."""
        
        class IncompleteExtractor(CVExtractor):
            """Extractor missing extract() implementation."""
            pass
        
        with pytest.raises(TypeError):
            IncompleteExtractor()

    def test_extract_method_can_be_implemented(self):
        """Test that extract() can be properly implemented in concrete class."""
        
        class ConcreteExtractor(CVExtractor):
            """Concrete implementation of CVExtractor."""
            
            def extract(self, source: Path) -> Dict[str, Any]:
                return {"identity": {}}
        
        extractor = ConcreteExtractor()
        result = extractor.extract(Path("dummy.docx"))
        assert isinstance(result, dict)
        assert "identity" in result

    def test_extract_method_signature_accepts_path(self):
        """Test that extract() accepts a Path argument."""
        
        class TestExtractor(CVExtractor):
            def extract(self, source: Path) -> Dict[str, Any]:
                assert isinstance(source, Path)
                return {}
        
        extractor = TestExtractor()
        test_path = Path("test.docx")
        extractor.extract(test_path)

    def test_extract_method_returns_dict(self):
        """Test that extract() returns a dictionary."""
        
        class TestExtractor(CVExtractor):
            def extract(self, source: Path) -> Dict[str, Any]:
                return {"identity": {"full_name": "John Doe"}}
        
        extractor = TestExtractor()
        result = extractor.extract(Path("test.docx"))
        assert isinstance(result, dict)

    def test_extract_method_can_raise_file_not_found(self):
        """Test that extract() can raise FileNotFoundError."""
        
        class TestExtractor(CVExtractor):
            def extract(self, source: Path) -> Dict[str, Any]:
                if not source.exists():
                    raise FileNotFoundError(f"File not found: {source}")
                return {}
        
        extractor = TestExtractor()
        non_existent = Path("/path/that/does/not/exist.docx")
        
        with pytest.raises(FileNotFoundError):
            extractor.extract(non_existent)

    def test_extract_method_can_raise_generic_exception(self):
        """Test that extract() can raise generic Exception for extraction errors."""
        
        class TestExtractor(CVExtractor):
            def extract(self, source: Path) -> Dict[str, Any]:
                raise Exception("Extraction failed")
        
        extractor = TestExtractor()
        with pytest.raises(Exception) as exc_info:
            extractor.extract(Path("test.docx"))
        assert "Extraction failed" in str(exc_info.value)

    def test_concrete_implementation_with_full_schema(self):
        """Test concrete implementation returning full CV schema structure."""
        
        class FullExtractor(CVExtractor):
            def extract(self, source: Path) -> Dict[str, Any]:
                return {
                    "identity": {
                        "title": "Senior Developer",
                        "full_name": "Jane Smith",
                        "first_name": "Jane",
                        "last_name": "Smith"
                    },
                    "sidebar": {
                        "languages": ["Python", "JavaScript"],
                        "tools": ["Git", "Docker"],
                        "certifications": ["AWS"],
                        "industries": ["Tech"],
                        "spoken_languages": ["English", "French"],
                        "academic_background": ["BS Computer Science"]
                    },
                    "overview": "Experienced developer",
                    "experiences": [
                        {
                            "heading": "Software Engineer",
                            "description": "Built systems",
                            "bullets": ["Led team"],
                            "environment": ["Python", "AWS"]
                        }
                    ]
                }
        
        extractor = FullExtractor()
        result = extractor.extract(Path("cv.docx"))
        
        assert result["identity"]["full_name"] == "Jane Smith"
        assert len(result["sidebar"]["languages"]) == 2
        assert len(result["experiences"]) == 1
        assert result["experiences"][0]["heading"] == "Software Engineer"

    def test_multiple_extractors_can_coexist(self):
        """Test that multiple concrete extractors can be defined independently."""
        
        class DocxExtractor(CVExtractor):
            def extract(self, source: Path) -> Dict[str, Any]:
                return {"format": "docx"}
        
        class PDFExtractor(CVExtractor):
            def extract(self, source: Path) -> Dict[str, Any]:
                return {"format": "pdf"}
        
        docx = DocxExtractor()
        pdf = PDFExtractor()
        
        assert docx.extract(Path("test.docx"))["format"] == "docx"
        assert pdf.extract(Path("test.pdf"))["format"] == "pdf"

    def test_extract_method_can_process_source_path(self):
        """Test that concrete implementation can process the source path."""
        
        class PathAwareExtractor(CVExtractor):
            def extract(self, source: Path) -> Dict[str, Any]:
                return {
                    "source_file": source.name,
                    "source_stem": source.stem,
                    "source_suffix": source.suffix
                }
        
        extractor = PathAwareExtractor()
        result = extractor.extract(Path("my_cv.docx"))
        
        assert result["source_file"] == "my_cv.docx"
        assert result["source_stem"] == "my_cv"
        assert result["source_suffix"] == ".docx"

    def test_extract_with_empty_dict_return(self):
        """Test that extract() can return empty dictionary."""
        
        class EmptyExtractor(CVExtractor):
            def extract(self, source: Path) -> Dict[str, Any]:
                return {}
        
        extractor = EmptyExtractor()
        result = extractor.extract(Path("test.docx"))
        assert result == {}

    def test_extract_method_override_works(self):
        """Test that extract() method can be properly overridden."""
        
        class BaseExtractor(CVExtractor):
            def extract(self, source: Path) -> Dict[str, Any]:
                return {"version": 1}
        
        class DerivedExtractor(BaseExtractor):
            def extract(self, source: Path) -> Dict[str, Any]:
                base_result = super().extract(source)
                base_result["version"] = 2
                return base_result
        
        extractor = DerivedExtractor()
        result = extractor.extract(Path("test.docx"))
        assert result["version"] == 2

    def test_is_abstract_base_class(self):
        """Test that CVExtractor is an abstract base class."""
        from abc import ABC
        assert issubclass(CVExtractor, ABC)

    def test_extract_is_abstractmethod(self):
        """Test that extract is marked as abstract."""
        from inspect import isabstract
        from abc import abstractmethod
        
        # Check that the class is abstract
        assert isabstract(CVExtractor)
        
        # Check that extract method has abstractmethod marker
        assert hasattr(CVExtractor.extract, "__isabstractmethod__")
        assert CVExtractor.extract.__isabstractmethod__

    def test_extract_can_handle_path_with_spaces(self):
        """Test that extract() can handle paths with spaces."""
        
        class TestExtractor(CVExtractor):
            def extract(self, source: Path) -> Dict[str, Any]:
                return {"filename": source.name}
        
        extractor = TestExtractor()
        result = extractor.extract(Path("My CV File.docx"))
        assert result["filename"] == "My CV File.docx"

    def test_concrete_implementations_are_independent(self):
        """Test that different implementations don't interfere."""
        
        class Impl1(CVExtractor):
            def extract(self, source: Path) -> Dict[str, Any]:
                return {"impl": 1}
        
        class Impl2(CVExtractor):
            def extract(self, source: Path) -> Dict[str, Any]:
                return {"impl": 2}
        
        impl1 = Impl1()
        impl2 = Impl2()
        
        assert impl1.extract(Path("x"))["impl"] == 1
        assert impl2.extract(Path("x"))["impl"] == 2
        assert impl1.extract(Path("x"))["impl"] == 1  # Verify not changed

    def test_extract_with_mocked_implementation(self):
        """Test that extract() works correctly when mocked."""
        
        class TestExtractor(CVExtractor):
            def extract(self, source: Path) -> Dict[str, Any]:
                return {"extracted": True}
        
        extractor = TestExtractor()
        with patch.object(extractor, "extract") as mock_extract:
            mock_extract.return_value = {"mocked": True}
            result = extractor.extract(Path("test.docx"))
            assert result["mocked"] is True
            mock_extract.assert_called_once()
