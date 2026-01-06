# Templating System

## Overview

The templating system enables data-driven CV rendering using Jinja2 templates embedded in Microsoft Word DOCX files.

## Status

**Active** - Core rendering capability

## Description

The system provides:
1. **Jinja2 Integration**: Full Jinja2 template syntax in DOCX files
2. **Variable Substitution**: `{{ variable }}` syntax for data insertion
3. **Control Flow**: `{% for %}`, `{% if %}` for dynamic content
4. **Filters**: `|join`, `|default` for data transformation
5. **WYSIWYG Editing**: Templates created/edited in Microsoft Word

## Entry Points

### Template Creation

1. Open Microsoft Word
2. Create document layout with styles
3. Insert Jinja2 expressions where data should appear
4. Save as `.docx`

### Template Usage

```bash
python -m cvextract.cli \
  --extract source=cv.docx \
  --render template=my_template.docx \
  --target output/
```

### Programmatic Rendering

```python
from cvextract.cli_config import RenderStage, UserConfig
from cvextract.renderers import DocxCVRenderer
from cvextract.shared import UnitOfWork
from pathlib import Path
import json

with open("cv.json") as f:
    cv_data = json.load(f)

renderer = DocxCVRenderer()
json_path = Path("cv.json")
json_path.write_text(json.dumps(cv_data, indent=2), encoding="utf-8")
output_path = Path("output.docx")

config = UserConfig(
    target_dir=Path("."),
    render=RenderStage(template=Path("template.docx"), data=json_path, output=output_path),
)
work = UnitOfWork(config=config, input=json_path, output=output_path, initial_input=json_path)
renderer.render(work)
```

## Configuration

### Template Syntax

**Variables**:
```jinja2
{{ identity.full_name }}
{{ identity.title }}
{{ overview }}
```

**Lists (joined)**:
```jinja2
{{ sidebar.languages|join(', ') }}
{{ sidebar.tools|join(', ') }}
```

**Loops**:
```jinja2
{% for experience in experiences %}
  {{ experience.heading }}
  {{ experience.description }}
  
  {% for bullet in experience.bullets %}
    • {{ bullet }}
  {% endfor %}
  
  Environment: {{ experience.environment|join(', ') }}
{% endfor %}
```

**Conditionals**:
```jinja2
{% if identity.title %}
  Title: {{ identity.title }}
{% endif %}

{% if experience.environment %}
  Tech: {{ experience.environment|join(', ') }}
{% endif %}
```

**Filters**:
```jinja2
{{ sidebar.languages|join(', ') }}           # Join list with comma
{{ sidebar.tools|join(' | ') }}              # Custom separator
{{ identity.title|default('Engineer') }}     # Default value
{{ overview|truncate(200) }}                 # Truncate text
```

## Interfaces

### Input

- **Template**: DOCX file with Jinja2 syntax
- **Data**: CV JSON conforming to `cv_schema.json`

### Output

- **Rendered DOCX**: Formatted document with data populated

### Available Variables

All fields from CV schema:

```python
{
  "identity": {
    "title": str,
    "full_name": str,
    "first_name": str,
    "last_name": str
  },
  "sidebar": {
    "languages": [str],
    "tools": [str],
    "certifications": [str],
    "industries": [str],
    "spoken_languages": [str],
    "academic_background": [str]
  },
  "overview": str,
  "experiences": [
    {
      "heading": str,
      "description": str,
      "bullets": [str],
      "environment": [str] or null
    }
  ]
}
```

## Dependencies

### Internal Dependencies

- `cvextract.renderers.DocxCVRenderer` - Template processor
- `cvextract.contracts.cv_schema.json` - Data structure contract

### External Dependencies

- `docxtpl` - Jinja2 DOCX rendering engine
- `jinja2` - Template engine (via docxtpl)
- `python-docx` - DOCX manipulation (via docxtpl)

### Integration Points

- Used by `DocxCVRenderer`
- Accessed via `--render template=<path>`
- Sample in `examples/templates/CV_Template_Jinja2.docx`

## Test Coverage

Tested in:
- `tests/test_renderers.py` - Template rendering tests
- `tests/test_pipeline.py` - End-to-end rendering tests
- Manual testing with sample templates

## Implementation History

The Jinja2 templating system was chosen for its:
- Industry-standard syntax
- Rich feature set
- Good docxtpl integration
- Familiarity to developers

**Key Files**:
- Renderer: `cvextract/renderers/docx_renderer.py`
- Sample Template: `examples/templates/CV_Template_Jinja2.docx`
- Guide: `examples/templates/TEMPLATE_GUIDE.md`

## Best Practices

### Template Design

1. **Start Simple**: Basic layout first, add Jinja2 gradually
2. **Test Incrementally**: Render after each template change
3. **Use Word Styles**: Leverage Word's formatting (don't rely on Jinja2 for styling)
4. **Preserve Context**: Keep Jinja2 expressions in same paragraph/context
5. **Handle Nulls**: Use `{% if %}` for optional fields

### Common Patterns

**Optional Sections**:
```jinja2
{% if sidebar.certifications %}
  Certifications:
  {% for cert in sidebar.certifications %}
    • {{ cert }}
  {% endfor %}
{% endif %}
```

**Numbered Lists**:
```jinja2
{% for exp in experiences %}
  {{ loop.index }}. {{ exp.heading }}
{% endfor %}
```

**Formatted Lists**:
```jinja2
Skills: {{ sidebar.languages[:5]|join(', ') }}
{% if sidebar.languages|length > 5 %}
  (and {{ sidebar.languages|length - 5 }} more)
{% endif %}
```

## File Paths

- Renderer: `cvextract/renderers/docx_renderer.py`
- Sample Template: `examples/templates/CV_Template_Jinja2.docx`
- Guide: `examples/templates/TEMPLATE_GUIDE.md`
- Tests: `tests/test_renderers.py`

## Related Documentation

- [Templates Architecture](../README.md)
- [Sample Templates](../sample-templates/README.md)
- [DOCX Renderer](../../rendering/docx-renderer/README.md)
- Template Guide: `examples/templates/TEMPLATE_GUIDE.md`
