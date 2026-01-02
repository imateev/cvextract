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
from pathlib import Path
from typing import Dict, Any

class CustomRenderer(CVRenderer):
    def render(self, cv_data: Dict[str, Any], template_path: Path, output_path: Path) -> Path:
        # Your rendering logic
        return output_path
```

### Using Renderers

```python
from cvextract.renderers import get_renderer

renderer = get_renderer("private-internal-renderer")
output = renderer.render(cv_data, template_path, output_path)
```

## Configuration

### CVRenderer Interface

```python
class CVRenderer(ABC):
    @abstractmethod
    def render(self, cv_data: Dict[str, Any], template_path: Path, output_path: Path) -> Path:
        """
        Render CV data to output file using template.
        
        Args:
            cv_data: CV data dict conforming to cv_schema.json
            template_path: Path to template file
            output_path: Path for rendered output file
            
        Returns:
            Path to the rendered output file
        """
        pass
```

## Interfaces

### Input Contract

- **cv_data**: Dictionary conforming to `cvextract/contracts/cv_schema.json`
- **template_path**: Path to format-specific template file
- **output_path**: Path where rendered file should be written

### Output Contract

- Returns: Path to successfully rendered file
- Side Effect: Creates rendered file at output_path

## Dependencies

### Internal Dependencies

- `cvextract.contracts.cv_schema.json` - Input data schema

### External Dependencies

None (base class is pure Python)

### Integration Points

- Implemented by `cvextract.renderers.DocxCVRenderer` (registered as `"private-internal-renderer"`)
- Used by `cvextract.pipeline_highlevel.render_cv_data()`
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
from pathlib import Path
from typing import Dict, Any

class PdfCVRenderer(CVRenderer):
    """PDF renderer using reportlab or weasyprint."""
    
    def render(self, cv_data: Dict[str, Any], template_path: Path, output_path: Path) -> Path:
        # PDF rendering logic using reportlab, weasyprint, etc.
        # ...
        return output_path

# Register the renderer
register_renderer("pdf-renderer", PdfCVRenderer)

# Use via registry
renderer = get_renderer("pdf-renderer")
output = renderer.render(cv_data, Path("template.html"), Path("cv.pdf"))
```

### Custom HTML Renderer

```python
from cvextract.renderers import CVRenderer, register_renderer
from pathlib import Path
from typing import Dict, Any
import jinja2

class HtmlCVRenderer(CVRenderer):
    """HTML renderer using Jinja2 templates."""
    
    def render(self, cv_data: Dict[str, Any], template_path: Path, output_path: Path) -> Path:
        # Load Jinja2 HTML template
        with open(template_path) as f:
            template = jinja2.Template(f.read())
        
        # Render
        html = template.render(**cv_data)
        
        # Save
        output_path.write_text(html)
        return output_path

# Register the renderer
register_renderer("html-renderer", HtmlCVRenderer)
```

### Mock Renderer for Testing

```python
from cvextract.renderers import CVRenderer
from pathlib import Path
from typing import Dict, Any

class MockCVRenderer(CVRenderer):
    def __init__(self):
        self.last_rendered = None
    
    def render(self, cv_data: Dict[str, Any], template_path: Path, output_path: Path) -> Path:
        self.last_rendered = {
            "cv_data": cv_data,
            "template": template_path,
            "output": output_path
        }
        # Create mock output
        output_path.write_text("Mock rendered content")
        return output_path

# Use in tests
renderer = MockCVRenderer()
output = renderer.render(test_data, template, output_path)
assert renderer.last_rendered["cv_data"] == test_data
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
