# Documentation

## Overview

The documentation feature provides comprehensive guides and reference materials for users to learn and use cvextract effectively.

## Status

**Active** - Core user documentation

## Description

Included documentation:
1. **TEMPLATE_GUIDE.md**: Complete guide to creating and using CV templates
2. **Main README.md**: Comprehensive project documentation with examples
3. **Module READMEs**: Documentation in each module directory

Features:
- Step-by-step guides
- Complete API reference
- Extensive examples
- Best practices
- Troubleshooting tips

## Entry Points

### Template Guide

Location: `examples/templates/TEMPLATE_GUIDE.md`

Content:
- Template variable reference
- Jinja2 syntax guide
- Editing instructions
- Advanced customization
- Troubleshooting

### Main README

Location: `README.md`

Content:
- Project overview
- CLI interface documentation
- Feature descriptions
- Usage examples
- Installation instructions

### Module Documentation

Locations:
- `cvextract/extractors/README.md`
- `cvextract/adjusters/README.md`
- `cvextract/renderers/README.md`
- `cvextract/verifiers/README.md`
- `cvextract/contracts/README.md`

## Configuration

### Documentation Structure

**Template Guide Sections**:
1. Overview
2. Template location and usage
3. Available template variables
4. Template data structure
5. Jinja2 filters
6. Editing instructions
7. Advanced customization
8. Output information
9. Troubleshooting

**Main README Sections**:
1. Project overview
2. License
3. Tool summary
4. CV data schema
5. Pluggable extractors
6. Pluggable renderers
7. Pluggable verifiers
8. CLI interface
9. CV adjustment with AI
10. Processing steps
11. Why separate data from presentation

## Interfaces

### Template Guide Usage

Users reference the guide when:
- Creating new templates
- Understanding template variables
- Debugging template issues
- Learning Jinja2 syntax

### README Usage

Users reference the README for:
- Getting started
- Understanding features
- CLI syntax and examples
- Architecture overview
- Integration patterns

## Dependencies

### Internal Dependencies

- References code examples from all modules
- Links to sample files
- Demonstrates features

### Integration Points

- Referenced in project documentation
- Used for onboarding new users
- Guides feature usage
- Supports troubleshooting

## Test Coverage

Validated through:
- Example commands tested in CI
- Template guide steps verified manually
- README examples kept up-to-date with code

## Implementation History

Documentation has evolved alongside the project:
- Initial: Basic README with setup instructions
- Refactoring: Module READMEs added for pluggable architecture
- Template Guide: Added when templating system introduced
- Continuous: Updated with each new feature

**Key Files**:
- `examples/templates/TEMPLATE_GUIDE.md`
- `README.md`
- `cvextract/*/README.md` (module docs)

## Documentation Best Practices

### Writing Guidelines

1. **Examples First**: Start with concrete examples
2. **Progressive**: Simple to complex
3. **Complete**: Include all parameters and options
4. **Tested**: Verify examples actually work
5. **Current**: Update when code changes

### Maintenance

- Update examples when CLI changes
- Add new features to main README
- Keep module docs in sync with code
- Test example commands regularly
- Update troubleshooting based on user issues

## Common Documentation Patterns

### CLI Examples

```bash
# Comment explaining what this does
python -m cvextract.cli \
  --extract source=file.docx \
  --target output/

# Output: /output/structured_data/file.json
```

### Programmatic Examples

```python
from cvextract.extractors import DocxCVExtractor
from pathlib import Path

# Clear comment
extractor = DocxCVExtractor()
cv_data = extractor.extract(Path("cv.docx"))
```

### Feature Documentation

1. Overview paragraph
2. When to use
3. Example usage
4. Configuration options
5. Advanced usage
6. Troubleshooting

## File Paths

- Template Guide: `examples/templates/TEMPLATE_GUIDE.md`
- Main README: `README.md`
- Module READMEs: `cvextract/*/README.md`
- Contributing: `.github/CONTRIBUTING.md`
- Support: `SUPPORT.md`
- Code of Conduct: `CODE_OF_CONDUCT.md`

## Related Documentation

- [Examples Architecture](../README.md)
- [Sample CVs](../sample-cvs/README.md)
- [Sample Templates](../../templates/sample-templates/README.md)
- All module READMEs
