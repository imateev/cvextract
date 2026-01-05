# RunInput Integration

## Status
Planned (Phase-based implementation)

## Purpose

Comprehensive integration of the `RunInput` object across all workflow stages. This multi-phase effort evolves the `RunInput` introduced in PR #72 into the **single source of truth** for all per-run state and paths throughout the extract → adjust → apply pipeline.

## Overview

The `RunInput` object was introduced as an internal abstraction to encapsulate workflow input file paths and position the codebase for future metadata enrichment. This feature tracks the work to extend `RunInput` throughout the entire pipeline, ensuring all stages (extract, adjust, apply, parallel) use it consistently.

## Implementation Phases

The integration is split into 5 focused, sequential phases:

### Phase 1: [Issue #1] Extend RunInput Structure
Extend `RunInput` to track paths produced by each stage.

**File:** `01-extend-runinput-structure.md`  
**Dependencies:** PR #72

### Phase 2: [Issue #2] Extract Stage Integration
Update extract stage to accept and return `RunInput`.

**File:** `02-extract-stage-integration.md`  
**Dependencies:** Phase 1, PR #72

### Phase 3: [Issue #3] Adjust Stage Integration
Update adjust stage to work with `RunInput` as the single source of truth.

**File:** `03-adjust-stage-integration.md`  
**Dependencies:** Phase 1, Phase 2, PR #72

### Phase 4: [Issue #4] Apply/Render Stage Integration
Update apply/render stage to accept and return `RunInput`.

**File:** `04-apply-render-stage-integration.md`  
**Dependencies:** Phase 1, Phase 2, Phase 3, PR #72

### Phase 5: [Issue #5] Parallel Processing Integration
Thread `RunInput` through parallel processing pipeline.

**File:** `05-parallel-processing-integration.md`  
**Dependencies:** Phase 1, Phase 2, Phase 3, Phase 4, PR #72

## Data Flow (End State)

```
CLI Boundary
  ↓
RunInput.from_path(input_file)
  ↓
extract_single(run_input) 
  → updates run_input.extracted_json_path
  → returns updated run_input
  ↓
adjust_cv_data(run_input)
  → reads from run_input.get_current_json_path()
  → updates run_input.adjusted_json_path
  → returns updated run_input
  ↓
render_cv(run_input)
  → reads from run_input.get_current_json_path()
  → updates run_input.rendered_docx_path
  → returns updated run_input
  ↓
Final RunInput with all paths populated
```

## Success Criteria (All Phases)

✅ No stage accepts raw `Path` objects for workflow input/output paths  
✅ All stages accept and return `RunInput`  
✅ `RunInput` is the single source of truth for per-run state  
✅ Path carryover works correctly between stages  
✅ Adjuster chaining passes `RunInput` correctly  
✅ Parallel processing threads `RunInput` through workers  
✅ All tests pass; code coverage maintained  
✅ No changes to public CLI interface or behavior  

## Architecture Notes

### RunInput Fields (Phase 1)
- `file_path: Path` — original workflow input file
- `extracted_json_path: Optional[Path]` — set by extract stage
- `adjusted_json_path: Optional[Path]` — set by adjust stage
- `rendered_docx_path: Optional[Path]` — set by apply stage
- `metadata: Dict[str, Any]` — for future extensibility

### Helper Methods (Phase 1)
- `get_current_json_path()` — returns adjusted_json_path if set, else extracted_json_path
- `with_extracted_json()` — immutable update
- `with_adjusted_json()` — immutable update
- `with_rendered_docx()` — immutable update

### Stage Functions Return Pattern
Each stage function returns a tuple of (ok, errors, warnings, updated_run_input).

## File References

**Core:**
- `cvextract/run_input.py` — RunInput class

**Pipeline:**
- `cvextract/cli_execute.py` — CLI boundary and orchestration
- `cvextract/pipeline_helpers.py` — extract and render helpers
- `cvextract/pipeline_highlevel.py` — high-level extraction/rendering
- `cvextract/cli_parallel.py` — parallel processing

**Tests:**
- `tests/test_run_input.py` — RunInput core tests
- `tests/test_cli_execute.py` — integration tests
- `tests/test_pipeline_helpers.py` — helper function tests
- `tests/test_cli_parallel.py` — parallel processing tests

## Timeline

Phase implementation should follow the listed order. Each phase depends on successful completion of previous phases.

---

**See individual phase documents for detailed requirements and implementation guidance.**