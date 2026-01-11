# Named Adjusters

## Overview

The named adjusters feature provides a registry-based system for discovering and using CV adjusters by name, enabling pluggable adjustment implementations.

## Status

**Active** - Core adjustment infrastructure

## Description

The registry system allows:
1. Registration of adjuster implementations by name
2. Runtime lookup and instantiation of adjusters
3. Discovery via CLI `--list adjusters` command
4. Flexible parameter passing to adjuster constructors

## Entry Points

### Programmatic API

```python
from cvextract.adjusters import register_adjuster, get_adjuster, list_adjusters
from cvextract.adjusters import CVAdjuster

# Register custom adjuster
class MyAdjuster(CVAdjuster):
    def name(self) -> str:
        return "my-adjuster"
    
    def description(self) -> str:
        return "My custom adjuster"
    
    def adjust(self, cv_data, **kwargs):
        return cv_data  # Implementation

register_adjuster(MyAdjuster)

# Retrieve adjuster
adjuster = get_adjuster("my-adjuster", model="gpt-4")

# List all adjusters
adjusters = list_adjusters()
```

### CLI Usage

```bash
# List available adjusters
python -m cvextract.cli --list adjusters

# Use named adjuster
python -m cvextract.cli \
  --extract source=cv.docx \
  --adjust name=openai-company-research customer-url=https://example.com \
  --target output/
```

## Configuration

### Built-in Adjusters

- **`openai-company-research`**: Company-based CV adjustment
- **`openai-job-specific`**: Job-based CV adjustment
- **`openai-translate`**: Translation of CV JSON into a target language

### Registry Functions

- `register_adjuster(adjuster_class)`: Register an adjuster class
- `get_adjuster(name, **kwargs)`: Get adjuster instance by name
- `list_adjusters()`: List all registered adjusters

## Interfaces

### CVAdjuster Base Class

```python
class CVAdjuster(ABC):
    @abstractmethod
    def name(self) -> str:
        """Return the name of this adjuster."""
        pass
    
    @abstractmethod
    def description(self) -> str:
        """Return a description of this adjuster."""
        pass
    
    @abstractmethod
    def adjust(self, cv_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Adjust CV data based on parameters."""
        pass
    
    def validate_params(self, **kwargs) -> None:
        """Validate adjustment parameters (optional)."""
        pass
```

## Dependencies

### Internal Dependencies

- `cvextract.adjusters.base.CVAdjuster` - Base class

### Integration Points

- Used by `cvextract.cli_gather` for validation
- Used by `cvextract.cli_execute_adjust.execute()` for instantiation
- Used by `cvextract.cli` for `--list adjusters`

## Test Coverage

Tested in:
- `tests/test_adjuster_registry.py` - Registry functions
- `tests/test_adjusters.py` - Integration
- `tests/test_cli.py` - CLI integration

## Implementation History

The registry pattern enables extensibility and follows the same design as the extractor and renderer registries.

**Key Files**:
- `cvextract/adjusters/__init__.py` - Registry implementation
- `cvextract/adjusters/base.py` - Base class

## File Paths

- Registry: `cvextract/adjusters/__init__.py`
- Base Class: `cvextract/adjusters/base.py`
- Tests: `tests/test_adjuster_registry.py`
- Documentation: `cvextract/adjusters/README.md`

## Related Documentation

- [Adjustment Architecture](../README.md)
- [ML Adjustment](../ml-adjustment/README.md)
- [Job-Specific Adjuster](../job-specific-adjuster/README.md)
- Module README: `cvextract/adjusters/README.md`
