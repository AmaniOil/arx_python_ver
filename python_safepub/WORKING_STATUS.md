# SafePub Python Port Working Status

This directory is the separate Python workspace for the SafePub port.

- Java source directory: `../src/`
- Python work directory: `./python_safepub/`
- Status: runnable first port complete

## Ported Components

- [x] SafePub parameter calculation: `(epsilon, delta) -> (beta, k)`
- [x] `(epsilon, delta)` differential privacy criterion wrapper
- [x] Beta-based subset sampling
- [x] Exponential mechanism for discrete candidate selection
- [x] Data-dependent SafePub-style search skeleton
- [x] Exponential-mechanism generalization-level selection for tabular data-dependent SafePub
- [x] Minimal tabular anonymization demo
- [x] Unit tests
- [x] CSV data and hierarchy loading
- [x] Simple CLI prompts for quasi-identifier hierarchy files
- [x] ARX-aligned Precision utility metric for the current no-suppression scope
- [x] ARX-style data-dependent search budget input, validation, and 10% default
- [x] Optional interactive prompt for data-dependent search budget ratio
- [x] Optional data-dependent search expansion limit
- [x] Explicitly keeps microaggregation out of the DP path, matching ARX validation

## Verification

Last verified with:

```bash
PYTHONPATH=python_safepub python3 -m unittest discover -s python_safepub/tests
PYTHONPATH=python_safepub python3 -m safepub.demo
PYTHONPATH=python_safepub python3 -m safepub.cli --help
```

The unit test command completed successfully with 27 tests.

## Notes

The Java source files are left untouched. All Python code and verification files for this work live under this directory.
