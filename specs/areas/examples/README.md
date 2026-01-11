# Examples Area

## Purpose

The examples area provides sample CVs and documentation to help users understand and test cvextract functionality.

## Features

- [Sample CVs](sample-cvs/README.md) - Example CV files for testing and demonstration
- [Documentation](documentation/README.md) - Template guides and usage documentation
- [Translation Example](translation-example/README.md) - Example of translate + render pipeline

## Architectural Notes

### Design Principles

1. **Learning by Example**: Concrete examples demonstrate features
2. **Testing**: Samples used in automated tests
3. **Documentation**: Examples serve as inline documentation
4. **Variety**: Different CV formats and structures

### Key Components

- **Sample CVs**: `examples/cvs/*.docx` - Ready-to-use example CVs
- **Template Guide**: `examples/templates/TEMPLATE_GUIDE.md` - Complete templating documentation
- **Templates**: `examples/templates/*.docx` - Sample templates
- **Translation Example**: `examples/translation/README.md` - Translate + render walkthrough

### Integration Points

- **Tests**: Sample CVs used in test suites
- **Documentation**: Referenced in README examples
- **Demos**: Used for feature demonstrations

## Dependencies

- **Internal**: Used by tests and documentation
- **External**: None (just data files and docs)

## File References

- Sample CVs: `examples/cvs/*.docx`
- Templates: `examples/templates/*.docx`
- Template Guide: `examples/templates/TEMPLATE_GUIDE.md`
- Translation Example: `examples/translation/README.md`
