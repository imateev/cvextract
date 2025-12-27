# Test Coverage Instructions

The test coverage for `pipeline.py` is at 99%. If your VS Code coverage tool shows lower coverage, you need to regenerate the coverage files.

## Regenerate Coverage Files

Run these commands in the repository root:

```bash
# Install dependencies
pip install -e . pytest pytest-cov

# Generate coverage files (JSON and XML for VS Code)
python -m pytest tests/ --cov=cvextract --cov-report=xml --cov-report=json --cov-report=term

# Or specifically for pipeline.py:
python -m pytest tests/ --cov=cvextract.pipeline --cov-report=xml --cov-report=json --cov-report=term
```

## Expected Results

- **pipeline.py**: 99% coverage (222 statements, 3 missing)
- Missing lines: 91-92 (exception handler), 183 (continue statement)
- Lines 280-320 in `run_apply_mode`: 100% covered

## VS Code Coverage Extension

If using the Coverage Gutters extension:
1. Run the command above to generate `coverage.xml`
2. Click "Watch" in the Coverage Gutters status bar
3. The coverage should update automatically

If coverage doesn't update:
1. Close and reopen the file
2. Run "Coverage Gutters: Display Coverage" command (Ctrl+Shift+P)
3. Ensure `coverage.xml` is in the project root

## Verify Coverage

Check specific lines in `run_apply_mode` (267-338):
```bash
python -m pytest tests/test_pipeline_complete_coverage.py::TestRunApplyModeComplete --cov=cvextract.pipeline --cov-report=term-missing
```

All lines in the 280-320 range should show as covered.
