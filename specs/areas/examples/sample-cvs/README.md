# Sample CVs

## Overview

Sample CVs provide realistic example CV files for testing, demonstration, and learning how cvextract works.

## Status

**Active** - Production test data

## Description

Included sample CVs:
1. **Sarah_Connor_CV.docx**: Standard professional CV
2. **T800_Model_101_CV.docx**: Technical specialist CV
3. **Luke_Reese_CV.docx**: Multi-experience CV

Features:
- Realistic content and structure
- Various experience levels and formats
- Test coverage for different CV patterns
- Production-quality formatting

## Entry Points

### Sample Locations

```
examples/cvs/
├── Sarah_Connor_CV.docx
├── T800_Model_101_CV.docx
└── Luke_Reese_CV.docx
```

### Usage in Examples

```bash
# Extract sample CV
python -m cvextract.cli \
  --extract source=examples/cvs/Sarah_Connor_CV.docx \
  --target output/

# Full pipeline with sample
python -m cvextract.cli \
  --extract source=examples/cvs/Sarah_Connor_CV.docx \
  --render template=examples/templates/CV_Template_Jinja2.docx \
  --target output/

# Batch process all samples
python -m cvextract.cli \
  --extract source=examples/cvs \
  --render template=examples/templates/CV_Template_Jinja2.docx \
  --target output/
```

### Testing

```python
# In tests
from cvextract.cli_config import UserConfig
from cvextract.shared import StepName, UnitOfWork
from pathlib import Path
import json

sample_cv = Path("examples/cvs/Sarah_Connor_CV.docx")
work = UnitOfWork(config=UserConfig(target_dir=Path("outputs")))
work.set_step_paths(
    StepName.Extract,
    input_path=sample_cv,
    output_path=Path("outputs/Sarah_Connor_CV.json"),
)
extractor.extract(work)
output_path = work.get_step_output(StepName.Extract)
result = json.loads(output_path.read_text(encoding="utf-8"))
assert result["identity"]["full_name"] == "Sarah Connor"
```

## Sample Descriptions

### Sarah_Connor_CV.docx

- **Profile**: Technology leader and systems engineer
- **Experience**: Military and technology background
- **Skills**: Leadership, systems engineering, tactical planning
- **Structure**: Standard format with overview and multiple experiences
- **Use Case**: Basic extraction and rendering tests

### T800_Model_101_CV.docx

- **Profile**: Technical specialist with precision focus
- **Experience**: Security and protection services
- **Skills**: Technical proficiency, reliability, persistence
- **Structure**: Technical CV with detailed skills
- **Use Case**: Technical role extraction tests

### Luke_Reese_CV.docx

- **Profile**: Security and intelligence professional
- **Experience**: Military and private sector
- **Skills**: Intelligence analysis, security operations
- **Structure**: Multi-organization career path
- **Use Case**: Complex experience structure tests

## Configuration

### Expected Structure

All sample CVs follow the expected DOCX structure:
- Header with identity and sidebar information
- "OVERVIEW" section with professional summary
- "PROFESSIONAL EXPERIENCE" section with entries
- Date-range headings for experiences
- Bullet points for achievements
- Optional environment/technology tags

### Data Quality

Samples demonstrate:
- Complete identity information
- Populated sidebar categories
- Substantive overview text
- Multiple experience entries
- Bullet point achievements
- Technology/environment tags

## Interfaces

### Input Format

- Microsoft Word `.docx` (Office Open XML)
- Structure expected by `DocxCVExtractor`
- Template-compatible content

### Output When Extracted

JSON conforming to `cv_schema.json` with:
- All identity fields populated
- All sidebar categories with content
- Overview text
- Multiple experiences with bullets

## Dependencies

### Internal Dependencies

- Used by test suites
- Referenced in README
- Used in documentation examples

### Integration Points

- Test data for `tests/test_extractors.py`
- Test data for `tests/test_pipeline.py`
- Examples in main README
- Template testing

## Test Coverage

Used in:
- `tests/test_docx_extractor.py` - Basic extraction
- `tests/test_pipeline.py` - Full pipeline
- `tests/test_renderers.py` - Rendering
- README example commands

## Implementation History

Sample CVs were created to:
- Provide realistic test data
- Enable automated testing
- Demonstrate features in README
- Support user learning

Content is fictional but realistic, using pop culture names for memorability.

**Key Files**:
- `examples/cvs/Sarah_Connor_CV.docx`
- `examples/cvs/T800_Model_101_CV.docx`
- `examples/cvs/Luke_Reese_CV.docx`

## Adding New Samples

### Creating a Sample CV

1. **Start with Template**: Copy existing sample
2. **Modify Content**: Change name, experience, skills
3. **Maintain Structure**: Keep expected sections and format
4. **Test Extraction**:
   ```bash
   python -m cvextract.cli \
     --extract source=examples/cvs/new_sample.docx \
     --target test/
   ```
5. **Verify JSON**: Check extracted data quality
6. **Add to Tests**: Include in test suite if representative

### Quality Standards

- [ ] Realistic content (no placeholder text)
- [ ] Complete identity information
- [ ] Populated sidebar (3+ items per category)
- [ ] Substantive overview (100+ words)
- [ ] 2+ experience entries
- [ ] 3+ bullets per experience
- [ ] Proper date formats in headings
- [ ] Environment tags (optional but recommended)
- [ ] Extracts without errors
- [ ] Renders cleanly to templates

## File Paths

- Samples: `examples/cvs/*.docx`
- Tests: `tests/test_extractors.py`, `tests/test_pipeline.py`
- Documentation: Main README.md examples

## Related Documentation

- [Examples Architecture](../README.md)
- [Documentation](../documentation/README.md)
- [Private Internal Extractor](../../extraction/private-internal-extractor/README.md)
- Main README: Examples sections
