# Sample Templates

## Overview

Sample templates provide ready-to-use, professional CV templates demonstrating the templating system capabilities.

## Status

**Active** - Production-ready templates

## Description

Included templates:
1. **CV_Template_Jinja2.docx**: Professional CV template with full Jinja2 integration

Features:
- Clean, professional layout
- Complete variable coverage (all CV schema fields)
- Proper use of Jinja2 loops and conditionals
- Word styling (fonts, colors, spacing)
- Production-tested

## Entry Points

### Template Location

`examples/templates/CV_Template_Jinja2.docx`

### Usage

```bash
# Extract and apply sample template
python -m cvextract.cli \
  --extract source=cv.docx \
  --apply template=examples/templates/CV_Template_Jinja2.docx \
  --target output/

# With adjustment
python -m cvextract.cli \
  --extract source=cv.docx \
  --adjust name=openai-company-research customer-url=https://example.com \
  --apply template=examples/templates/CV_Template_Jinja2.docx \
  --target output/
```

### Customization

1. Open `CV_Template_Jinja2.docx` in Microsoft Word
2. Modify fonts, colors, layout as needed
3. Keep Jinja2 expressions intact
4. Save and test with actual CV data

## Template Features

### CV_Template_Jinja2.docx

**Sections**:
- Header with name and title
- Sidebar with skills, tools, certifications, etc.
- Professional overview
- Detailed experience entries with bullets
- Environment/technology tags per experience

**Jinja2 Usage**:
- Variables: `{{ identity.full_name }}`, etc.
- Loops: `{% for exp in experiences %}`
- Filters: `{{ sidebar.languages|join(', ') }}`
- Conditionals: `{% if experience.environment %}`

**Styling**:
- Professional fonts (Calibri, Arial)
- Consistent spacing and margins
- Color accents for headers
- Bullet formatting for achievements

## Configuration

### Template Variables Used

**All identity fields**:
```jinja2
{{ identity.title }}
{{ identity.full_name }}
{{ identity.first_name }}
{{ identity.last_name }}
```

**All sidebar fields**:
```jinja2
{{ sidebar.languages|join(', ') }}
{{ sidebar.tools|join(', ') }}
{{ sidebar.certifications|join(', ') }}
{{ sidebar.industries|join(', ') }}
{{ sidebar.spoken_languages|join(', ') }}
{{ sidebar.academic_background|join(', ') }}
```

**Overview and experiences**:
```jinja2
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

## Interfaces

### Input

- CV data conforming to `cv_schema.json`

### Output

- Formatted DOCX with professional appearance
- All data properly rendered
- Consistent styling throughout

## Dependencies

### Internal Dependencies

- `cvextract.renderers.DocxCVRenderer` - Template processor
- `cvextract.contracts.cv_schema.json` - Data structure

### External Dependencies

- `docxtpl` - Template rendering
- Microsoft Word (for editing)

### Integration Points

- Used in README examples
- Used in tests as reference template
- Starting point for custom templates

## Test Coverage

Tested in:
- `tests/test_renderers.py` - Rendering with sample template
- `tests/test_pipeline.py` - End-to-end with sample template
- README examples using sample template

## Implementation History

Sample templates were created to:
- Demonstrate templating capabilities
- Provide production-ready starting point
- Serve as documentation by example

**Key Files**:
- Template: `examples/templates/CV_Template_Jinja2.docx`
- Guide: `examples/templates/TEMPLATE_GUIDE.md`

## Creating Custom Templates

### Starting from Sample

1. **Copy Template**:
   ```bash
   cp examples/templates/CV_Template_Jinja2.docx my_template.docx
   ```

2. **Edit in Word**:
   - Open in Microsoft Word
   - Modify layout, fonts, colors
   - Keep Jinja2 expressions

3. **Test**:
   ```bash
   python -m cvextract.cli \
     --extract source=test_cv.docx \
     --apply template=my_template.docx \
     --target test_output/
   ```

4. **Iterate**: Refine based on output

### Template Checklist

- [ ] All CV schema fields represented
- [ ] Jinja2 loops for experiences and bullets
- [ ] Filters for joining lists
- [ ] Conditionals for optional fields
- [ ] Consistent styling (fonts, colors)
- [ ] Proper spacing and margins
- [ ] Tested with real CV data
- [ ] Handles edge cases (empty lists, nulls)

## File Paths

- Template: `examples/templates/CV_Template_Jinja2.docx`
- Guide: `examples/templates/TEMPLATE_GUIDE.md`
- Tests: `tests/test_renderers.py`

## Related Documentation

- [Templates Architecture](../README.md)
- [Templating System](../templating-system/README.md)
- [DOCX Renderer](../../rendering/docx-renderer/README.md)
- Template Guide: `examples/templates/TEMPLATE_GUIDE.md`
