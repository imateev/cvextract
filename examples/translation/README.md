# Translation Example (German)

This example translates a CV to German using the structured JSON pipeline and renders it with a DOCX template.

## Command

```bash
export OPENAI_API_KEY="sk-proj-..."

python -m cvextract.cli \
  --extract source=examples/cvs/Sarah_Connor_CV.docx \
  --adjust name=openai-translate language=de \
  --render template=examples/templates/CV_Template_Jinja2.docx \
  --target output/
```

## Outputs

- `output/structured_data/Sarah_Connor_CV.json` (extracted)
- `output/adjusted_structured_data/Sarah_Connor_CV.json` (translated)
- `output/documents/Sarah_Connor_CV_NEW.docx` (rendered)
