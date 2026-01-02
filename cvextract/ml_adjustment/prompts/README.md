# Prompts Directory

This directory contains all prompt templates used by OpenAI-interacting components in the cvextract package.

## Overview

All prompts are stored as Markdown files (`.md`) in this directory. This approach provides:

- **Consistency**: All OpenAI components use the same prompt loading mechanism
- **Immutability**: Prompts are part of the installed package, not user-editable at runtime
- **Cross-platform compatibility**: Prompts are loaded using platform-independent paths
- **Version control**: Prompts are tracked in git like regular code
- **Easy editing**: Markdown format is human-readable and easy to modify

## Available Prompts

### CV Extraction (`openai_extractor.py`)

- **`cv_extraction_system.md`**: System prompt for CV data extraction
  - Sets up the assistant role as a CV/resume data extraction expert
  - Defines output format expectations (JSON only)
  
- **`cv_extraction_user.md`**: User prompt template for CV data extraction
  - Contains extraction guidelines and schema reference
  - Template variables: `{schema_json}`, `{file_name}`

### ML Adjustment (`ml_adjustment/adjuster.py`)

- **`system_prompt.md`**: System prompt for CV adjustment based on company profile
  - Template variables: `{company_name}`, `{company_desc}`, `{domains_text}`, etc.
  
- **`website_analysis_prompt.md`**: Prompt for company research
  - Template variables: `{customer_url}`, `{schema}`

### Job-Specific Adjustment (`adjusters/openai_job_specific_adjuster.py`)

- **`job_specific_prompt.md`**: Prompt for job-specific CV adjustment
  - Template variables: `{job_description}`

## How to Add a New Prompt

### 1. Create the Prompt File

Create a new `.md` file in this directory with a descriptive name:

```bash
# Example: adding a new prompt for cover letter generation
touch cvextract/ml_adjustment/prompts/cover_letter_generation.md
```

### 2. Write the Prompt Content

Write your prompt in Markdown format. Use `{variable_name}` syntax for template variables:

```markdown
You are an expert cover letter writer.

Generate a professional cover letter for the following job:

{job_description}

Based on the candidate's CV:

{cv_data}

Requirements:
1. Professional tone
2. Highlight relevant experience
3. Maximum 400 words
```

### 3. Load the Prompt in Your Code

Use the `prompt_loader` module to load your prompt:

```python
from cvextract.ml_adjustment.prompt_loader import load_prompt, format_prompt

# Load without formatting (if no variables)
prompt = load_prompt("cover_letter_generation")

# Load with formatting (if template variables exist)
formatted_prompt = format_prompt(
    "cover_letter_generation",
    job_description=job_desc,
    cv_data=json.dumps(cv_data)
)

if formatted_prompt is None:
    # Handle error - prompt file not found or formatting failed
    raise RuntimeError("Failed to load prompt")
```

### 4. Add Tests

Add tests to verify your prompt loads correctly:

```python
# In tests/test_prompt_loader.py

def test_load_cover_letter_generation_prompt(self):
    """Test loading cover_letter_generation.md file."""
    result = load_prompt("cover_letter_generation")
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0
    assert "cover letter" in result.lower()

def test_format_cover_letter_generation_prompt(self):
    """Test formatting cover_letter_generation with variables."""
    result = format_prompt(
        "cover_letter_generation",
        job_description="Software Engineer position",
        cv_data='{"name": "John Doe"}'
    )
    assert result is not None
    assert "Software Engineer position" in result
    assert "John Doe" in result
```

### 5. Update Tests to Include Your Prompt

Update the packaging tests to ensure your new prompt is included:

```python
# In tests/test_prompt_packaging.py

def test_prompts_accessible_via_pathlib(self):
    expected_prompts = [
        "system_prompt.md",
        "website_analysis_prompt.md",
        "job_specific_prompt.md",
        "cv_extraction_system.md",
        "cv_extraction_user.md",
        "cover_letter_generation.md",  # Add your prompt here
    ]
    # ... rest of test
```

### 6. Update Documentation

Document your new prompt in the relevant README files:

- `cvextract/ml_adjustment/README.md`: If it's an ML adjustment prompt
- Component-specific documentation: If it's for a specific component

## Prompt Loading Mechanism

Prompts are loaded using the `prompt_loader` module, which provides two main functions:

### `load_prompt(prompt_name: str) -> Optional[str]`

Loads a prompt file without formatting:

```python
prompt = load_prompt("system_prompt")
# Returns the raw content of system_prompt.md
```

### `format_prompt(prompt_name: str, **kwargs) -> Optional[str]`

Loads and formats a prompt with template variables:

```python
formatted = format_prompt(
    "cv_extraction_user",
    schema_json=json.dumps(schema),
    file_name="cv.docx"
)
# Returns the formatted prompt with variables substituted
```

## Packaging

Prompts are automatically included in the package distribution via `pyproject.toml`:

```toml
[tool.setuptools.package-data]
cvextract = ["contracts/*.json", "ml_adjustment/prompts/*.md"]
```

The `*.md` pattern ensures all Markdown files in the prompts directory are included when building the package.

## Best Practices

1. **Use descriptive names**: Prompt filenames should clearly indicate their purpose
2. **Keep prompts focused**: Each prompt should have a single, well-defined purpose
3. **Document template variables**: List all required variables in a comment at the top of the prompt
4. **Test thoroughly**: Always add tests to verify prompt loading and formatting
5. **Version control**: Track prompt changes in git like any other code
6. **Avoid inline prompts**: Never store prompts as inline strings in Python files

## Migration Guide

If you have inline prompts in your code, migrate them following these steps:

1. **Extract the prompt**: Copy the prompt string from your Python code
2. **Create a prompt file**: Save it as a `.md` file in this directory
3. **Update the code**: Replace the inline string with `load_prompt()` or `format_prompt()`
4. **Add tests**: Verify the prompt loads correctly
5. **Remove the inline string**: Delete the old inline prompt from your code

Example:

```python
# Before (inline prompt)
system_prompt = """You are a helpful assistant.
Extract data from the document."""

# After (prompt file)
from cvextract.ml_adjustment.prompt_loader import load_prompt

system_prompt = load_prompt("my_extraction_system")
if not system_prompt:
    raise RuntimeError("Failed to load system prompt")
```

## Troubleshooting

### Prompt not loading

If `load_prompt()` returns `None`:

1. Check the prompt filename (without `.md` extension)
2. Verify the file exists in `cvextract/ml_adjustment/prompts/`
3. Check file permissions (must be readable)
4. Verify the package is properly installed

### Formatting fails

If `format_prompt()` returns `None`:

1. Verify all required template variables are provided
2. Check for typos in variable names (must match exactly)
3. Ensure the prompt file exists and is loadable

### Prompt not in package distribution

If prompts are missing after installation:

1. Verify `pyproject.toml` includes the prompts pattern
2. Rebuild the package: `pip install -e .`
3. Check the wheel contents: `unzip -l dist/*.whl | grep prompts`

## See Also

- `cvextract/ml_adjustment/prompt_loader.py`: Implementation of prompt loading
- `cvextract/ml_adjustment/README.md`: ML adjustment module documentation
- `tests/test_prompt_loader.py`: Prompt loading tests
- `tests/test_prompt_packaging.py`: Packaging verification tests
