# CV Adjusters

This module provides a pluggable architecture for CV adjustment implementations. Adjusters can modify CV data for various purposes such as customer-specific tailoring, job-specific optimization, or other transformations.

## Architecture

The adjuster framework follows the same pluggable pattern as extractors and renderers:

- **Base Interface**: `CVAdjuster` abstract base class defines the contract
- **Registry System**: Adjusters are registered and can be looked up by name
- **Multiple Implementations**: Support for different adjustment strategies

## Built-in Adjusters

### `openai-company-research`

Adjusts CV data based on target company research using OpenAI.

**Parameters:**
- `customer_url` (required): URL of the target company's website

**Example:**
```python
from pathlib import Path
from cvextract.adjusters import get_adjuster
from cvextract.cli_config import UserConfig, ExtractStage
from cvextract.shared import StepName, UnitOfWork

adjuster = get_adjuster("openai-company-research", model="gpt-4o-mini")
work = UnitOfWork(
    config=UserConfig(target_dir=Path("out"), extract=ExtractStage(source=Path("cv.json"))),
)
work.set_step_paths(
    StepName.Adjust,
    input_path=Path("cv.json"),
    output_path=Path("cv.json"),
)
adjusted_work = adjuster.adjust(
    work,
    customer_url="https://example.com"
)
adjusted_json = adjusted_work.get_step_output(StepName.Adjust)
```

### `openai-job-specific`

Adjusts CV data based on a specific job description using OpenAI.

**Parameters:**
- `job_url` (required if no job_description): URL of the job posting
- `job_description` (required if no job_url): Direct text of job description

**Example:**
```python
from pathlib import Path
from cvextract.adjusters import get_adjuster
from cvextract.cli_config import UserConfig, ExtractStage
from cvextract.shared import StepName, UnitOfWork

adjuster = get_adjuster("openai-job-specific", model="gpt-4o-mini")
work = UnitOfWork(
    config=UserConfig(target_dir=Path("out"), extract=ExtractStage(source=Path("cv.json"))),
)
work.set_step_paths(
    StepName.Adjust,
    input_path=Path("cv.json"),
    output_path=Path("cv.json"),
)
adjusted_work = adjuster.adjust(
    work,
    job_url="https://careers.example.com/job/123"
)
adjusted_json = adjusted_work.get_step_output(StepName.Adjust)
```

## Creating Custom Adjusters

To create a custom adjuster:

1. Subclass `CVAdjuster`
2. Implement required methods: `name()`, `description()`, `adjust()`
3. Optionally override `validate_params()` for parameter validation
4. Register your adjuster with `register_adjuster()`

### Example Custom Adjuster

```python
from cvextract.adjusters import CVAdjuster, register_adjuster
from cvextract.shared import UnitOfWork
class MyCustomAdjuster(CVAdjuster):
    def name(self) -> str:
        return "my-custom-adjuster"
    
    def description(self) -> str:
        return "Does something custom with CV data"
    
    def validate_params(self, **kwargs) -> None:
        if 'required_param' not in kwargs:
            raise ValueError("required_param is missing")
    
    def adjust(self, work: UnitOfWork, **kwargs) -> UnitOfWork:
        self.validate_params(**kwargs)
        data = self._load_input_json(work)
        # Your adjustment logic here
        return self._write_output_json(work, data)

# Register it
register_adjuster(MyCustomAdjuster)
```

## Chaining Adjusters

Adjusters can be chained together in the CLI:

```bash
python -m cvextract.cli \
  --extract source=cv.docx \
  --adjust name=openai-company-research customer-url=https://example.com \
  --adjust name=openai-job-specific job-url=https://careers.example.com/job/123 \
  --render template=template.docx \
  --target output/
```

The output of each adjuster becomes the input to the next adjuster in the chain.

## Listing Available Adjusters

Use the CLI to list all registered adjusters:

```bash
python -m cvextract.cli --list adjusters
```

## Registry System

The `adjusters` module maintains a global registry of adjuster implementations:

- `register_adjuster(adjuster_class)`: Register an adjuster class
- `get_adjuster(name, **kwargs)`: Get an adjuster instance by name
- `list_adjusters()`: List all registered adjusters with descriptions

## Testing

When creating custom adjusters, follow these testing guidelines:

1. Test the adjuster in isolation with mock data
2. Test parameter validation
3. Test error handling (what happens when APIs fail, etc.)
4. Test integration with the CLI pipeline

## Best Practices

1. **Fail Gracefully**: If adjustment fails, return the original CV data
2. **Validate Parameters**: Use `validate_params()` to check required parameters early
3. **Log Appropriately**: Use the logging module to inform users of progress and errors
4. **Preserve Schema**: Never add or remove fields from the CV data structure
5. **Defer Output Verification**: Return adjusted CV data and let the pipeline run verifiers after the step completes
6. **Document Parameters**: Clearly document what parameters your adjuster expects
