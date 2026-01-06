# DOCX Renderer

## Overview

The DOCX renderer transforms structured CV JSON data into formatted Microsoft Word documents using Jinja2 templates via the docxtpl library.

## Status

**Active** - Primary rendering implementation

## Description

The `DocxCVRenderer` class:
1. Loads a Jinja2-enabled DOCX template file
2. Renders CV JSON data into the template
3. Handles XML sanitization for special characters
4. Outputs a formatted DOCX file

## Entry Points

### Programmatic API

```python
from cvextract.renderers import DocxCVRenderer
from pathlib import Path
import json

# Load CV data
with open("cv.json", "r") as f:
    cv_data = json.load(f)

# Render
renderer = DocxCVRenderer()
output_path = renderer.render(
    cv_data,
    template_path=Path("template.docx"),
    output_path=Path("output/cv_NEW.docx")
)
```

### CLI Usage

```bash
# Extract and render (chained)
python -m cvextract.cli \
  --extract source=cv.docx \
  --render template=template.docx \
  --target output/

# Apply only (from existing JSON)
python -m cvextract.cli \
  --render template=template.docx data=cv.json \
  --target output/
```

## Configuration

### CLI Parameters

- `template=<path>`: Template DOCX file (required)
- `data=<path>`: Input JSON file (optional when chained after extract/adjust)
- `output=<path>`: Output DOCX path (optional, defaults to `{target}/documents/`)

### Template Requirements

Templates must be valid DOCX files with Jinja2 syntax:
- Variables: `{{ identity.full_name }}`
- Loops: `{% for exp in experiences %}...{% endfor %}`
- Filters: `{{ sidebar.languages|join(', ') }}`

## Interfaces

### Input

- **CV Data**: JSON conforming to `cvextract/contracts/cv_schema.json`
- **Template**: DOCX file with Jinja2 template syntax

### Output

- **Rendered DOCX**: Formatted Word document with data populated

### Template Variables

```jinja2
{{ identity.title }}
{{ identity.full_name }}
{{ identity.first_name }}
{{ identity.last_name }}

{{ sidebar.languages|join(', ') }}
{{ sidebar.tools|join(', ') }}
{{ sidebar.certifications|join(', ') }}
{{ sidebar.industries|join(', ') }}
{{ sidebar.spoken_languages|join(', ') }}
{{ sidebar.academic_background|join(', ') }}

{{ overview }}

{% for experience in experiences %}
  {{ experience.heading }}
  {{ experience.description }}
  {% for bullet in experience.bullets %}
    {{ bullet }}
  {% endfor %}
  {{ experience.environment|join(', ') }}
{% endfor %}
```

## Dependencies

### Internal Dependencies

- `cvextract.renderers.base.CVRenderer` - Abstract base class
- `cvextract.contracts.cv_schema.json` - Input data schema

### External Dependencies

- `docxtpl` - Jinja2 template rendering for DOCX
- `python-docx` - DOCX file manipulation

### Integration Points

- Used by `cvextract.pipeline_highlevel.render_cv_data()`
- Used by `cvextract.cli_execute.execute_pipeline()` for render stage
- Templates in `examples/templates/CV_Template_Jinja2.docx`

## Test Coverage

Tested in:
- `tests/test_docx_renderer.py` - Unit tests
- `tests/test_renderers.py` - Integration tests
- `tests/test_pipeline.py` - End-to-end rendering

## Implementation History

The DOCX renderer was part of the initial implementation, later refactored into a pluggable architecture.

**Key Files**:
- `cvextract/renderers/docx_renderer.py` - Implementation
- `cvextract/renderers/base.py` - Base class
- `examples/templates/CV_Template_Jinja2.docx` - Sample template

## Open Questions

1. **Multi-Template**: Should we support rendering to multiple templates in one operation?
2. **Conditional Sections**: Should we add helper functions for conditional rendering?
3. **Styling**: Should we provide pre-built style libraries?

## XML Sanitization

The renderer sanitizes text to be XML-safe:
- Handles raw ampersands (`&` → `&amp;`)
- Removes invalid XML 1.0 characters
- Preserves non-breaking spaces and other valid entities
- Uses docxtpl's auto-escaping

## File Paths

- Implementation: `cvextract/renderers/docx_renderer.py`
- Base Class: `cvextract/renderers/base.py`
- Sample Template: `examples/templates/CV_Template_Jinja2.docx`
- Template Guide: `examples/templates/TEMPLATE_GUIDE.md`
- Tests: `tests/test_docx_renderer.py`

## Related Documentation

- [Rendering Architecture](../README.md)
- [Pluggable Renderer Architecture](../pluggable-renderer-architecture/README.md)
- [Templating System](../../templates/templating-system/README.md)
- Module README: `cvextract/renderers/README.md`
- Template Guide: `examples/templates/TEMPLATE_GUIDE.md`
