## Project Overview

[![CI](https://github.com/imateev/cvextract/actions/workflows/ci.yml/badge.svg)](https://github.com/imateev/cvextract/actions/workflows/ci.yml) [![codecov](https://codecov.io/gh/imateev/cvextract/graph/badge.svg?token=PRBIB4KCWE)](https://codecov.io/gh/imateev/cvextract)

[![codecov](https://codecov.io/gh/imateev/cvextract/graphs/tree.svg?token=PRBIB4KCWE)](https://codecov.io/gh/imateev/cvextract)

cvextract is a command-line tool for extracting structured data from CV `.docx` files that conform to a very specific, predefined input format. It can optionally re-render the extracted data into a new `.docx` template based on the extracted structure.

The tool is not intended to handle arbitrary CV layouts out of the box. Instead, it focuses on deterministic, schema-driven extraction for known document structures. Thanks to its pluggable architecture, however, cvextract can be extended with additional extractors, renderers, or verifiers to support other formats and workflows.

This project started as a small, three-day after-hours effort to help a resourcing team migrate consultant CVs from a legacy Word template to a new standardized format. It has since evolved into a standalone playground for experimenting with CV parsing, transformation, and document rendering workflows, and is now published as an open-source project.

## License
Copyright 2025 Ivo Mateev  
Licensed under the Apache License, Version 2.0


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

The CLI uses a stage-based architecture with explicit flags for each operation. Stages can be chained together or run independently, making the pipeline clear and composable.

### Parameter Syntax

All CLI parameters use the modern `key=value` format:

```bash
python -m cvextract.cli \
  --extract source=/path/to/cv.docx \
  --adjust name=openai-company-research customer-url=https://example.com \
  --apply template=/path/to/template.docx \
  --target /output
```

**Key features:**
- Each flag (`--extract`, `--adjust`, `--apply`) is followed by one or more `key=value` parameters
- Parameters are space-separated: `--extract source=file.docx output=data.json`
- Values can contain spaces: `source=/path with spaces/file.docx`
- Multiple `--adjust` flags can be used to chain adjusters sequentially
- Boolean flags have no value: `--adjust name=... dry-run`

### Execution Modes

**Single-file mode** (default) - Process one file at a time:
```bash
python -m cvextract.cli --extract source=<file> [--adjust ...] [--apply ...] --target <dir> [options]
```

**Batch mode** - Process multiple files in parallel:
```bash
python -m cvextract.cli --parallel input=<dir> n=<num_workers> [--extract] [--adjust ...] [--apply ...] --target <dir> [options]
```

### Stage Chaining

When stages are chained together, **the output of each stage automatically becomes the input to the next stage**:

- **Extract → Adjust**: The extracted JSON is automatically passed to the adjust stage (no need to specify `data=`)
- **Adjust → Apply**: The adjusted JSON is automatically passed to the apply stage
- **Extract → Apply** (no adjust): The extracted JSON is automatically passed to the apply stage

The `data=` parameter in `--adjust` and `--apply` is only needed when you want to process **pre-existing JSON files without extraction**. When stages are chained, this parameter is ignored.

Example of automatic chaining:
```bash
python -m cvextract.cli \
  --extract source=/path/to/cv.docx \
  --adjust customer-url=https://example.com \
  --apply template=/path/to/template.docx \
  --target /output

# Flow: DOCX → Extract JSON → Adjust JSON → Apply to template
# No explicit data= parameters needed
```

### Stages

**`--extract`**: Extract CV data from DOCX to JSON
- `source=<path>` - Input DOCX file or directory (required in single-file mode)
  - Single file: processes one file
  - Directory: processes all `.docx` files recursively
- `output=<path>` - Output JSON path (optional, defaults to `{target}/structured_data/`)

**`--adjust`**: Adjust CV data using named adjusters (can be specified multiple times for chaining)
- `name=<adjuster-name>` - Name of the adjuster to use (required, see `--list adjusters` for available adjusters)
- Adjuster-specific parameters (varies by adjuster):
  - For `openai-company-research`: `customer-url=<url>` (required)
  - For `openai-job-specific`: `job-url=<url>` OR `job-description=<text>` (one required)
- `data=<path>` - Input JSON file or directory (only used when NOT chained after extract)
  - When chained after extract, this is ignored and the extracted JSON is used automatically
  - Single file: processes one file
  - Directory: processes all `.json` files recursively
- `output=<path>` - Output JSON path (optional, defaults to `{target}/adjusted_structured_data/`)
- `openai-model=<model>` - OpenAI model to use (optional, defaults to `gpt-4o-mini`)
- `dry-run` - Only adjust without rendering (optional flag, prevents apply stage execution)
- **Chaining**: Multiple `--adjust` flags can be specified to chain adjusters in sequence

**`--apply`**: Apply CV data to DOCX template
- `template=<path>` - Template DOCX file (required for apply stage)
- `data=<path>` - Input JSON file or directory (only used when NOT chained after extract/adjust)
  - When chained after extract or adjust, this is ignored and the JSON from the previous stage is used automatically
  - Single file: applies to one template
  - Directory: applies all matching JSON files
- `output=<path>` - Output DOCX path (optional, defaults to `{target}/documents/`)

**`--parallel`**: Batch processing mode (alternative to single-file stages)
- `input=<dir>` - Input directory containing DOCX files (required)
- `n=<num>` - Number of worker processes (required, e.g., `n=10`)
- When used, stages like `--extract`, `--adjust`, `--apply` still apply but work in parallel
- Each worker processes files independently using the same stage configuration

### Global Options

- `--target <dir>` - Output directory (required unless using `--list`)
- `--list {adjusters,renderers,extractors}` - List available components and exit
- `--strict` - Treat warnings as errors (exit code 2)
- `--debug` - Verbose logging with stack traces
- `--log-file <path>` - Optional log file path for persistent logging

### Listing Available Components

Use `--list` to see available adjusters, renderers, or extractors:

```bash
# List all available adjusters
python -m cvextract.cli --list adjusters

# List available renderers
python -m cvextract.cli --list renderers

# List available extractors
python -m cvextract.cli --list extractors
```

### Examples

#### Single-File Extraction

```bash
# Extract one CV file with default output location
python -m cvextract.cli \
  --extract source=/path/to/cv.docx \
  --target /output

# Output: /output/structured_data/cv.json
```

#### Single-File with Custom Output

```bash
# Extract with relative output path
python -m cvextract.cli \
  --extract source=/path/to/cv.docx output=custom/location.json \
  --target /output

# Output: /output/custom/location.json
```

```bash
# Extract with absolute output path (ignores --target for this output)
python -m cvextract.cli \
  --extract source=/path/to/cv.docx output=/absolute/path/data.json \
  --target /output

# Output: /absolute/path/data.json
```

#### Extract + Apply (Render CV)

```bash
# Extract and apply to template with default output structure
python -m cvextract.cli \
  --extract source=/path/to/cv.docx \
  --apply template=/path/to/template.docx \
  --target /output

# Outputs:
#   /output/structured_data/cv.json
#   /output/documents/cv_NEW.docx
```

```bash
# Extract and apply with custom output paths
python -m cvextract.cli \
  --extract source=/path/to/cv.docx output=json/extracted.json \
  --apply template=/path/to/template.docx output=final/result.docx \
  --target /output

# Outputs:
#   /output/json/extracted.json
#   /output/final/result.docx
```

#### Extract + Adjust + Apply (With Customer Research)

```bash
# Full pipeline: extract, adjust for customer, then apply
export OPENAI_API_KEY="sk-proj-..."

python -m cvextract.cli \
  --extract source=/path/to/cv.docx \
  --adjust name=openai-company-research customer-url=https://example.com \
  --apply template=/path/to/template.docx \
  --target /output

# Outputs:
#   /output/structured_data/cv.json (original)
#   /output/adjusted_structured_data/cv.json (customer-optimized)
#   /output/documents/cv_NEW.docx (from adjusted JSON)
#   /output/research_data/cv/example_com.json (cached research)
```

```bash
# Adjust with custom OpenAI model
python -m cvextract.cli \
  --extract source=/path/to/cv.docx \
  --adjust name=openai-company-research customer-url=https://example.com openai-model=gpt-4 \
  --apply template=/path/to/template.docx \
  --target /output
```

#### Adjust Only (Dry-Run - No Rendering)

```bash
# Extract and adjust without applying (useful for preview/testing)
export OPENAI_API_KEY="sk-proj-..."

python -m cvextract.cli \
  --extract source=/path/to/cv.docx \
  --adjust name=openai-company-research customer-url=https://example.com dry-run \
  --target /output

# Outputs:
#   /output/structured_data/cv.json (original)
#   /output/adjusted_structured_data/cv.json (customer-optimized)
#   No DOCX file generated
```

#### Adjust from Existing JSON

```bash
# Adjust pre-extracted JSON without re-extracting
export OPENAI_API_KEY="sk-proj-..."

python -m cvextract.cli \
  --adjust name=openai-company-research data=/path/to/extracted.json customer-url=https://example.com \
  --apply template=/path/to/template.docx \
  --target /output

# Outputs:
#   /output/adjusted_structured_data/extracted.json
#   /output/documents/extracted_NEW.docx
```

#### Apply Only (From Existing JSON)

```bash
# Apply pre-adjusted JSON to template (no extraction or adjustment)
python -m cvextract.cli \
  --apply template=/path/to/template.docx data=/path/to/data.json \
  --target /output

# Output: /output/documents/data_NEW.docx
```

#### Named Adjusters (New Interface)

```bash
# Use explicit adjuster name (recommended for clarity)
export OPENAI_API_KEY="sk-proj-..."

python -m cvextract.cli \
  --extract source=/path/to/cv.docx \
  --adjust name=openai-company-research customer-url=https://example.com \
  --apply template=/path/to/template.docx \
  --target /output

# Outputs:
#   /output/structured_data/cv.json (original)
#   /output/adjusted_structured_data/cv.json (company-optimized)
#   /output/documents/cv_NEW.docx
#   /output/research_data/example_com.json (cached research)
```

#### Job-Specific Adjustment

```bash
# Adjust CV for a specific job posting
export OPENAI_API_KEY="sk-proj-..."

python -m cvextract.cli \
  --extract source=/path/to/cv.docx \
  --adjust name=openai-job-specific job-url=https://careers.example.com/job/123 \
  --apply template=/path/to/template.docx \
  --target /output

# Or use job description directly
python -m cvextract.cli \
  --extract source=/path/to/cv.docx \
  --adjust name=openai-job-specific job-description="Senior Software Engineer position..." \
  --apply template=/path/to/template.docx \
  --target /output
```

#### Chaining Multiple Adjusters

```bash
# Chain adjusters: first company research, then job-specific
export OPENAI_API_KEY="sk-proj-..."

python -m cvextract.cli \
  --extract source=/path/to/cv.docx \
  --adjust name=openai-company-research customer-url=https://target-company.com \
  --adjust name=openai-job-specific job-url=https://target-company.com/careers/job/456 \
  --apply template=/path/to/template.docx \
  --target /output

# Flow: DOCX → Extract → Adjust (company) → Adjust (job) → Apply to template
# Each adjuster receives the output of the previous one
# Final output is doubly-optimized for both company and job
```

```bash
# Use different models for different adjusters
export OPENAI_API_KEY="sk-proj-..."

python -m cvextract.cli \
  --extract source=/path/to/cv.docx \
  --adjust name=openai-company-research customer-url=https://example.com openai-model=gpt-4 \
  --adjust name=openai-job-specific job-url=https://example.com/job/123 openai-model=gpt-3.5-turbo \
  --apply template=/path/to/template.docx \
  --target /output
```

#### Batch Processing - Extract Multiple Files

```bash
# Extract all CVs from a directory in parallel (10 workers)
python -m cvextract.cli \
  --parallel input=/path/to/cv_folder n=10 \
  --extract \
  --target /output

# Processes all .docx files in /path/to/cv_folder recursively
# Outputs: /output/structured_data/{preserved_directory_structure}/{filename}.json
```

#### Batch Processing - Extract + Apply

```bash
# Extract and render all CVs in parallel (20 workers)
python -m cvextract.cli \
  --parallel input=/path/to/cv_folder n=20 \
  --extract \
  --apply template=/path/to/template.docx \
  --target /output

# Processes all .docx files recursively
# Outputs:
#   /output/structured_data/{structure}/{filename}.json
#   /output/documents/{structure}/{filename}_NEW.docx
```

#### Batch Processing - Extract + Adjust + Apply

```bash
# Full pipeline for entire folder in parallel
export OPENAI_API_KEY="sk-proj-..."

python -m cvextract.cli \
  --parallel input=/data/consultants n=15 \
  --extract \
  --adjust name=openai-company-research customer-url=https://target-company.com \
  --apply template=/path/to/template.docx \
  --target /output

# Processes all CVs in parallel
# Outputs:
#   /output/structured_data/{structure}/{filename}.json (originals)
#   /output/adjusted_structured_data/{structure}/{filename}.json (adjusted)
#   /output/documents/{structure}/{filename}_NEW.docx (rendered)
#   /output/research_data/{structure}/{filename}/target_company_com.json (cached research)
```

#### Error Handling and Logging

```bash
# Run with strict mode (warnings treated as errors, exit code 2)
python -m cvextract.cli \
  --extract source=/path/to/cv.docx \
  --apply template=/path/to/template.docx \
  --target /output \
  --strict

# Exit code: 0 (success), 1 (failures), 2 (warnings in strict mode)
```

```bash
# Run with debug logging and persistent log file
python -m cvextract.cli \
  --extract source=/path/to/cv.docx \
  --target /output \
  --debug \
  --log-file /path/to/cvextract.log

# Logs stack traces and detailed diagnostics to console and file
```

```bash
# Batch processing with debug logging
python -m cvextract.cli \
  --parallel input=/data/cvs n=10 \
  --extract \
  --apply template=/path/to/template.docx \
  --target /output \
  --debug \
  --log-file /output/batch_processing.log
```

#### Complex Directory Structure Preservation

```bash
# Extract maintaining source directory structure
# Source: /source/teams/backend/engineer1.docx, /source/teams/backend/engineer2.docx
# Output structure will be:
#   /output/structured_data/teams/backend/engineer1.json
#   /output/structured_data/teams/backend/engineer2.json

python -m cvextract.cli \
  --extract source=/source \
  --target /output
```

#### Mixed Batch Processing with Custom Outputs

```bash
# Batch process but save adjusted data to custom location
export OPENAI_API_KEY="sk-proj-..."

python -m cvextract.cli \
  --parallel input=/source/cvs n=12 \
  --extract \
  --adjust name=openai-company-research customer-url=https://example.com output=/custom/adjusted/ \
  --apply template=/path/to/template.docx \
  --target /output

# Outputs:
#   /output/structured_data/{structure}/{filename}.json
#   /custom/adjusted/{structure}/{filename}.json (custom location)
#   /output/documents/{structure}/{filename}_NEW.docx
```

### CV Adjustment with AI

The tool supports pluggable CV adjusters that can modify CV content for different purposes:

#### Available Adjusters

Use `--list adjusters` to see all available adjusters:

1. **`openai-company-research`** - Adjusts CV based on target company research
   - Researches the company from its website
   - Emphasizes relevant experience, skills, and technologies
   - Reorders content to highlight company-aligned qualifications
   - Parameters: `customer-url=<url>` (required)

2. **`openai-job-specific`** - Adjusts CV for a specific job posting
   - Analyzes job requirements and responsibilities
   - Highlights matching experience and skills
   - Adjusts terminology to match job description
   - Parameters: `job-url=<url>` OR `job-description=<text>` (one required)

#### How Adjustment Works

- Adjusters can be chained together by specifying multiple `--adjust` flags
- Each adjuster receives the output of the previous one in the chain
- The final adjusted JSON is saved to `{target}/adjusted_structured_data/`
- All adjustments preserve the original CV schema and data integrity
- Adjusters never invent new experience or qualifications

#### Environment Requirements

- `OPENAI_API_KEY`: Required for OpenAI-based adjusters
- `OPENAI_MODEL`: Optional, defaults to `gpt-4o-mini` (can be overridden per-adjuster)

#### Behavior Notes

- Company research results are cached in `{target}/research_data/` for reuse
- Roundtrip comparison (JSON ↔ DOCX ↔ JSON) is intentionally skipped when adjustment is used; the compare icon shows as `➖`
- In dry-run mode, adjustment is performed but rendering is skipped

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