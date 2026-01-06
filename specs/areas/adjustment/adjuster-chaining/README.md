# Adjuster Chaining

## Overview

Adjuster chaining allows sequential application of multiple adjusters, with each adjuster receiving the output of the previous one.

## Status

**Active** - Fully implemented in CLI

## Description

Chaining enables:
1. Multiple `--adjust` flags in a single command
2. Sequential adjuster execution (left-to-right order)
3. Data flow from one adjuster to the next
4. Combined optimizations (e.g., company + job-specific)

## Entry Points

### CLI Usage

```bash
export OPENAI_API_KEY="sk-proj-..."

# Chain company research and job-specific adjusters
python -m cvextract.cli \
  --extract source=cv.docx \
  --adjust name=openai-company-research customer-url=https://target-company.com \
  --adjust name=openai-job-specific job-url=https://target-company.com/careers/job/456 \
  --render template=template.docx \
  --target output/

# Data flow: Extract → Company Adjust → Job Adjust → Render
```

### Programmatic API

```python
import json
from pathlib import Path
from cvextract.adjusters import get_adjuster
from cvextract.cli_config import UserConfig, ExtractStage
from cvextract.shared import UnitOfWork

input_json = Path("cv.json")
config = UserConfig(target_dir=Path("out"), extract=ExtractStage(source=input_json))

# First adjuster
company_adjuster = get_adjuster("openai-company-research")
work = UnitOfWork(config=config, input=input_json, output=input_json)
cv_data = company_adjuster.adjust(work, customer_url="https://example.com")

# Persist adjusted data so the next adjuster can load it
intermediate = Path("cv_adjusted.json")
intermediate.write_text(json.dumps(cv_data, indent=2))

# Second adjuster reads the updated JSON
job_adjuster = get_adjuster("openai-job-specific")
work = UnitOfWork(config=config, input=intermediate, output=intermediate)
cv_data = job_adjuster.adjust(work, job_url="https://example.com/job/123")
```

## Configuration

### CLI Syntax

```bash
--adjust name=<adjuster1> <params1...> \
--adjust name=<adjuster2> <params2...> \
--adjust name=<adjuster3> <params3...>
```

Each `--adjust` flag can have different:
- Adjuster names
- Parameters
- OpenAI models

### Execution Order

Adjusters execute in the order they appear on the command line (left-to-right).

## Interfaces

### Data Flow

```
Extract
  │
  v
Original CV JSON
  │
  v
Adjuster 1 (company research)
  │
  v
Adjusted CV JSON (company-optimized)
  │
  v
Adjuster 2 (job-specific)
  │
  v
Adjusted CV JSON (company+job optimized)
  │
  v
Apply/Render
```

### Output Paths

When multiple adjusters are chained:
- Intermediate results are not saved by default
- Only final adjusted JSON is saved to `{target}/adjusted_structured_data/`
- Research caches are saved independently per adjuster

## Dependencies

### Internal Dependencies

- `cvextract.cli_gather.AdjustmentSpec` - Stores adjustment configurations
- `cvextract.cli_execute.execute_pipeline()` - Chains adjusters

### Integration Points

- Implemented in `cvextract.cli_gather._parse_adjustment_specs()`
- Executed in `cvextract.cli_execute.execute_pipeline()`

## Test Coverage

Tested in:
- `tests/test_cli.py` - CLI chaining syntax
- `tests/test_pipeline.py` - End-to-end chaining
- `tests/test_adjusters.py` - Manual chaining

## Implementation History

Chaining was implemented as part of the named adjusters refactoring to enable flexible, composable CV optimization workflows.

**Key Files**:
- `cvextract/cli_gather.py` - Multiple adjustment specs parsing
- `cvextract/cli_execute.py` - Sequential adjuster execution

## Open Questions

1. **Intermediate Outputs**: Should we optionally save intermediate adjuster outputs?
2. **Rollback**: Should we support undo/rollback if an adjuster fails?
3. **Parallel**: Could some adjusters run in parallel instead of sequentially?
4. **Caching**: Should we cache the entire chain result?

## Use Cases

### Company + Job Optimization

```bash
# Optimize for both company culture and specific role
python -m cvextract.cli \
  --extract source=cv.docx \
  --adjust name=openai-company-research customer-url=https://company.com \
  --adjust name=openai-job-specific job-url=https://company.com/job/123 \
  --render template=template.docx \
  --target output/
```

### Different Models Per Adjuster

```bash
# Use GPT-4 for company research, GPT-3.5 for job-specific
python -m cvextract.cli \
  --extract source=cv.docx \
  --adjust name=openai-company-research customer-url=https://company.com openai-model=gpt-4 \
  --adjust name=openai-job-specific job-url=https://company.com/job/123 openai-model=gpt-3.5-turbo \
  --target output/
```

### Custom Adjuster Chain

```python
# Register custom adjusters and chain them
from cvextract.adjusters import register_adjuster, get_adjuster

register_adjuster(MyCustomAdjuster1)
register_adjuster(MyCustomAdjuster2)

# Chain via CLI
# --adjust name=custom1 param1=value1 \
# --adjust name=custom2 param2=value2
```

## File Paths

- CLI Parsing: `cvextract/cli_gather.py` (function: `_parse_adjustment_specs`)
- Execution: `cvextract/cli_execute.py` (in `execute_pipeline`)
- Tests: `tests/test_cli.py`, `tests/test_pipeline.py`
- Documentation: Main README.md (section: "Chaining Multiple Adjusters")

## Related Documentation

- [Adjustment Architecture](../README.md)
- [Named Adjusters](../named-adjusters/README.md)
- [Job-Specific Adjuster](../job-specific-adjuster/README.md)
- Main README: "Chaining Multiple Adjusters" section
