## Project Overview

This project is an internal CV transformation pipeline designed to help the resourcing team migrate consultant CVs from the old Word template to the new one.

### Tool summary
This is a command-line tool that converts résumé/CV .docx files into a clean, structured JSON format and can optionally generate a new .docx by filling a Word template with that JSON.

## Installation

```bash
# Clone the repository
git clone https://github.com/imateev/cvextract.git
cd cvextract

# Install dependencies
pip install -e .
```

## Usage

The tool provides three main modes of operation:

### 1. Extract Mode - Extract CVs to JSON

Extract structured data from DOCX files and save as JSON:

```bash
python -m cvextract.cli \
  --mode extract \
  --source /path/to/cvs \
  --template /path/to/template.docx \
  --target /path/to/output
```

**Output**: Creates `structured_data/` directory with JSON files

### 2. Extract-Apply Mode - Extract and Render

Extract data from DOCX files and render to new DOCX using a template:

```bash
python -m cvextract.cli \
  --mode extract-apply \
  --source /path/to/cvs \
  --template /path/to/template.docx \
  --target /path/to/output
```

**Output**: 
- `structured_data/` - Extracted JSON files
- `documents/` - Rendered DOCX files
- `verification_structured_data/` - Round-trip verification JSON

### 3. Apply Mode - Render from Existing JSON

Apply a template to existing JSON files to generate DOCX:

```bash
python -m cvextract.cli \
  --mode apply \
  --source /path/to/json_files \
  --template /path/to/template.docx \
  --target /path/to/output
```

**Output**: Creates `documents/` directory with rendered DOCX files

### Additional Options

#### Strict Mode
Treat warnings as failures (non-zero exit code):
```bash
python -m cvextract.cli --mode extract --strict ...
```

#### Debug Mode
Enable verbose logs and stack traces:
```bash
python -m cvextract.cli --mode extract --debug ...
```

#### File Logging
Write output to a log file:
```bash
python -m cvextract.cli --mode extract --log-file logs/run.log ...
```

#### Customer Adjustment (OpenAI)
Adjust CV content for a specific customer using OpenAI:

```bash
export OPENAI_API_KEY="sk-proj-..."

python -m cvextract.cli \
  --mode extract-apply \
  --source /path/to/cvs \
  --template /path/to/template.docx \
  --target /path/to/output \
  --adjust-for-customer https://example.com/customer \
  --openai-model gpt-4o-mini
```

**Dry Run** - Save adjusted JSON without rendering:
```bash
python -m cvextract.cli \
  --mode extract-apply \
  --source /path/to/cvs \
  --template /path/to/template.docx \
  --target /path/to/output \
  --adjust-for-customer https://example.com/customer \
  --adjust-dry-run
```

### Command-Line Reference

```
python -m cvextract.cli --help
```

**Required Arguments:**
- `--mode` - Operation mode: `extract`, `extract-apply`, or `apply`
- `--source` - Input file or folder (.docx for extract*, .json for apply)
- `--template` - Template .docx file (single file)
- `--target` - Target output directory

**Optional Arguments:**
- `--strict` - Treat warnings as failure (non-zero exit code)
- `--debug` - Verbose logs + stack traces on failure
- `--log-file` - Path to log file
- `--adjust-for-customer` - URL to customer page for AI adjustment
- `--openai-model` - OpenAI model (default: gpt-4o-mini)
- `--adjust-dry-run` - Adjust and save JSON without rendering

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

### Core functions / modes
- extract:
  - Scans one .docx or a folder of .docx files and writes one JSON file per résumé.
- extract-apply:
  - Extracts JSON as above, then renders a new .docx for each input by applying a docxtpl template.
- apply:
  - Takes existing JSON files and renders new .docx files using a docxtpl template.

### Customer Adjustment (OpenAI)
- Optional flag `--adjust-for-customer <url>` enriches the extracted JSON for a specific customer by:
  - Fetching basic info from the provided URL
  - Calling OpenAI with the original JSON to re-order bullets, emphasize relevant tools/industries, and tweak descriptions for relevance
  - Writing an `.adjusted.json` alongside the original and rendering from that adjusted JSON
- Environment:
  - `OPENAI_API_KEY`: required for adjustment
  - `OPENAI_MODEL`: optional (defaults to `gpt-4o-mini`)
- Roundtrip compare (JSON ↔ DOCX ↔ JSON) is intentionally skipped when adjustment is requested; the compare icon shows as `➖`.

#### Example
```bash
export OPENAI_API_KEY="sk-proj-..."
python -m cvextract.cli \
  --mode extract-apply \
  --source /path/to/cvs \
  --template /path/to/template.docx \
  --target /path/to/output \
  --adjust-for-customer https://example.com/customer \
  --openai-model gpt-4o-mini
```

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