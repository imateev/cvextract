# Templates Area

## Purpose

The templates area provides Jinja2-based DOCX templating system and sample templates for rendering CV data to formatted Word documents.

## Features

- [Templating System](templating-system/README.md) - Jinja2-based DOCX template rendering via docxtpl
- [Sample Templates](sample-templates/README.md) - Professional CV template examples

## Architectural Notes

### Design Principles

1. **Separation of Concerns**: Data separated from presentation
2. **Standard Tools**: Uses Jinja2 (industry standard templating)
3. **WYSIWYG**: Templates edited in Microsoft Word
4. **Flexibility**: Full Jinja2 features available (loops, conditionals, filters)

### Key Components

- **Template Engine**: `docxtpl` library provides Jinja2 integration with DOCX
- **Sample Templates**: `examples/templates/*.docx` - Ready-to-use templates
- **Documentation**: `examples/templates/TEMPLATE_GUIDE.md` - Template authoring guide

### Template Variables

Templates have access to full CV data structure:

```jinja2
{{ identity.full_name }}
{{ sidebar.languages|join(', ') }}
{{ overview }}
{% for exp in experiences %}
  {{ exp.heading }}
  {% for bullet in exp.bullets %}
    {{ bullet }}
  {% endfor %}
{% endfor %}
```

### Integration Points

- **Renderer**: `cvextract.renderers.DocxCVRenderer` processes templates
- **CLI**: `--apply template=<path>` specifies template
- **Data Source**: CV data conforming to `cvextract/contracts/cv_schema.json`

## Dependencies

- **Internal**: `cvextract.renderers.DocxCVRenderer`, `cvextract.contracts.cv_schema.json`
- **External**: `docxtpl` (Jinja2 DOCX rendering), `python-docx` (DOCX manipulation)

## File References

- Sample Templates: `examples/templates/CV_Template_Jinja2.docx`
- Template Guide: `examples/templates/TEMPLATE_GUIDE.md`
- Renderer: `cvextract/renderers/docx_renderer.py`
