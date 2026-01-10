# Extractor Registry

## Overview

The extractor registry provides a centralized registration and lookup system for CV extractors, enabling pluggable, interchangeable extraction implementations.

## Status

**Active** - Core infrastructure for extraction subsystem

## Description

The registry system allows:
1. **Registration**: Extractor implementations register themselves by name
2. **Lookup**: Retrieve extractor instances by name at runtime
3. **Discovery**: List all available extractors with descriptions
4. **Factory Pattern**: Create extractor instances with configuration

This enables the CLI and pipeline to dynamically select extractors without hard-coded dependencies.

## Entry Points

### Programmatic API

```python
from cvextract.extractors import register_extractor, get_extractor, list_extractors
from cvextract.extractors import CVExtractor
from cvextract.shared import UnitOfWork

# Register a custom extractor
class MyExtractor(CVExtractor):
    def extract(self, work: UnitOfWork) -> UnitOfWork:
        # Implementation
        pass

register_extractor("my-extractor", MyExtractor)

# Retrieve extractor
extractor = get_extractor("my-extractor")

# List all extractors
extractors = list_extractors()
# Returns: [{"name": "default-docx-cv-extractor", "description": "..."}, ...]
```

### CLI Usage

```bash
# List available extractors
python -m cvextract.cli --list extractors

# Use specific extractor
python -m cvextract.cli \
  --extract source=cv.docx name=openai-extractor \
  --target output/
```

## Configuration

### Registry Functions

- **`register_extractor(name: str, extractor_class: Type[CVExtractor])`**: Register an extractor
- **`get_extractor(name: str) -> Optional[CVExtractor]`**: Retrieve extractor instance
- **`list_extractors() -> List[Dict[str, str]]`**: List all registered extractors

### Built-in Registrations

In `cvextract/extractors/__init__.py`:

```python
register_extractor("default-docx-cv-extractor", DocxCVExtractor)
register_extractor("openai-extractor", OpenAICVExtractor)
```

## Interfaces

### CVExtractor Base Class

All extractors must inherit from `CVExtractor` and implement:

```python
class CVExtractor(ABC):
    @abstractmethod
    def extract(self, work: UnitOfWork) -> UnitOfWork:
        """Extract CV data and write JSON to the Extract step output."""
        pass
    
    def name(self) -> str:
        """Return the name of this extractor."""
        return self.__class__.__name__
    
    def description(self) -> str:
        """Return a description of this extractor."""
        return ""
```

### Registry Storage

- **Global Dictionary**: `_EXTRACTOR_REGISTRY: Dict[str, Type[CVExtractor]]`
- **Thread Safety**: Not explicitly thread-safe (registrations happen at module import time)

## Dependencies

### Internal Dependencies

- `cvextract.extractors.base.CVExtractor` - Base class for all extractors

### External Dependencies

None (pure Python)

### Integration Points

- Used by `cvextract.cli_gather` to validate and select extractors
- Used by `cvextract.pipeline_helpers.extract_single` to instantiate extractors
- Used by `cvextract.cli` for `--list extractors` command

## Test Coverage

Tested in:
- `tests/test_extractor_registry.py` - Registry functions
- `tests/test_extractors.py` - Integration with extractors
- `tests/test_cli.py` - CLI integration

## Implementation History

### Initial Implementation

The registry pattern was introduced as part of the pluggable architecture refactoring to enable:
- Runtime extractor selection
- Extensibility without modifying core code
- CLI-driven extractor discovery

**Key Files**:
- `cvextract/extractors/extractor_registry.py` - Registry implementation
- `cvextract/extractors/base.py` - Base class definition
- `cvextract/extractors/__init__.py` - Built-in extractor registrations

## Open Questions

1. **Validation**: Should we validate extractor implementations at registration time?
2. **Versioning**: Should we support multiple versions of the same extractor?
3. **Configuration**: Should extractors declare their configuration schema?
4. **Priority**: Should we support extractor priorities or fallback chains?

## Extension Examples

### Custom Extractor Registration

```python
from cvextract.cli_config import UserConfig
from cvextract.extractors import CVExtractor, register_extractor
from cvextract.shared import UnitOfWork
from pathlib import Path

class PdfCVExtractor(CVExtractor):
    def extract(self, work: UnitOfWork) -> UnitOfWork:
        # PDF extraction logic
        data = {
            "identity": {...},
            "sidebar": {...},
            "overview": "...",
            "experiences": [...]
        }
        return self._write_output_json(work, data)
    
    def name(self) -> str:
        return "pdf-extractor"
    
    def description(self) -> str:
        return "Extract CV data from PDF files"

# Register
register_extractor("pdf-extractor", PdfCVExtractor)

# Use
from cvextract.extractors import get_extractor
extractor = get_extractor("pdf-extractor")
work = UnitOfWork(
    config=UserConfig(target_dir=Path("outputs")),
    input=Path("cv.pdf"),
    output=Path("outputs/cv.json"),
)
extractor.extract(work)
```

### Dynamic Extractor Loading

```python
# In a plugin system
import importlib

def load_extractor_plugin(module_name: str):
    """Load extractor from external module."""
    module = importlib.import_module(module_name)
    # Plugin module should call register_extractor() on import
    
# Use
load_extractor_plugin("my_extractors.pdf")
extractor = get_extractor("pdf-extractor")
```

## File Paths

- Implementation: `cvextract/extractors/extractor_registry.py`
- Base Class: `cvextract/extractors/base.py`
- Public API: `cvextract/extractors/__init__.py`
- Tests: `tests/test_extractor_registry.py`

## Related Documentation

- [Extractor Architecture](../README.md)
- [Default DOCX CV Extractor](../default-docx-cv-extractor/README.md)
- [OpenAI Extractor](../openai-extractor/README.md)
- Module README: `cvextract/extractors/README.md`
