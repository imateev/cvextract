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

The `CVVerifier` abstract base class defines the contract that all verifiers must implement.
Verifiers read inputs from the `UnitOfWork` (typically `work.output` for single-input verifiers, and `work.input` + `work.output` for roundtrip comparisons):

```python
import json
from cvextract.cli_config import UserConfig
from cvextract.shared import StepName, UnitOfWork
from cvextract.verifiers import CVVerifier

class CustomVerifier(CVVerifier):
    def verify(self, work: UnitOfWork) -> UnitOfWork:
        with work.output.open("r", encoding="utf-8") as f:
            data = json.load(f)
        # Your verification logic here
        errors = []
        warnings = []
        # ... validate data ...
        return self._record(work, errors, warnings)
```

### Available Verifiers

#### ExtractedDataVerifier

Validates completeness and basic structure of extracted CV data:

```python
from pathlib import Path
from cvextract.cli_config import UserConfig
from cvextract.shared import StepName, UnitOfWork
from cvextract.verifiers import ExtractedDataVerifier

verifier = ExtractedDataVerifier()
cv_path = Path("cv.json")
work = UnitOfWork(config=UserConfig(target_dir=cv_path.parent), input=cv_path, output=cv_path)
work.current_step = StepName.Extract
work.ensure_step_status(StepName.Extract)
work.current_step = StepName.Extract
work.ensure_step_status(StepName.Extract)
result = verifier.verify(work)
status = result.step_states[StepName.Extract]
if not status.errors:
    print("Data is valid!")
else:
    print(f"Errors: {status.errors}")
    print(f"Warnings: {status.warnings}")
```

#### CVSchemaVerifier

Validates CV data against the JSON schema defined in `cv_schema.json`:

```python
from cvextract.verifiers import CVSchemaVerifier
from pathlib import Path
from cvextract.cli_config import UserConfig
from cvextract.shared import StepName, UnitOfWork

# Use default schema location (cv_schema.json in contracts/ directory)
verifier = CVSchemaVerifier()

# Or specify custom schema path
verifier = CVSchemaVerifier(schema_path=Path("custom_schema.json"))

cv_path = Path("cv.json")
work = UnitOfWork(config=UserConfig(target_dir=cv_path.parent), input=cv_path, output=cv_path)
work.current_step = StepName.Extract
work.ensure_step_status(StepName.Extract)
result = verifier.verify(work)
```

#### RoundtripVerifier

Compares two CV data structures for equivalence:

```python
from pathlib import Path
from cvextract.cli_config import UserConfig
from cvextract.shared import StepName, UnitOfWork
from cvextract.verifiers import get_verifier

verifier = get_verifier("roundtrip-verifier")
source_path = Path("source.json")
target_path = Path("roundtrip.json")
work = UnitOfWork(config=UserConfig(target_dir=source_path.parent), input=source_path, output=target_path)
work.current_step = StepName.RoundtripComparer
work.ensure_step_status(StepName.RoundtripComparer)
result = verifier.verify(work)
status = result.step_states[StepName.RoundtripComparer]
if not status.errors:
    print("Data structures match!")
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
   from cvextract.shared import StepName, UnitOfWork
   ```

2. Create your implementation:
   ```python
   class EmailVerifier(CVVerifier):
       def verify(self, work: UnitOfWork) -> UnitOfWork:
           with work.output.open("r", encoding="utf-8") as f:
               data = json.load(f)
           errors = []
           # Check for email in identity
           identity = data.get("identity", {})
           if "email" not in identity:
               errors.append("identity missing email field")
           return self._record(work, errors, [])
   ```

3. Use your verifier:
   ```python
   from pathlib import Path
   from cvextract.cli_config import UserConfig
   from cvextract.shared import StepName, UnitOfWork

   verifier = EmailVerifier()
   cv_path = Path("cv.json")
   work = UnitOfWork(config=UserConfig(target_dir=cv_path.parent), input=cv_path, output=cv_path)
   work.current_step = StepName.Extract
   work.ensure_step_status(StepName.Extract)
   result = verifier.verify(work)
   ```

## Passing Data from External Sources

The verifier architecture uses `UnitOfWork` paths for input and output:

### Example: Verifying External Data

```python
import json
from pathlib import Path
from cvextract.cli_config import UserConfig
from cvextract.shared import StepName, UnitOfWork
from cvextract.verifiers import ExtractedDataVerifier

# Verify the externally sourced data
cv_path = Path("external_cv.json")
work = UnitOfWork(config=UserConfig(target_dir=cv_path.parent), input=cv_path, output=cv_path)
work.current_step = StepName.Extract
work.ensure_step_status(StepName.Extract)
verifier = ExtractedDataVerifier()
result = verifier.verify(work)
```

### Example: Comparing External Data Sources

```python
from pathlib import Path
from cvextract.cli_config import UserConfig
from cvextract.shared import StepName, UnitOfWork
from cvextract.verifiers import get_verifier

# Compare them
verifier = get_verifier("roundtrip-verifier")
source_path = Path("source_cv.json")
target_path = Path("target_cv.json")
work = UnitOfWork(config=UserConfig(target_dir=source_path.parent), input=source_path, output=target_path)
work.current_step = StepName.RoundtripComparer
work.ensure_step_status(StepName.RoundtripComparer)
result = verifier.verify(work)
```

## Integration with Existing Pipeline

The verifiers are now used directly throughout the codebase:

```python
# Use verifiers directly from cvextract.verifiers
from pathlib import Path
from cvextract.cli_config import UserConfig
from cvextract.shared import StepName, UnitOfWork
from cvextract.verifiers import CVSchemaVerifier, ExtractedDataVerifier, get_verifier

cv_path = Path("cv.json")
work = UnitOfWork(config=UserConfig(target_dir=cv_path.parent), input=cv_path, output=cv_path)
work.current_step = StepName.Extract
work.ensure_step_status(StepName.Extract)

# Verify extracted CV data
data_result = get_verifier("private-internal-verifier").verify(work)

# Compare two CV data structures
source_path = Path("source_cv.json")
target_path = Path("target_cv.json")
compare_work = UnitOfWork(config=UserConfig(target_dir=source_path.parent), input=source_path, output=target_path)
compare_work.current_step = StepName.RoundtripComparer
compare_work.ensure_step_status(StepName.RoundtripComparer)
result = get_verifier("roundtrip-verifier").verify(compare_work)
```

## Examples

### Using Multiple Verifiers

```python
from cvextract.verifiers import CVSchemaVerifier, ExtractedDataVerifier
from pathlib import Path
from cvextract.cli_config import UserConfig
from cvextract.shared import StepName, UnitOfWork

# First verify against schema
schema_verifier = CVSchemaVerifier()
cv_path = Path("cv.json")
work = UnitOfWork(config=UserConfig(target_dir=cv_path.parent), input=cv_path, output=cv_path)
work.current_step = StepName.Extract
work.ensure_step_status(StepName.Extract)
schema_result = schema_verifier.verify(work)

schema_status = schema_result.step_states[StepName.Extract]
if not schema_status.errors:
    # Then check for completeness
    data_verifier = ExtractedDataVerifier()
    data_result = data_verifier.verify(work)
    
    data_status = data_result.step_states[StepName.Extract]
    if not data_status.errors:
        print("Data is valid and complete!")
    else:
        print(f"Completeness issues: {data_status.warnings}")
```

### Roundtrip Verification

```python
from cvextract.cli_config import RenderStage, UserConfig
from cvextract.extractors import DocxCVExtractor
from cvextract.renderers import DocxCVRenderer
from cvextract.shared import StepName, UnitOfWork
from cvextract.verifiers import get_verifier
from pathlib import Path

# Extract original data
extractor = DocxCVExtractor()
json_path = Path("roundtrip.json")
extract_work = UnitOfWork(
    config=UserConfig(target_dir=Path(".")),
    input=Path("cv.docx"),
    output=json_path,
)
extractor.extract(extract_work)

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

# Verify they match
verifier = get_verifier("roundtrip-verifier")
compare_work = UnitOfWork(
    config=UserConfig(target_dir=Path(".")),
    input=json_path,
    output=roundtrip_json,
)
compare_work.current_step = StepName.RoundtripComparer
compare_work.ensure_step_status(StepName.RoundtripComparer)
result = verifier.verify(compare_work)
status = result.step_states[StepName.RoundtripComparer]

if not status.errors:
    print("Roundtrip successful!")
else:
    print(f"Differences found: {result.errors}")
```

### Creating a Mock Verifier for Testing

```python
from pathlib import Path
from cvextract.cli_config import UserConfig
from cvextract.verifiers import CVVerifier
from cvextract.shared import StepName, UnitOfWork

class AlwaysPassVerifier(CVVerifier):
    def verify(self, work: UnitOfWork) -> UnitOfWork:
        return self._record(work, [], [])

class AlwaysFailVerifier(CVVerifier):
    def verify(self, work: UnitOfWork) -> UnitOfWork:
        return self._record(
            work,
            ["test error"],
            ["test warning"],
        )

# Use in tests
pass_verifier = AlwaysPassVerifier()
work = UnitOfWork(
    config=UserConfig(target_dir=Path(".")),
    input=Path("input.json"),
    output=Path("output.json"),
)
work.current_step = StepName.Extract
work.ensure_step_status(StepName.Extract)
assert pass_verifier.verify(work).step_states[StepName.Extract].errors == []

fail_verifier = AlwaysFailVerifier()
status = fail_verifier.verify(work).step_states[StepName.Extract]
assert "test error" in status.errors
```

## Module Organization

All verification-related code is organized in the `cvextract/verifiers/` directory:

```
cvextract/verifiers/
├── __init__.py              # Public API exports
├── base.py                  # CVVerifier abstract base class
├── default_expected_cv_data_verifier.py         # ExtractedDataVerifier implementation
├── roundtrip_verifier.py   # RoundtripVerifier implementation
├── default_cv_schema_verifier.py       # CVSchemaVerifier implementation
└── README.md                # This file
```

The module maintains a clean boundary with minimal public API surface through the `__all__` export in `__init__.py`.
