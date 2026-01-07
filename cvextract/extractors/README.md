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
from cvextract.shared import UnitOfWork

class CustomExtractor(CVExtractor):
    def extract(self, work: UnitOfWork) -> UnitOfWork:
        # Your extraction logic here
        data = {
            "identity": {...},
            "sidebar": {...},
            "overview": "...",
            "experiences": [...]
        }
        return self._write_output_json(work, data)
```

### DocxCVExtractor

The `DocxCVExtractor` is the default implementation that extracts CV data from Microsoft Word `.docx` files:

```python
from cvextract.cli_config import UserConfig
from cvextract.extractors import DocxCVExtractor
from cvextract.shared import UnitOfWork
from pathlib import Path
import json

extractor = DocxCVExtractor()
work = UnitOfWork(
    config=UserConfig(target_dir=Path("outputs")),
    input=Path("path/to/cv.docx"),
    output=Path("outputs/cv.json"),
)
extractor.extract(work)
cv_data = json.loads(work.output.read_text(encoding="utf-8"))
```

## CV Data Schema

All extractors must write data conforming to the CV schema defined in `cv_schema.json`. The structure includes:

- **identity**: Personal information (title, full_name, first_name, last_name)
- **sidebar**: Categorized lists (languages, tools, certifications, industries, spoken_languages, academic_background)
- **overview**: Free-text overview section
- **experiences**: List of professional experience entries (heading, description, bullets, environment)

See `cv_schema.json` in the cvextract/contracts/ directory for the complete JSON schema definition.

## Creating a Custom Extractor

To create a custom extractor:

1. Import the base class:
   ```python
   from cvextract.extractors import CVExtractor
   from cvextract.shared import UnitOfWork
   ```

2. Create your implementation:
   ```python
   class MyCustomExtractor(CVExtractor):
       def extract(self, work: UnitOfWork) -> UnitOfWork:
           # Read and parse the source file
           # Extract the required fields
           data = {
               "identity": {...},
               "sidebar": {...},
               "overview": "...",
               "experiences": [...]
           }
           return self._write_output_json(work, data)
   ```

3. Use your extractor:
   ```python
   from cvextract.cli_config import UserConfig
   from pathlib import Path

   extractor = MyCustomExtractor()
   work = UnitOfWork(
       config=UserConfig(target_dir=Path("outputs")),
       input=Path("path/to/source"),
       output=Path("outputs/source.json"),
   )
   extractor.extract(work)
   ```

## Examples

### Using the Default DOCX Extractor

```python
from cvextract.cli_config import UserConfig
from cvextract.extractors import DocxCVExtractor
from cvextract.shared import UnitOfWork
from pathlib import Path
import json

# Create an extractor instance
extractor = DocxCVExtractor()

# Extract CV data
work = UnitOfWork(
    config=UserConfig(target_dir=Path("outputs")),
    input=Path("consultant_cv.docx"),
    output=Path("outputs/consultant_cv.json"),
)
extractor.extract(work)
cv_data = json.loads(work.output.read_text(encoding="utf-8"))

# Work with the extracted data
print(cv_data["identity"]["full_name"])
print(f"Skills: {', '.join(cv_data['sidebar']['languages'])}")

# Save to JSON
with open("output.json", "w") as f:
    json.dump(cv_data, f, indent=2)
```

### Creating a Mock Extractor for Testing

```python
from cvextract.cli_config import UserConfig
from cvextract.extractors import CVExtractor
from cvextract.shared import UnitOfWork
from pathlib import Path
import json

class MockCVExtractor(CVExtractor):
    def extract(self, work: UnitOfWork) -> UnitOfWork:
        data = {
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
        return self._write_output_json(work, data)

# Use in tests
extractor = MockCVExtractor()
work = UnitOfWork(
    config=UserConfig(target_dir=Path("outputs")),
    input=Path("any/path"),
    output=Path("outputs/mock.json"),
)
extractor.extract(work)
test_data = json.loads(work.output.read_text(encoding="utf-8"))
```

## Integration with Existing Pipeline

The extractors integrate seamlessly with the existing pipeline through the `extract_cv_data()` function in `pipeline_helpers.py`, which uses `DocxCVExtractor` by default and expects a `UnitOfWork`.
