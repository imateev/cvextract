# CV Verifiers

This module provides a pluggable architecture for verifying structured CV data in various ways.

## Overview

The verifier architecture allows for interchangeable implementations of CV verification, making it easy to:

- Validate data against the JSON schema
- Check for completeness and data quality
- Compare data structures for roundtrip verification
- Implement custom validation rules
- Test verification logic in isolation

## Core Concepts

### CVVerifier Interface

The `CVVerifier` abstract base class defines the contract that all verifiers must implement:

```python
from cvextract.verifiers import CVVerifier
from cvextract.shared import VerificationResult
from typing import Dict, Any

class CustomVerifier(CVVerifier):
    def verify(self, **kwargs) -> VerificationResult:
        data = kwargs.get("data")
        if data is None:
            raise ValueError("CustomVerifier requires a 'data' parameter.")
        # Your verification logic here
        errors = []
        warnings = []
        # ... validate data ...
        return VerificationResult(ok=not errors, errors=errors, warnings=warnings)
```

### Available Verifiers

#### ExtractedDataVerifier

Validates completeness and basic structure of extracted CV data:

```python
from typing import Any, Dict
from cvextract.verifiers import ExtractedDataVerifier

verifier = ExtractedDataVerifier()
cv_data: Dict[str, Any] = {
    "identity": {"title": "...", "full_name": "...", ...},
    "sidebar": {...},
    "overview": "...",
    "experiences": [...]
}
result = verifier.verify(data=cv_data)
if result.ok:
    print("Data is valid!")
else:
    print(f"Errors: {result.errors}")
    print(f"Warnings: {result.warnings}")
```

#### CVSchemaVerifier

Validates CV data against the JSON schema defined in `cv_schema.json`:

```python
from typing import Any, Dict
from cvextract.verifiers import get_verifier
from pathlib import Path

# Use default schema location (cv_schema.json in contracts/ directory)
verifier = CVSchemaVerifier()

# Or specify custom schema path
verifier = CVSchemaVerifier(schema_path=Path("custom_schema.json"))

cv_data: Dict[str, Any] = {...}
result = verifier.verify(data=cv_data)
```

#### RoundtripVerifier

Compares two CV data structures for equivalence:

```python
from typing import Any, Dict
from cvextract.verifiers import get_verifier

verifier = get_verifier("roundtrip-verifier")
original_data: Dict[str, Any] = {...}
roundtrip_data: Dict[str, Any] = {...}

result = verifier.verify(data=original_data, target_data=roundtrip_data)
if result.ok:
    print("Data structures match!")
```

#### FileRoundtripVerifier

Compares two CV data JSON files:

```python
from cvextract.verifiers import get_verifier
from pathlib import Path

verifier = get_verifier("file-roundtrip-verifier")
source_file: Path = Path("original.json")
target_file: Path = Path("roundtrip.json")
result = verifier.verify(
    source_file=source_file,
    target_file=target_file
)
```

## CV Data Schema

All verifiers work with data conforming to the CV schema defined in `cv_schema.json`. The structure includes:

- **identity**: Personal information (title, full_name, first_name, last_name)
- **sidebar**: Categorized lists (languages, tools, certifications, industries, spoken_languages, academic_background)
- **overview**: Free-text overview section
- **experiences**: List of professional experience entries (heading, description, bullets, environment)

See `cv_schema.json` in the cvextract/contracts/ directory for the complete JSON schema definition.

## Creating a Custom Verifier

To create a custom verifier:

1. Import the base class:
   ```python
   from cvextract.verifiers import CVVerifier
   from cvextract.shared import VerificationResult
   ```

2. Create your implementation:
   ```python
   class EmailVerifier(CVVerifier):
       def verify(self, **kwargs) -> VerificationResult:
           data = kwargs.get("data")
           if data is None:
               raise ValueError("EmailVerifier requires a 'data' parameter.")
           errors = []
           # Check for email in identity
           identity = data.get("identity", {})
           if "email" not in identity:
               errors.append("identity missing email field")
           return VerificationResult(ok=not errors, errors=errors, warnings=[])
   ```

3. Use your verifier:
   ```python
   from typing import Any, Dict

   verifier = EmailVerifier()
   cv_data: Dict[str, Any] = {...}
   result = verifier.verify(data=cv_data)
   ```

## Passing Data from External Sources

The verifier architecture supports passing both source and target data as parameters:

### Example: Verifying External Data

```python
from typing import Any, Dict
from cvextract.verifiers import ExtractedDataVerifier
import json
from pathlib import Path

# Load CV data from external source
with open("external_cv.json", "r") as f:
    cv_data: Dict[str, Any] = json.load(f)

# Verify the externally sourced data
verifier = ExtractedDataVerifier()
result = verifier.verify(data=cv_data)
```

### Example: Comparing External Data Sources

```python
from typing import Any, Dict
from cvextract.verifiers import get_verifier
import json

# Load data from different sources
with open("source_cv.json", "r") as f:
    source_data: Dict[str, Any] = json.load(f)

with open("target_cv.json", "r") as f:
    target_data: Dict[str, Any] = json.load(f)

# Compare them
verifier = get_verifier("roundtrip-verifier")
result = verifier.verify(data=source_data, target_data=target_data)
```

## Integration with Existing Pipeline

The verifiers are now used directly throughout the codebase:

```python
# Use verifiers directly from cvextract.verifiers
from typing import Any, Dict
from cvextract.verifiers import ExtractedDataVerifier, get_verifier

cv_data: Dict[str, Any] = {...}

# Verify extracted CV data
data_result = get_verifier("private-internal-verifier").verify(data=cv_data)

# Compare two CV data structures
result = get_verifier("roundtrip-verifier").verify(data=original_data, target_data=roundtrip_data)
```

## Examples

### Using Multiple Verifiers

```python
from typing import Any, Dict
from cvextract.verifiers import get_verifier

cv_data: Dict[str, Any] = {...}

# First verify against schema
schema_verifier = CVSchemaVerifier()
schema_result = schema_verifier.verify(data=cv_data)

if schema_result.ok:
    # Then check for completeness
    data_verifier = ExtractedDataVerifier()
    data_result = data_verifier.verify(data=cv_data)
    
    if data_result.ok:
        print("Data is valid and complete!")
    else:
        print(f"Completeness issues: {data_result.warnings}")
```

### Roundtrip Verification

```python
from typing import Any, Dict
from cvextract.cli_config import RenderStage, UserConfig
from cvextract.extractors import DocxCVExtractor
from cvextract.renderers import DocxCVRenderer
from cvextract.shared import UnitOfWork
from cvextract.verifiers import get_verifier
from pathlib import Path
import json

# Extract original data
extractor = DocxCVExtractor()
json_path = Path("roundtrip.json")
extract_work = UnitOfWork(
    config=UserConfig(target_dir=Path(".")),
    input=Path("cv.docx"),
    output=json_path,
)
extractor.extract(extract_work)
original_data: Dict[str, Any] = json.loads(json_path.read_text(encoding="utf-8"))

# Render to new document
output_path = Path("output.docx")

config = UserConfig(
    target_dir=Path("."),
    render=RenderStage(template=Path("template.docx"), data=json_path, output=output_path),
)
work = UnitOfWork(config=config, input=json_path, output=output_path, initial_input=json_path)

renderer = DocxCVRenderer()
renderer.render(work)

# Extract from rendered document
roundtrip_json = Path("roundtrip_rendered.json")
roundtrip_work = UnitOfWork(
    config=UserConfig(target_dir=Path(".")),
    input=output_path,
    output=roundtrip_json,
)
extractor.extract(roundtrip_work)
roundtrip_data: Dict[str, Any] = json.loads(roundtrip_json.read_text(encoding="utf-8"))

# Verify they match
verifier = get_verifier("roundtrip-verifier")
result = verifier.verify(data=original_data, target_data=roundtrip_data)

if result.ok:
    print("Roundtrip successful!")
else:
    print(f"Differences found: {result.errors}")
```

### Creating a Mock Verifier for Testing

```python
from typing import Any, Dict
from cvextract.verifiers import CVVerifier
from cvextract.shared import VerificationResult

class AlwaysPassVerifier(CVVerifier):
    def verify(self, **kwargs) -> VerificationResult:
        return VerificationResult(ok=True, errors=[], warnings=[])

class AlwaysFailVerifier(CVVerifier):
    def verify(self, **kwargs) -> VerificationResult:
        return VerificationResult(
            ok=False,
            errors=["test error"],
            warnings=["test warning"]
        )

# Use in tests
pass_verifier = AlwaysPassVerifier()
assert pass_verifier.verify(data={}).ok is True

fail_verifier = AlwaysFailVerifier()
assert fail_verifier.verify(data={}).ok is False
```

## Module Organization

All verification-related code is organized in the `cvextract/verifiers/` directory:

```
cvextract/verifiers/
├── __init__.py              # Public API exports
├── base.py                  # CVVerifier abstract base class
├── data_verifier.py         # ExtractedDataVerifier implementation
├── comparison_verifier.py   # RoundtripVerifier and FileRoundtripVerifier
├── schema_verifier.py       # CVSchemaVerifier implementation
└── README.md                # This file
```

The module maintains a clean boundary with minimal public API surface through the `__all__` export in `__init__.py`.
