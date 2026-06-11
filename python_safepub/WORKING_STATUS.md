# SafePub Python Port Working Status

This directory is the separate Python workspace for the SafePub port.

- Java source directory: `../src/`
- Python work directory: `./python_safepub/`
- Status: runnable port aligned with ARX's SafePub flow (incl. suppression)

## Ported Components

- [x] SafePub parameter calculation: `(epsilon, delta) -> (beta, k)`
- [x] `(epsilon, delta)` differential privacy criterion wrapper
- [x] Beta-based subset sampling
- [x] Exponential mechanism for discrete candidate selection
- [x] Data-dependent SafePub search over the full local lattice (no data-dependent candidate filtering), mirroring `DataDependentEDDPAlgorithm`
- [x] All six ARX SafePub score functions with record suppression (incl. the non-sampled `pcount - count` term): Precision, Loss (domain shares), Discernibility, Non-uniform entropy (root-value handling), AECS, Classification (response variables, QI and non-QI targets)
- [x] Record suppression: sampled records in classes smaller than `k` and non-sampled records are released as fully suppressed rows (ARX with a 100% suppression limit)
- [x] ARX-style output rows: one output row per input record
- [x] Optimum tracking with ARX's tiebreak (equal score -> lower transformation level)
- [x] Data-independent SafePub via fixed `DataGeneralizationScheme`-style levels/degrees (no search)
- [x] Minimal tabular anonymization demo
- [x] Unit tests (41)
- [x] CSV data and hierarchy loading
- [x] Simple CLI prompts for quasi-identifier hierarchy files
- [x] ARX-aligned Precision utility metric including suppression, normalized by the sampled-subset size
- [x] ARX-style data-dependent search budget input, validation, and 10% default
- [x] Optional interactive prompt for data-dependent search budget ratio
- [x] Optional data-dependent search expansion limit
- [x] Explicitly keeps microaggregation out of the DP path, matching ARX validation

## Verification

Last verified on Windows (PowerShell, Python 3.13):

```powershell
$env:PYTHONPATH = 'python_safepub'
python -m unittest discover -s python_safepub/tests
python -m safepub.demo
python -m safepub.cli --help
```

The unit test command completed successfully with 58 tests. The adult-data
CLI run was regenerated with the corrected flow (see
`outputs/adult_safepub_report.md`), and all six score functions were
smoke-tested on the adult dataset.

## Notes

The Java source files are left untouched. All Python code and verification
files for this work live under this directory.

Known intentional deviations from ARX (documented in the README):

- Regular `float` arithmetic instead of ARX's interval arithmetic (Java uses
  `BigFraction` inside the score functions).
- The default data-dependent expansion limit is the local lattice size minus
  one (ARX requires the caller to set a finite step limit).
- Conventional information loss is ported for Precision only; the other
  quality models contribute their SafePub score functions (which is all the
  data-dependent DP path uses). The reference information-loss line is
  therefore always `arx_precision`.
