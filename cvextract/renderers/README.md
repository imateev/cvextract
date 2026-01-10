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
renderer = get_renderer("default-docx-cv-renderer")

# List all available renderers
renderers = list_renderers()
```

### CVRenderer Interface

The `CVRenderer` abstract base class defines the contract that all renderers must implement:

```python
from cvextract.renderers import CVRenderer
from cvextract.shared import StepName, UnitOfWork
from pathlib import Path

class CustomRenderer(CVRenderer):
    def render(self, work: UnitOfWork) -> UnitOfWork:
        input_path = work.get_step_input(StepName.Render)
        output_path = work.get_step_output(StepName.Render)
        # Your rendering logic here
        # Read CV data from input_path
        # Use work.config.render.template for the template
        # Save to output_path
        return work
```

### DocxCVRenderer (default-docx-cv-renderer)

The `DocxCVRenderer` is the default implementation (registered as `"default-docx-cv-renderer"`) that renders CV data to Microsoft Word `.docx` files using docxtpl templates:

```python
from cvextract.cli_config import RenderStage, UserConfig
from cvextract.renderers import get_renderer
from cvextract.shared import StepName, UnitOfWork
from pathlib import Path

template_path = Path("template.docx")
json_path = Path("cv_data.json")
output_path = Path("output/output.docx")

config = UserConfig(
    target_dir=Path("output"),
    render=RenderStage(template=template_path, data=json_path, output=output_path),
)
work = UnitOfWork(config=config, initial_input=json_path)
work.set_step_paths(
    StepName.Render,
    input_path=json_path,
    output_path=output_path,
)

renderer = get_renderer("default-docx-cv-renderer")
result = renderer.render(work)
output = result.get_step_output(StepName.Render)
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
   from cvextract.shared import StepName, UnitOfWork
   from pathlib import Path
   ```

2. Create your implementation:
   ```python
   class MyCustomRenderer(CVRenderer):
       def render(self, work: UnitOfWork) -> UnitOfWork:
           input_path = work.get_step_input(StepName.Render)
           output_path = work.get_step_output(StepName.Render)
           # Load template
           # Process input_path JSON with the template
           # Write output to output_path
           return work
   ```

3. Register and use your renderer:
   ```python
   # Register the renderer
   register_renderer("my-custom-renderer", MyCustomRenderer)
   
   # Get an instance via the registry
   renderer = get_renderer("my-custom-renderer")
   result = renderer.render(work)
   ```

## Examples

### Using the Default DOCX Renderer

```python
from cvextract.cli_config import RenderStage, UserConfig
from cvextract.renderers import get_renderer
from cvextract.shared import StepName, UnitOfWork
from pathlib import Path

json_path = Path("cv_data.json")
template_path = Path("template.docx")
output_path = Path("output/john_doe_NEW.docx")

config = UserConfig(
    target_dir=Path("output"),
    render=RenderStage(template=template_path, data=json_path, output=output_path),
)
work = UnitOfWork(config=config, initial_input=json_path)
work.set_step_paths(
    StepName.Render,
    input_path=json_path,
    output_path=output_path,
)

renderer = get_renderer("default-docx-cv-renderer")
result = renderer.render(work)

print(f"Rendered CV saved to: {result.get_step_output(StepName.Render)}")
```

### Creating a Mock Renderer for Testing

```python
from cvextract.cli_config import RenderStage, UserConfig
from cvextract.renderers import CVRenderer
from cvextract.shared import StepName, UnitOfWork
from pathlib import Path
import json

class MockCVRenderer(CVRenderer):
    def __init__(self):
        self.last_rendered = None
    
    def render(self, work: UnitOfWork) -> UnitOfWork:
        input_path = work.get_step_input(StepName.Render)
        output_path = work.get_step_output(StepName.Render)
        with input_path.open("r", encoding="utf-8") as f:
            cv_data = json.load(f)
        self.last_rendered = {
            "cv_data": cv_data,
            "template": work.config.render.template,
            "output": output_path
        }
        # Simulate file creation
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("Mock rendered content")
        return work

# Use in tests
renderer = MockCVRenderer()
work = UnitOfWork(
    config=UserConfig(
        target_dir=Path("output"),
        render=RenderStage(
            template=Path("template.docx"),
            data=Path("test_data.json"),
            output=Path("test_output.docx"),
        ),
    ),
    initial_input=Path("test_data.json"),
)
work.set_step_paths(
    StepName.Render,
    input_path=Path("test_data.json"),
    output_path=Path("test_output.docx"),
)
result = renderer.render(work)
```

### Passing Parameters from Outside

The renderer architecture allows you to pass both template and data as parameters:

```python
from cvextract.cli_config import RenderStage, UserConfig
from cvextract.renderers import get_renderer
from cvextract.shared import StepName, UnitOfWork
from pathlib import Path

def render_cv_with_custom_template(json_file: Path, template_file: Path, output_file: Path):
    """Render CV using externally provided template and data."""
    config = UserConfig(
        target_dir=output_file.parent,
        render=RenderStage(template=template_file, data=json_file, output=output_file),
    )
    work = UnitOfWork(
        config=config,
        initial_input=json_file,
    )
    work.set_step_paths(
        StepName.Render,
        input_path=json_file,
        output_path=output_file,
    )
    renderer = get_renderer("default-docx-cv-renderer")
    return renderer.render(work)

# Usage
result = render_cv_with_custom_template(
    json_file=Path("data/cv.json"),
    template_file=Path("templates/modern_template.docx"),
    output_file=Path("output/rendered_cv.docx"),
)
```

## Integration with Existing Pipeline

The renderers integrate with the existing pipeline through the `render_cv_data()` function in `pipeline_helpers.py`, which uses the default renderer (`"default-docx-cv-renderer"`).
