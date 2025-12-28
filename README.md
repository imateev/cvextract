## Project Overview

This project is an internal CV transformation pipeline designed to help the resourcing team migrate consultant CVs from the old Word template to the new one.

### Tool summary
This is a command-line tool that converts résumé/CV .docx files into a clean, structured JSON format and can optionally generate a new .docx by filling a Word template with that JSON.

### CV Data Schema
The extracted data conforms to a well-defined JSON schema (see `cvextract/contracts/cv_schema.json`) that ensures consistency and interoperability. The schema defines the structure for:
- **identity**: Personal information (title, names)
- **sidebar**: Categorized skills, tools, languages, etc.
- **overview**: Professional summary
- **experiences**: Work history with details

### Pluggable Extractors
The extraction logic is implemented using a pluggable architecture (`cvextract/extractors/`) that allows:
- **Interchangeable implementations**: Easy to swap or customize extraction logic
- **Support for multiple formats**: Current DOCX support can be extended to PDF, HTML, etc.
- **Testing flexibility**: Mock extractors for testing without real documents

See `cvextract/extractors/README.md` for details on creating custom extractors.

### Pluggable Renderers
The rendering logic is implemented using a pluggable architecture (`cvextract/renderers/`) that allows:
- **Interchangeable implementations**: Easy to swap or customize rendering logic
- **Support for multiple formats**: Current DOCX support can be extended to PDF, HTML, etc.
- **External parameters**: Templates and structured data can be passed from outside
- **Testing flexibility**: Mock renderers for testing without real templates

See `cvextract/renderers/README.md` for details on creating custom renderers.

### Pluggable Verifiers
The verification logic is implemented using a pluggable architecture (`cvextract/verifiers/`) that allows:
- **Interchangeable implementations**: Easy to swap or customize verification logic
- **Schema validation**: Validates against cvextract/contracts/cv_schema.json
- **Completeness checks**: Verifies extracted data for required fields
- **Roundtrip comparison**: Compares source and target data structures
- **External parameters**: Source and target data can be passed from outside
- **Testing flexibility**: Mock verifiers for testing without real data

See `cvextract/verifiers/README.md` for details on creating custom verifiers.


### What it does
- Reads a .docx directly from its WordprocessingML (XML) parts to extract content reliably without external converters.
- Produces a consistent JSON structure containing:
  - identity: title, full name, first name, last name (from the document header)
  - sidebar: categorized lists such as skills, languages, tools, certifications, industries, spoken languages, and academic background (from header/sidebar text boxes)
  - overview: free-text overview section (from the main document body)
  - experiences: a list of experience entries, each with a heading, description, and bullet points (from the main document body)

## CLI Interface

The stage-based interface uses explicit flags for each operation, making the pipeline clear and composable:

**Stages:**
- `--extract`: Extract CV data from DOCX to JSON
  - `source=<path>` - Input DOCX file(s) (required)
  - `output=<path>` - Output JSON path (optional, defaults to target_dir/structured_data/)

- `--adjust`: Adjust CV data for a specific customer using AI
  - `data=<path>` - Input JSON (optional if chained after --extract)
  - `customer-url=<url>` - Customer website URL for research
  - `output=<path>` - Output JSON path (optional)
  - `openai-model=<model>` - OpenAI model to use (optional, defaults to gpt-4o-mini)
  - `dry-run` - Only adjust without rendering (optional flag)

- `--apply`: Apply CV data to DOCX template
  - `template=<path>` - Template DOCX file (required)
  - `data=<path>` - Input JSON (optional if chained after --extract or --adjust)
  - `output=<path>` - Output DOCX path (optional, defaults to target_dir/documents/)

**Global options:**
- `--target <dir>` - Output directory (required)
- `--strict` - Treat warnings as failures
- `--debug` - Verbose logging with stack traces
- `--log-file <path>` - Optional log file path

**Examples:**

```bash
# Extract only
python -m cvextract.cli \
  --extract source=/path/to/cvs \
  --target /path/to/output

# Extract and apply
python -m cvextract.cli \
  --extract source=/path/to/cvs \
  --apply template=/path/to/template.docx \
  --target /path/to/output

# Extract, adjust for customer, and apply
export OPENAI_API_KEY="sk-proj-..."
python -m cvextract.cli \
  --extract source=/path/to/cvs \
  --adjust customer-url=https://example.com \
  --apply template=/path/to/template.docx \
  --target /path/to/output

# Apply to existing JSON
python -m cvextract.cli \
  --apply template=/path/to/template.docx data=/path/to/data.json \
  --target /path/to/output
```

### Customer Adjustment (OpenAI)
- When using the `--adjust` stage, the tool enriches the extracted JSON for a specific customer by:
  - Fetching basic info from the provided URL
  - Calling OpenAI with the original JSON to re-order bullets, emphasize relevant tools/industries, and tweak descriptions for relevance
  - Writing an `.adjusted.json` alongside the original and rendering from that adjusted JSON
- Environment:
  - `OPENAI_API_KEY`: required for adjustment
  - `OPENAI_MODEL`: optional (defaults to `gpt-4o-mini`)
- Roundtrip compare (JSON ↔ DOCX ↔ JSON) is intentionally skipped when adjustment is requested; the compare icon shows as `➖`.

### How it achieves this
- DOCX parsing:
  - Opens the .docx as a ZIP archive and parses:
    - word/document.xml for the main body paragraphs, including list detection via Word numbering properties.
    - word/header*.xml for header/sidebar content, prioritizing text inside text boxes (w:txbxContent), which is where sidebar layouts are typically stored.
- Section recognition:
  - Identifies “OVERVIEW” and “PROFESSIONAL EXPERIENCE” in the body to route content into the right fields.
  - Detects experience entry boundaries using date-range headings (e.g., “Jan 2020 – Present”) and/or Word heading styles.
  - Collects bullets and description text under each experience entry based on Word list formatting and paragraph grouping.
- Safe template rendering:
  - Sanitizes extracted strings to be XML-safe (handles raw ampersands, non-breaking spaces, and invalid XML 1.0 characters) before rendering.
  - Renders with docxtpl using auto-escaping and writes the output .docx to the target directory.

### Logging

The tool emits concise, human-readable logs suitable for batch processing
and automation. Detailed logging behavior is defined in the pipeline layer.


---

## Why Separate Data From Presentation?

By separating the **CV content** from the **way it looks**, we gain several benefits:

* **Easier migration** of consultants to the new CV formats also in the future
* **Consistency** across all CVs, regardless of who edits them
* **Faster updates** when the visual template changes—only the template needs to be updated, not every CV
* **Reusability** of the same CV data across:

  * multiple templates
  * client-specific branding
  * shortened or extended versions
  * different export formats (Word, PDF, HTML, etc.)
* **Reduced manual work** and elimination of copy-paste errors during CV updates

---

## Processing Steps

1. **Parses old CV Word documents**
2. **Extracts structured content** into a JSON format
3. **Validates the extracted information** (identity, sidebar, experiences, completeness)
4. **Produces clean machine-readable CV data**
5. **Applies this data to new Word templates** to generate updated CVs
6. **(Optional)** Adjusts JSON for a target customer before rendering when the flag is used