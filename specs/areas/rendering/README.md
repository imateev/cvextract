# Rendering Area

## Purpose

The rendering area provides a pluggable architecture for rendering structured CV data to various output formats, currently supporting DOCX via Jinja2 templates.

## Features

- [DOCX Renderer](docx-renderer/README.md) - Renders CV data to DOCX using docxtpl/Jinja2
- [Pluggable Renderer Architecture](pluggable-renderer-architecture/README.md) - Abstract base class and registry for renderers

## Architectural Notes

### Design Principles

1. **Pluggable Architecture**: All renderers implement the `CVRenderer` abstract base class
2. **Registry Pattern**: Renderers are registered by name (ready for future expansion)
3. **Template-Based**: Separates data from presentation
4. **Format Agnostic**: Architecture supports PDF, HTML, etc. (DOCX currently implemented)

### Key Components

- **Base Interface**: `cvextract/renderers/base.py` - `CVRenderer` abstract base class
- **DOCX Implementation**: `cvextract/renderers/docx_renderer.py` - Jinja2/docxtpl rendering
- **Public API**: `cvextract/renderers/__init__.py`

### Data Flow

```
UnitOfWork (input JSON + template + output path)
    │
    v
[Renderer.render(work)]
    │
    v
Rendered Document (.docx)
```

### Integration Points

- **CLI**: `--render template=<path> data=<json>`
- **Pipeline**: `cvextract.pipeline_highlevel.render_cv_data()`
- **Templates**: Jinja2 templates in `examples/templates/`

## Dependencies

- **Internal**: `cvextract.contracts` (CV schema)
- **External**: `docxtpl` (Jinja2 DOCX templating), `python-docx` (DOCX manipulation)

## File References

- Base: `cvextract/renderers/base.py`
- DOCX Renderer: `cvextract/renderers/docx_renderer.py`
- Public API: `cvextract/renderers/__init__.py`
- Documentation: `cvextract/renderers/README.md`
- Templates: `examples/templates/*.docx`
