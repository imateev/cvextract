# cvextract Features Index

This document provides a comprehensive index of all features in the cvextract project, organized by functional area.

## Table of Contents

- [cvextract Features Index](#cvextract-features-index)
  - [Table of Contents](#table-of-contents)
  - [Extraction](#extraction)
    - [Features](#features)
  - [Adjustment](#adjustment)
    - [Features](#features-1)
  - [Rendering](#rendering)
    - [Features](#features-2)
  - [Verification](#verification)
    - [Features](#features-3)
  - [CLI](#cli)
    - [Features](#features-4)
  - [Contracts](#contracts)
    - [Features](#features-5)
  - [Templates](#templates)
    - [Features](#features-6)
  - [Examples](#examples)
    - [Features](#features-7)
  - [CI/CD](#cicd)
    - [Features](#features-8)
  - [Feature Status Legend](#feature-status-legend)
  - [Integration Map](#integration-map)
  - [Provenance Notes](#provenance-notes)

---

## Extraction

**Area Overview**: [specs/areas/extraction/README.md](areas/extraction/README.md)

The extraction area provides pluggable architecture for extracting structured CV data from various source formats.

### Features

| Feature | Status | Description | Entry Points | Config/Env |
|---------|--------|-------------|--------------|------------|
| [Default DOCX CV Extractor](areas/extraction/default-docx-cv-extractor/README.md) | Active | Default DOCX parser using WordprocessingML XML | `cvextract.extractors.DocxCVExtractor` | `name=default-docx-cv-extractor` (default) |
| [OpenAI Extractor](areas/extraction/openai-extractor/README.md) | Active | OpenAI-powered intelligent extraction for TXT/DOCX | `cvextract.extractors.OpenAICVExtractor` | `name=openai-extractor`, `OPENAI_API_KEY` |
| [Extractor Registry](areas/extraction/extractor-registry/README.md) | Active | Pluggable extractor registration and lookup system | `cvextract.extractors.{register_extractor, get_extractor, list_extractors}` | N/A |

---

## Adjustment

**Area Overview**: [specs/areas/adjustment/README.md](areas/adjustment/README.md)

The adjustment area provides ML-based CV optimization and transformation capabilities.

### Features

| Feature | Status | Description | Entry Points | Config/Env |
|---------|--------|-------------|--------------|------------|
| [Company Research Adjuster](areas/adjustment/company-research-adjuster/README.md) | Active | OpenAI-based CV adjustment with company research and caching | `cvextract.adjusters.OpenAICompanyResearchAdjuster` | `OPENAI_API_KEY`, `customer-url=<url>` |
| [Job-Specific Adjuster](areas/adjustment/job-specific-adjuster/README.md) | Active | Optimizes CV for specific job postings | `cvextract.adjusters.OpenAIJobSpecificAdjuster` | `job-url=<url>` or `job-description=<text>` |
| [Named Adjusters](areas/adjustment/named-adjusters/README.md) | Active | Registry-based adjuster lookup system | `cvextract.adjusters.{register_adjuster, get_adjuster, list_adjusters}` | `--adjust name=<adjuster-name>` |
| [Adjuster Chaining](areas/adjustment/adjuster-chaining/README.md) | Active | Sequential application of multiple adjusters | Multiple `--adjust` CLI flags | N/A |

---

## Rendering

**Area Overview**: [specs/areas/rendering/README.md](areas/rendering/README.md)

The rendering area provides pluggable architecture for rendering structured CV data to various output formats.

### Features

| Feature | Status | Description | Entry Points | Config/Env |
|---------|--------|-------------|--------------|------------|
| [DOCX Renderer](areas/rendering/docx-renderer/README.md) | Active | Renders CV data to DOCX using docxtpl/Jinja2 | `cvextract.renderers.DocxCVRenderer` or `get_renderer("default-docx-cv-renderer")` | `template=<path>` |
| [Pluggable Renderer Architecture](areas/rendering/pluggable-renderer-architecture/README.md) | Active | Abstract base class and registry for renderers | `cvextract.renderers.{CVRenderer, register_renderer, get_renderer, list_renderers}` | N/A |

---

## Verification

**Area Overview**: [specs/areas/verification/README.md](areas/verification/README.md)

The verification area provides data validation and quality checking capabilities.

### Features

| Feature | Status | Description | Entry Points | Config/Env |
|---------|--------|-------------|--------------|------------|
| [Extracted Data Verifier](areas/verification/extracted-data-verifier/README.md) | Active | Validates completeness and structure of extracted data | `cvextract.verifiers.DefaultExpectedCvDataVerifier` | N/A |
| [Roundtrip Verifier](areas/verification/comparison-verifiers/README.md) | Active | Compares data structures for roundtrip verification | `cvextract.verifiers.RoundtripVerifier` | N/A |
| [CV Schema Verifier](areas/verification/schema-verifier/README.md) | Active | Validates CV data against JSON schema | `cvextract.verifiers.DefaultCvSchemaVerifier` | `schema_path` parameter |
| [Verifier Registry](areas/verification/verifier-registry/README.md) | Active | Pluggable verifier registration and lookup system | `cvextract.verifiers.{register_verifier, get_verifier, list_verifiers}` | N/A |

---

## CLI

**Area Overview**: [specs/areas/cli/README.md](areas/cli/README.md)

The CLI area provides command-line interface with stage-based architecture and modern parameter syntax.

### Features

| Feature | Status | Description | Entry Points | Config/Env |
|---------|--------|-------------|--------------|------------|
| [Stage-Based Interface](areas/cli/stage-based-interface/README.md) | Active | Explicit flags for extract/adjust/render operations | `--extract`, `--adjust`, `--render` | N/A |
| [Batch Processing](areas/cli/batch-processing/README.md) | Active | Process multiple files recursively from directories | `source=<dir>` in extract/adjust/render | N/A |
| [Parallel Processing](areas/cli/parallel-processing/README.md) | Active | Multi-worker parallel file processing with progress indicator | `--parallel source=<dir> n=<workers> [file-type=<pattern>]` | N/A |
| [Directory Structure Preservation](areas/cli/directory-structure-preservation/README.md) | Active | Maintains source directory hierarchy in outputs | Automatic in batch/parallel modes | N/A |
| [Named Flags](areas/cli/named-flags/README.md) | Active | Modern key=value parameter syntax | `key=value` format for all parameters | N/A |

---

## Contracts

**Area Overview**: [specs/areas/contracts/README.md](areas/contracts/README.md)

The contracts area defines JSON schemas for data structures used throughout the application.

### Features

| Feature | Status | Description | Entry Points | Config/Env |
|---------|--------|-------------|--------------|------------|
| [CV Schema](areas/contracts/cv-schema/README.md) | Active | JSON Schema for CV data structure | `cvextract/contracts/cv_schema.json` | N/A |
| [Research Schema](areas/contracts/research-schema/README.md) | Active | JSON Schema for company research data | `cvextract/contracts/research_schema.json` | N/A |

---

## Templates

**Area Overview**: [specs/areas/templates/README.md](areas/templates/README.md)

The templates area provides Jinja2-based DOCX templating system and sample templates.

### Features

| Feature | Status | Description | Entry Points | Config/Env |
|---------|--------|-------------|--------------|------------|
| [Templating System](areas/templates/templating-system/README.md) | Active | Jinja2-based DOCX template rendering via docxtpl | Template files with `{{ }}` and `{% %}` syntax | N/A |
| [Sample Templates](areas/templates/sample-templates/README.md) | Active | Professional CV template examples | `examples/templates/CV_Template_Jinja2.docx` | N/A |

---

## Examples

**Area Overview**: [specs/areas/examples/README.md](areas/examples/README.md)

The examples area provides sample CVs and documentation for users.

### Features

| Feature | Status | Description | Entry Points | Config/Env |
|---------|--------|-------------|--------------|------------|
| [Sample CVs](areas/examples/sample-cvs/README.md) | Active | Example CV files for testing and demonstration | `examples/cvs/*.docx` | N/A |
| [Documentation](areas/examples/documentation/README.md) | Active | Template guides and usage documentation | `examples/templates/TEMPLATE_GUIDE.md` | N/A |

---

## CI/CD

**Area Overview**: [specs/areas/cicd/README.md](areas/cicd/README.md)

The CI/CD area covers continuous integration, deployment, and release automation.

### Features

| Feature | Status | Description | Entry Points | Config/Env |
|---------|--------|-------------|--------------|------------|
| [Automated Binary Releases](areas/cicd/automated-binary-releases/README.md) | Active | Automatic binary creation for macOS and Windows on version bumps | `.github/workflows/release.yml` | `bump2version`, `cvextract.spec` |

---

## Feature Status Legend

- **Active**: Feature is fully implemented and actively maintained
- **Deprecated**: Feature exists but is marked for removal
- **Experimental**: Feature is partially complete or in testing

---

## Integration Map

```
┌─────────────┐
│  CLI Layer  │ (stage-based interface, parallel processing)
└──────┬──────┘
       │
       ├──────> Extraction (private-internal, openai, registry)
       │              │
       │              v
       ├──────> [JSON Data + CV Schema]
       │              │
       │              v
       ├──────> Adjustment (company research, job-specific, chaining)
       │              │
       │              v
       ├──────> [Adjusted JSON Data]
       │              │
       │              v
       ├──────> Rendering (DOCX renderer, template system)
       │              │
       │              v
       └──────> Verification (data, schema, roundtrip verifier)

┌────────────────────────────────────────────────────────────────┐
│  CI/CD Pipeline  (automated binary releases)                   │
│                                                                 │
│  Version Bump → Create Release → Build Binaries → Upload       │
│  (bump2version)   (GitHub)        (PyInstaller)    (Releases)  │
└────────────────────────────────────────────────────────────────┘
```

---

## Provenance Notes

This feature index is derived from:
- Repository README.md (comprehensive CLI and feature documentation)
- Module-level README.md files in cvextract/extractors, cvextract/adjusters, cvextract/renderers, cvextract/verifiers, cvextract/contracts
- Source code analysis of implementation files
- CLI implementation in cvextract/cli*.py files
- Contract schemas in cvextract/contracts/*.json
- Example files in examples/ directory

All features documented here are grounded in actual implementation as of the current codebase state.
