# Pluggable Renderer Architecture

## Overview

The pluggable renderer architecture provides an abstract base class, registry infrastructure, and APIs for interchangeable rendering implementations.

## Status

**Active** - Core rendering infrastructure with registry system

## Description

The architecture enables:
1. **Base Class**: `CVRenderer` abstract interface for all renderers
2. **Registry System**: Centralized management of available renderers
3. **Interchangeability**: Easy swapping of rendering implementations via registry lookup
4. **Extensibility**: Add new output formats (PDF, HTML, etc.) without modifying core code
5. **Testing**: Mock renderers for isolated testing
6. **CLI Integration**: List and select renderers via command-line interface

## Entry Points

### Registry APIs

```python
from cvextract.renderers import register_renderer, get_renderer, list_renderers

# Register a custom renderer
register_renderer("my-custom-renderer", MyCustomRenderer)

# Get a renderer instance by name
renderer = get_renderer("private-internal-renderer")

# List all available renderers
renderers = list_renderers()
```

### Base Class Definition

```python
from cvextract.renderers import CVRenderer
from cvextract.shared import UnitOfWork

class CustomRenderer(CVRenderer):
    def render(self, work: UnitOfWork) -> UnitOfWork:
        # Your rendering logic
        return work
```

### Using Renderers

```python
from cvextract.renderers import get_renderer

renderer = get_renderer("private-internal-renderer")
result = renderer.render(work)
```

## Configuration

### CVRenderer Interface

```python
class CVRenderer(ABC):
    @abstractmethod
    def render(self, work: UnitOfWork) -> UnitOfWork:
        """
        Render CV data to output file using template.
        
        Args:
            work: UnitOfWork containing input/output paths and render config
            
        Returns:
            UnitOfWork with rendered output populated
        """
        pass
```

## Interfaces

### Input Contract

- **work.input**: JSON file conforming to `cvextract/contracts/cv_schema.json`
- **work.config.render.template**: Path to format-specific template file
- **work.output**: Path where rendered file should be written

### Output Contract

- Returns: UnitOfWork with rendered output populated
- Side Effect: Creates rendered file at work.output

## Dependencies

### Internal Dependencies

- `cvextract.contracts.cv_schema.json` - Input data schema

### External Dependencies

None (base class is pure Python)

### Integration Points

- Implemented by `cvextract.renderers.DocxCVRenderer` (registered as `"private-internal-renderer"`)
- Used by `cvextract.pipeline_helpers.render_cv_data()`
- Registry pattern mirrors `cvextract.extractors.extractor_registry`

## Test Coverage

Tested in:
- `tests/test_renderers.py` - Base class contract
- `tests/test_docx_renderer.py` - DOCX implementation
- `tests/test_renderer_registry.py` - Registry functionality
- Mock renderers in test suites

## Implementation History

The pluggable architecture was introduced during refactoring to separate concerns and enable extensibility. The registry system was added to match the architecture of extractors and adjusters.

**Key Files**:
- `cvextract/renderers/base.py` - Abstract base class
- `cvextract/renderers/docx_renderer.py` - DOCX implementation (registered as `"private-internal-renderer"`)
- `cvextract/renderers/renderer_registry.py` - Registry implementation
- `cvextract/renderers/__init__.py` - Public API and renderer registration

## Extension Examples

### Custom PDF Renderer

```python
from cvextract.renderers import CVRenderer, register_renderer
from cvextract.shared import UnitOfWork

class PdfCVRenderer(CVRenderer):
    """PDF renderer using reportlab or weasyprint."""
    
    def render(self, work: UnitOfWork) -> UnitOfWork:
        # PDF rendering logic using reportlab, weasyprint, etc.
        # ...
        return work

# Register the renderer
register_renderer("pdf-renderer", PdfCVRenderer)

# Use via registry
renderer = get_renderer("pdf-renderer")
# work = UnitOfWork(...)
result = renderer.render(work)
```

### Custom HTML Renderer

```python
from cvextract.renderers import CVRenderer, register_renderer
from cvextract.shared import UnitOfWork
import jinja2
import json

class HtmlCVRenderer(CVRenderer):
    """HTML renderer using Jinja2 templates."""
    
    def render(self, work: UnitOfWork) -> UnitOfWork:
        # Load Jinja2 HTML template
        with open(work.config.render.template) as f:
            template = jinja2.Template(f.read())
        
        # Render
        with work.input.open("r", encoding="utf-8") as f:
            cv_data = json.load(f)
        html = template.render(**cv_data)
        
        # Save
        work.output.write_text(html)
        return work

# Register the renderer
register_renderer("html-renderer", HtmlCVRenderer)
```

### Mock Renderer for Testing

```python
from cvextract.renderers import CVRenderer
from cvextract.shared import UnitOfWork
import json

class MockCVRenderer(CVRenderer):
    def __init__(self):
        self.last_rendered = None
    
    def render(self, work: UnitOfWork) -> UnitOfWork:
        with work.input.open("r", encoding="utf-8") as f:
            cv_data = json.load(f)
        self.last_rendered = {
            "cv_data": cv_data,
            "template": work.config.render.template,
            "output": work.output
        }
        # Create mock output
        work.output.write_text("Mock rendered content")
        return work

# Use in tests
renderer = MockCVRenderer()
# work = UnitOfWork(...)
result = renderer.render(work)
assert renderer.last_rendered["cv_data"] is not None
```

## File Paths

- Base Class: `cvextract/renderers/base.py`
- DOCX Implementation: `cvextract/renderers/docx_renderer.py`
- Registry: `cvextract/renderers/renderer_registry.py`
- Public API: `cvextract/renderers/__init__.py`
- Tests: `tests/test_renderers.py`, `tests/test_renderer_registry.py`
- Documentation: `cvextract/renderers/README.md`

## Related Documentation

- [Rendering Architecture](../README.md)
- [DOCX Renderer](../docx-renderer/README.md)
- Module README: `cvextract/renderers/README.md`
