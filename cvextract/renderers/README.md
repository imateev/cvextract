# CV Renderers

This module provides a pluggable architecture for rendering structured CV data to various output formats.

## Overview

The renderer architecture allows for interchangeable implementations of CV rendering through a registry system, making it easy to:

- Add support for new output formats (PDF, HTML, etc.)
- Replace or customize rendering logic
- Test rendering logic in isolation
- Implement custom rendering pipelines
- Choose between different renderers via CLI

## Core Concepts

### Renderer Registry

The renderer registry manages all available renderers and allows you to register new ones:

```python
from cvextract.renderers import register_renderer, get_renderer, list_renderers

# Register a custom renderer
register_renderer("my-custom-renderer", MyCustomRenderer)

# Get a renderer instance by name
renderer = get_renderer("private-internal-renderer")

# List all available renderers
renderers = list_renderers()
```

### CVRenderer Interface

The `CVRenderer` abstract base class defines the contract that all renderers must implement:

```python
from cvextract.renderers import CVRenderer
from pathlib import Path
from typing import Dict, Any

class CustomRenderer(CVRenderer):
    def render(self, cv_data: Dict[str, Any], template_path: Path, output_path: Path) -> Path:
        # Your rendering logic here
        # Process cv_data using template_path
        # Save to output_path
        return output_path
```

### DocxCVRenderer (private-internal-renderer)

The `DocxCVRenderer` is the default implementation (registered as `"private-internal-renderer"`) that renders CV data to Microsoft Word `.docx` files using docxtpl templates:

```python
from cvextract.renderers import get_renderer
from pathlib import Path

renderer = get_renderer("private-internal-renderer")
cv_data = {
    "identity": {...},
    "sidebar": {...},
    "overview": "...",
    "experiences": [...]
}
output = renderer.render(cv_data, Path("template.docx"), Path("output.docx"))
```

## CV Data Schema

All renderers accept data conforming to the CV schema defined in `cv_schema.json`. The structure includes:

- **identity**: Personal information (title, full_name, first_name, last_name)
- **sidebar**: Categorized lists (languages, tools, certifications, industries, spoken_languages, academic_background)
- **overview**: Free-text overview section
- **experiences**: List of professional experience entries (heading, description, bullets, environment)

See `cv_schema.json` in the cvextract/contracts/ directory for the complete JSON schema definition.

## Creating a Custom Renderer

To create a custom renderer:

1. Import the base class:
   ```python
   from cvextract.renderers import CVRenderer, register_renderer
   ```

2. Create your implementation:
   ```python
   class MyCustomRenderer(CVRenderer):
       def render(self, cv_data: Dict[str, Any], template_path: Path, output_path: Path) -> Path:
           # Load template
           # Process cv_data with the template
           # Write output to output_path
           return output_path
   ```

3. Register and use your renderer:
   ```python
   # Register the renderer
   register_renderer("my-custom-renderer", MyCustomRenderer)
   
   # Get an instance via the registry
   renderer = get_renderer("my-custom-renderer")
   output = renderer.render(cv_data, Path("template.ext"), Path("output.ext"))
   ```

## Examples

### Using the Default DOCX Renderer

```python
from cvextract.renderers import get_renderer
from pathlib import Path
import json

# Load CV data
with open("cv_data.json", "r") as f:
    cv_data = json.load(f)

# Get the default renderer from the registry
renderer = get_renderer("private-internal-renderer")

# Render CV data to DOCX
output_path = renderer.render(
    cv_data,
    template_path=Path("template.docx"),
    output_path=Path("output/john_doe_NEW.docx")
)

print(f"Rendered CV saved to: {output_path}")
```

### Creating a Mock Renderer for Testing

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
        # Simulate file creation
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("Mock rendered content")
        return output_path

# Use in tests
renderer = MockCVRenderer()
output = renderer.render(test_data, Path("template.docx"), Path("test_output.docx"))
assert renderer.last_rendered["cv_data"] == test_data
```

### Passing Parameters from Outside

The renderer architecture allows you to pass both template and data as parameters:

```python
from cvextract.renderers import get_renderer
from pathlib import Path
import json

def render_cv_with_custom_template(json_file: Path, template_file: Path, output_file: Path):
    """Render CV using externally provided template and data."""
    # Load structured data from external source
    with open(json_file, "r") as f:
        cv_data = json.load(f)
    
    # Use the default renderer from the registry
    renderer = get_renderer("private-internal-renderer")
    return renderer.render(cv_data, template_file, output_file)

# Usage
output = render_cv_with_custom_template(
    json_file=Path("data/cv.json"),
    template_file=Path("templates/modern_template.docx"),
    output_file=Path("output/rendered_cv.docx")
)
```

## Integration with Existing Pipeline

The renderers integrate seamlessly with the existing pipeline through the `render_cv_data()` function in `pipeline_highlevel.py`, which uses the default renderer (`"private-internal-renderer"`) while maintaining backward compatibility.
