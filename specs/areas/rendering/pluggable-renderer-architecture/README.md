# Pluggable Renderer Architecture

## Overview

The pluggable renderer architecture provides an abstract base class and infrastructure for interchangeable rendering implementations.

## Status

**Active** - Core rendering infrastructure

## Description

The architecture enables:
1. **Base Class**: `CVRenderer` abstract interface for all renderers
2. **Interchangeability**: Easy swapping of rendering implementations
3. **Extensibility**: Add new output formats (PDF, HTML, etc.) without modifying core code
4. **Testing**: Mock renderers for isolated testing

## Entry Points

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
from cvextract.renderers import DocxCVRenderer

renderer = DocxCVRenderer()
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

- Implemented by `cvextract.renderers.DocxCVRenderer`
- Used by `cvextract.pipeline_highlevel.render_cv_data()`
- Future: Registry pattern like extractors/adjusters

## Test Coverage

Tested in:
- `tests/test_renderers.py` - Base class contract
- `tests/test_docx_renderer.py` - DOCX implementation
- Mock renderers in test suites

## Implementation History

The pluggable architecture was introduced during refactoring to separate concerns and enable extensibility.

**Key Files**:
- `cvextract/renderers/base.py` - Abstract base class
- `cvextract/renderers/docx_renderer.py` - DOCX implementation
- `cvextract/renderers/__init__.py` - Public API

## Open Questions

1. **Registry**: Should we implement a renderer registry like extractors/adjusters?
2. **Multi-Format**: Should one renderer support multiple output formats?
3. **Streaming**: Should we support streaming rendering for large documents?
4. **Validation**: Should renderers validate input data against schema?

## Extension Examples

### Custom PDF Renderer

```python
from cvextract.renderers import CVRenderer
from pathlib import Path
from typing import Dict, Any

class PdfCVRenderer(CVRenderer):
    def render(self, cv_data: Dict[str, Any], template_path: Path, output_path: Path) -> Path:
        # PDF rendering logic using reportlab, weasyprint, etc.
        # ...
        return output_path

# Use
renderer = PdfCVRenderer()
output = renderer.render(cv_data, Path("template.html"), Path("cv.pdf"))
```

### Custom HTML Renderer

```python
from cvextract.renderers import CVRenderer
from pathlib import Path
from typing import Dict, Any
import jinja2

class HtmlCVRenderer(CVRenderer):
    def render(self, cv_data: Dict[str, Any], template_path: Path, output_path: Path) -> Path:
        # Load Jinja2 HTML template
        with open(template_path) as f:
            template = jinja2.Template(f.read())
        
        # Render
        html = template.render(**cv_data)
        
        # Save
        output_path.write_text(html)
        return output_path
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
- Public API: `cvextract/renderers/__init__.py`
- Tests: `tests/test_renderers.py`
- Documentation: `cvextract/renderers/README.md`

## Related Documentation

- [Rendering Architecture](../README.md)
- [DOCX Renderer](../docx-renderer/README.md)
- Module README: `cvextract/renderers/README.md`
