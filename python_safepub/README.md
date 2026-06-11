# SafePub Python Port

This is a standalone Python workspace for porting the SafePub-related parts of ARX.

> 日本語の使い方ガイドは [HOW_TO_USE.md](HOW_TO_USE.md) を参照してください。
> (Japanese usage guide: [HOW_TO_USE.md](HOW_TO_USE.md))

The implementation mirrors the ARX Java components at a practical Python level:

- `org.deidentifier.arx.dp.ParameterCalculation`
- `org.deidentifier.arx.criteria.EDDifferentialPrivacy`
- `org.deidentifier.arx.dp.ExponentialMechanism`
- `org.deidentifier.arx.algorithm.DataDependentEDDPAlgorithm`
- `org.deidentifier.arx.metric.v2.MetricMDNMPrecision` (information loss and DP score, including record suppression)
- The SafePub score functions of all further ARX quality models that support
  data-dependent DP (`isScoreFunctionSupported()`):
  `MetricMDNMLoss`, `MetricSDNMDiscernability`,
  `MetricMDNUEntropyPrecomputed`, `MetricSDAECS`, `MetricSDClassification`
- `org.deidentifier.arx.DataGeneralizationScheme` (fixed schemes for data-independent DP)

The original ARX Java source remains in `../src/`. This directory is intentionally separate so the Python port can be reviewed and run without mixing it into the Java codebase.

## Quick Start

Windows (PowerShell):

```powershell
$env:PYTHONPATH = 'python_safepub'
python -m unittest discover -s python_safepub/tests
python -m safepub.demo
```

Linux/macOS:

```bash
PYTHONPATH=python_safepub python3 -m unittest discover -s python_safepub/tests
PYTHONPATH=python_safepub python3 -m safepub.demo
```

## CSV CLI

You can run the tabular SafePub implementation on user-provided CSV files.
Data-dependent SafePub (PowerShell; use backslash-free relative paths or full
Windows paths):

```powershell
$env:PYTHONPATH = 'python_safepub'
python -m safepub.cli `
  --data data/adult.csv `
  --qi age sex workclass `
  --hierarchy age=data/adult_hierarchy_age.csv `
  --hierarchy sex=data/adult_hierarchy_sex.csv `
  --hierarchy workclass=data/adult_hierarchy_workclass.csv `
  --epsilon 2.0 `
  --delta 0.00001 `
  --data-dependent `
  --delimiter ';' `
  --hierarchy-header no `
  --output python_safepub/outputs/adult_safepub_anonymized.csv
```

(On Linux/macOS use `PYTHONPATH=python_safepub python3 -m safepub.cli ...` with
`\` line continuations instead of PowerShell backticks.)

### Data-dependent SafePub

For ARX-style data-dependent SafePub budget splitting, `--data-dependent` uses
ARX GUI's default search fraction of 10% and selects generalization levels with
the exponential mechanism:

```text
search_budget = epsilon * 0.10
anonymization_budget = epsilon - search_budget
```

You can override this with an absolute search budget (`--dp-search-budget 0.1`),
a ratio (`--dp-search-budget-ratio 0.05`), or interactively
(`--prompt-search-budget`, where empty input uses the ARX GUI default of 0.10).
Supplying a positive search budget implies data-dependent SafePub. Explicit
values must satisfy `0 < search_budget < epsilon`, matching ARX's validation.

The data-dependent search mirrors ARX's `DataDependentEDDPAlgorithm`: it starts
from the top transformation, adds every predecessor transformation to the
candidate set, and selects the next pivot with the exponential mechanism.
Candidates are never filtered based on the data; equivalence classes smaller
than `k` are folded into the DP score as suppressed records. By default the
expansion limit is the local hierarchy lattice size minus one; you can
override it with `--search-expansion-limit 100`.

### Quality models (score functions)

`--utility-metric` selects the ARX quality model whose SafePub score function
drives the data-dependent search. All Java quality models that support
data-dependent DP are available:

| `--utility-metric`   | ARX quality model                 | SafePub | Score sign |
|----------------------|-----------------------------------|---------|------------|
| `arx_precision`      | `MetricMDNMPrecision` (default)   | §5.1    | negative   |
| `arx_loss`           | `MetricMDNMLoss` (granularity)    | §5.1    | negative   |
| `arx_discernibility` | `MetricSDNMDiscernability`        | §5.2    | negative   |
| `arx_entropy`        | `MetricMDNUEntropyPrecomputed`    | §5.3    | negative   |
| `arx_aecs`           | `MetricSDAECS` (avg. class size)  | §5.4    | positive   |
| `arx_classification` | `MetricSDClassification`          | §5.5    | positive   |

Higher scores are always better; like in Java, the AECS score (number of
non-suppressed classes, plus one if anything is suppressed) and the
Classification score (majority-class frequencies divided by the sensitivity
`k * #targets`) are positive, the others negative. `arx_classification`
requires at least one target column via `--response-variable ATTRIBUTE`
(quasi-identifying or not), like ARX's response variables:

```powershell
python -m safepub.cli ... --data-dependent `
  --utility-metric arx_classification `
  --response-variable salary-class
```

The Loss model uses ARX-style domain shares (the fraction of the raw domain
covered by a generalized value, derived from the hierarchy); the Entropy
model treats values generalized to the hierarchy's root value as suppressed,
like Java's `rootValues` handling.

### Data-independent SafePub

Data-independent SafePub uses a fixed generalization scheme, like ARX's
`DataGeneralizationScheme`, and spends the full epsilon on anonymization:

```powershell
python -m safepub.cli `
  --data input.csv `
  --qi age gender zipcode `
  --epsilon 2.0 `
  --delta 0.3 `
  --generalization-degree medium `
  --generalization-level age=2 `
  --output anonymized.csv
```

An explicit `--generalization-level ATTRIBUTE=LEVEL` wins; other quasi
identifiers fall back to `--generalization-degree` (one of `none`, `low`,
`low_medium`, `medium`, `medium_high`, `high`, `complete`), resolved as
`round(factor * max_level)` like ARX. One of the two options is required for
data-independent runs — selecting levels by looking at the data without a
privacy budget would not be differentially private.

### Hierarchies

For each quasi identifier without a `--hierarchy ATTRIBUTE=PATH` argument, the CLI asks for a hierarchy CSV file:

```text
Please select the file for the generalization hierarchy for "age":
```

Hierarchy CSV files use ARX-style rows:

```csv
34,<50,*
45,<50,*
66,>=50,*
70,>=50,*
```

The first column is the raw value, followed by increasingly generalized values. Header rows such as `value,level1,level2` are auto-detected; use `--hierarchy-header yes` or `--hierarchy-header no` to override that behavior.

## Output and Suppression

Following SafePub, the released records are the beta-sampled subset, and
sampled records in equivalence classes smaller than `k` are suppressed. The
output CSV mirrors ARX's output handle: one row per input record, where
suppressed records (non-sampled, or in a class smaller than `k`) have every
column replaced by `*`.

## Utility Metric

The reported `utility value` mirrors what Java ARX reports for the solution:

- **Data-dependent runs**: transformations are checked with
  `ScoreType.DP_SCORE`, so the information loss ARX reports for the solution
  (`ARXLattice` node) *is* the `ILScore` of the selected quality model —
  higher is better (negative for Precision/Loss/Discernibility/Entropy,
  positive for AECS/Classification). Records outside the sampled subset and
  records in classes smaller than `k` count as suppressed in the score. The
  CLI prints this as `utility value (ARX ILScore, higher is better)` and
  exposes it as `result.score` (model name in `result.score_function`).
- **Data-independent (fixed scheme) runs**: ARX measures conventional
  information loss, so the reported value is `arx_precision` — ARX's
  arithmetic-mean Precision including record suppression
  (`MetricMDNMPrecision#getInformationLossInternal`, normalized by the
  sampled-subset size, with ARX's default `gsFactor=0.5` so both factors
  are 1). **Positive, lower is better**:

  ```text
  attribute_value_i = (unsuppressed * level_i / max_level_i + suppressed) / sampled
  utility_value     = arithmetic_mean(attribute_value_i)
  ```

For data-dependent runs the CLI prints the ILScore alone, exactly like Java
ARX. The conventional Precision value is not part of SafePub's reported
output, but it remains available for analysis via the API as
`result.utility` / `result.quality_loss`.

## Scope

This port currently focuses on the SafePub algorithmic core:

- Compute SafePub's sampling probability `beta` and anonymity threshold `k`.
- Sample a subset according to `beta`.
- Suppress records in equivalence classes smaller than `k` (ARX with a 100% suppression limit, as in ARX's DP examples).
- Use the exponential mechanism for candidate selection over the full local lattice.
- Select data-dependent generalization levels with an ARX-style exponential-mechanism search.
- Apply fixed ARX-style generalization schemes for data-independent DP.
- Provide a tiny hierarchy-based tabular demo.
- Load input data and hierarchy definitions from CSV files.
- Accept ARX-style data-dependent search budgets with a 10% default, absolute epsilon override, or ratio override.

It does not attempt to reimplement the full ARX framework, GUI, metrics catalog,
or all hierarchy builders. Microaggregation is intentionally not included,
matching ARX's constraint that differential privacy must not be combined with
microaggregation.

## Numerical Note

ARX uses interval arithmetic for conservative floating-point bounds. This Python port follows the same SafePub formulae and ARX-compatible `k` loop with regular Python `float` arithmetic. It is suitable as a runnable port and experimentation base; production-grade privacy certification should add interval or arbitrary-precision bounds before being relied on for guarantees.
