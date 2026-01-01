# CV Template Documentation

## Overview
The `CV_Template.docx` is a Jinja2-compatible Word template for rendering extracted CV data using the cvextract system. It uses the **docxtpl** library which allows embedding Jinja2 template syntax directly in Word documents.

## Template Location
```
examples/templates/CV_Template.docx
```

## Usage

### Basic Command
```bash
python -m cvextract.cli \
  --extract source=path/to/cv.docx \
  --apply template=examples/templates/CV_Template.docx \
  --target output_directory
```

### Example with Full Pipeline
```bash
# Extract, apply template, and render
python -m cvextract.cli \
  --extract source=examples/cvs/Sarah_Connor_CV.docx \
  --apply template=examples/templates/CV_Template.docx \
  --target /tmp/rendered_cv

# Output location:
# /tmp/rendered_cv/documents/Sarah_Connor_CV.docx
```

## Available Template Variables

### Identity Information
```jinja2
{{ identity.title }}           # Job title (string)
{{ identity.full_name }}       # Full name (string)
{{ identity.first_name }}      # First name (string)
{{ identity.last_name }}       # Last name (string)
```

### Sidebar Skills & Background
All sidebar fields support the `join` filter for comma-separated output:

```jinja2
{{ sidebar.languages|join(', ') }}              # Programming languages
{{ sidebar.tools|join(', ') }}                  # Tools and technologies
{{ sidebar.certifications|join(', ') }}         # Certifications
{{ sidebar.industries|join(', ') }}             # Industries
{{ sidebar.spoken_languages|join(', ') }}       # Languages spoken
{{ sidebar.academic_background|join(', ') }}    # Educational background
```

### Main Content
```jinja2
{{ overview }}                 # Professional summary/overview (string)
```

### Professional Experiences
Use a Jinja2 for-loop to render multiple experiences:

```jinja2
{% for experience in experiences %}
    {{ experience.heading }}           # Job title and date range
    {{ experience.description }}       # Job description text
    
    {% for bullet in experience.bullets %}
        {{ bullet }}                   # Individual bullet point
    {% endfor %}
    
    {% if experience.environment %}
        {{ experience.environment|join(', ') }}  # Technologies/environment
    {% endif %}
{% endfor %}
```

## Template Data Structure

The CV data passed to the template has this structure:

```json
{
  "identity": {
    "title": "Job Title",
    "full_name": "Full Name",
    "first_name": "First",
    "last_name": "Last"
  },
  "sidebar": {
    "languages": ["Python", "C++", ...],
    "tools": ["Docker", "Kubernetes", ...],
    "certifications": ["CISSP", ...],
    "industries": ["Tech", "Finance", ...],
    "spoken_languages": ["English", "German", ...],
    "academic_background": ["BS CS", "MS EE", ...]
  },
  "overview": "Professional summary text...",
  "experiences": [
    {
      "heading": "Senior Engineer - Jan 2020 - Present",
      "description": "Job description text...",
      "bullets": [
        "Achievement 1",
        "Achievement 2",
        ...
      ],
      "environment": ["Python", "AWS"] or null
    },
    ...
  ]
}
```

## Jinja2 Filters Used

### `join(separator)`
Converts a list into a string with the given separator:
```jinja2
{{ sidebar.languages|join(', ') }}
# Output: "Python, C++, Rust, Go"
```

## Editing the Template

To customize the template:

1. **Open in Word**: Open `examples/templates/CV_Template.docx` in Microsoft Word
2. **Edit Style**: Adjust fonts, spacing, colors, layout as needed
3. **Preserve Jinja2 Syntax**: Keep all `{{ variable }}` and `{% for ... %}` blocks intact
4. **Test Rendering**: Run the extract+apply command to verify output

### Important Notes
- Jinja2 expressions must remain inside their paragraph/text contexts
- Avoid deleting or moving template variables
- Use Word's native formatting (bold, italics, colors) - don't rely on CSS
- Test with actual extracted data to ensure all fields render correctly

## Advanced Customization

### Conditional Rendering
Show content only if a field exists:
```jinja2
{% if identity.title %}
    Title: {{ identity.title }}
{% endif %}
```

### Filtering Lists
Only include non-empty items:
```jinja2
{% for lang in sidebar.languages if lang %}
    {{ lang }}
{% endfor %}
```

### Multiple Sections
The template supports multiple professional experiences, education entries, etc.:
```jinja2
{% for exp in experiences %}
    <render experience>
{% endfor %}
```

## Output

After running extract+apply:
- **Rendered DOCX**: `output_directory/documents/filename.docx`
- **Extracted JSON**: `output_directory/structured_data/filename.json`

Both contain the same CV data in different formats.

## Troubleshooting

### Template not rendering
- Ensure template file is `.docx` format (not `.doc`)
- Check that all Jinja2 syntax is preserved exactly
- Verify extracted JSON has correct data structure

### Missing or incorrect data
- Check the extracted JSON to verify data was extracted correctly
- Ensure sidebar lists aren't empty
- Verify experience bullets have content

### Word document errors
- Try opening template in Word and saving to refresh formatting
- Check for hidden special characters in Jinja2 expressions
- Ensure template hasn't been corrupted by editing

## Example Templates

For reference implementations, see:
- `examples/templates/CV_Template.docx` - Standard professional template
- `examples/cvs/Sarah_Connor_CV.docx` - Example extracted CV