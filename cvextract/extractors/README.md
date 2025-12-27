# CV Extractors

This module provides a pluggable architecture for extracting structured CV data from various source formats.

## Overview

The extractor architecture allows for interchangeable implementations of CV extraction, making it easy to:

- Add support for new document formats (PDF, HTML, etc.)
- Replace or customize extraction logic
- Test extraction logic in isolation
- Implement custom extraction pipelines

## Core Concepts

### CVExtractor Interface

The `CVExtractor` abstract base class defines the contract that all extractors must implement:

```python
from cvextract.extractors import CVExtractor
from pathlib import Path
from typing import Dict, Any

class CustomExtractor(CVExtractor):
    def extract(self, source: Path) -> Dict[str, Any]:
        # Your extraction logic here
        return {
            "identity": {...},
            "sidebar": {...},
            "overview": "...",
            "experiences": [...]
        }
```

### DocxCVExtractor

The `DocxCVExtractor` is the default implementation that extracts CV data from Microsoft Word `.docx` files:

```python
from cvextract.extractors import DocxCVExtractor
from pathlib import Path

extractor = DocxCVExtractor()
cv_data = extractor.extract(Path("path/to/cv.docx"))
```

## CV Data Schema

All extractors must return data conforming to the CV schema defined in `cv_schema.json`. The structure includes:

- **identity**: Personal information (title, full_name, first_name, last_name)
- **sidebar**: Categorized lists (languages, tools, certifications, industries, spoken_languages, academic_background)
- **overview**: Free-text overview section
- **experiences**: List of professional experience entries (heading, description, bullets, environment)

See `cv_schema.json` in the repository root for the complete JSON schema definition.

## Creating a Custom Extractor

To create a custom extractor:

1. Import the base class:
   ```python
   from cvextract.extractors.base import CVExtractor
   ```

2. Create your implementation:
   ```python
   class MyCustomExtractor(CVExtractor):
       def extract(self, source: Path) -> Dict[str, Any]:
           # Read and parse the source file
           # Extract the required fields
           # Return data matching the CV schema
           return {
               "identity": {...},
               "sidebar": {...},
               "overview": "...",
               "experiences": [...]
           }
   ```

3. Use your extractor:
   ```python
   extractor = MyCustomExtractor()
   cv_data = extractor.extract(Path("path/to/source"))
   ```

## Examples

### Using the Default DOCX Extractor

```python
from cvextract.extractors import DocxCVExtractor
from pathlib import Path
import json

# Create an extractor instance
extractor = DocxCVExtractor()

# Extract CV data
cv_data = extractor.extract(Path("consultant_cv.docx"))

# Work with the extracted data
print(cv_data["identity"]["full_name"])
print(f"Skills: {', '.join(cv_data['sidebar']['languages'])}")

# Save to JSON
with open("output.json", "w") as f:
    json.dump(cv_data, f, indent=2)
```

### Creating a Mock Extractor for Testing

```python
from cvextract.extractors.base import CVExtractor
from pathlib import Path

class MockCVExtractor(CVExtractor):
    def extract(self, source: Path) -> Dict[str, Any]:
        return {
            "identity": {
                "title": "Test Engineer",
                "full_name": "Test User",
                "first_name": "Test",
                "last_name": "User"
            },
            "sidebar": {
                "languages": ["Python", "Java"],
                "tools": ["Docker", "Kubernetes"],
                "industries": ["Technology"],
                "spoken_languages": ["English"],
                "academic_background": ["BS Computer Science"]
            },
            "overview": "Experienced software engineer...",
            "experiences": [
                {
                    "heading": "2020-Present | Senior Engineer",
                    "description": "Leading development...",
                    "bullets": ["Achievement 1", "Achievement 2"],
                    "environment": ["Python", "AWS"]
                }
            ]
        }

# Use in tests
extractor = MockCVExtractor()
test_data = extractor.extract(Path("any/path"))
```

## Integration with Existing Pipeline

The extractors integrate seamlessly with the existing pipeline through the `extract_cv_structure()` function in `pipeline_highlevel.py`, which uses `DocxCVExtractor` by default while maintaining backward compatibility.
