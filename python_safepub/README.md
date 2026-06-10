# SafePub Python Port

This is a standalone Python workspace for porting the SafePub-related parts of ARX.

The implementation mirrors the ARX Java components at a practical Python level:

- `org.deidentifier.arx.dp.ParameterCalculation`
- `org.deidentifier.arx.criteria.EDDifferentialPrivacy`
- `org.deidentifier.arx.dp.ExponentialMechanism`
- `org.deidentifier.arx.algorithm.DataDependentEDDPAlgorithm`

The original ARX Java source remains in `../src/`. This directory is intentionally separate so the Python port can be reviewed and run without mixing it into the Java codebase.

## Quick Start

```bash
PYTHONPATH=python_safepub python3 -m unittest discover -s python_safepub/tests
PYTHONPATH=python_safepub python3 -m safepub.demo
```

## CSV CLI

You can run the current tabular SafePub implementation on user-provided CSV files:

```bash
PYTHONPATH=python_safepub python3 -m safepub.cli \
  --data input.csv \
  --qi age gender zipcode \
  --epsilon 2.0 \
  --delta 0.3 \
  --data-dependent \
  --utility-metric arx_precision \
  --output anonymized.csv
```

For ARX-style data-dependent SafePub budget splitting, `--data-dependent` uses
ARX GUI's default search fraction of 10% and selects generalization levels with
the exponential mechanism:

```text
search_budget = epsilon * 0.10
anonymization_budget = epsilon - search_budget
```

You can override this with an absolute search budget:

```bash
PYTHONPATH=python_safepub python3 -m safepub.cli \
  --data input.csv \
  --qi age gender zipcode \
  --epsilon 2.0 \
  --delta 0.3 \
  --data-dependent \
  --dp-search-budget 0.1 \
  --output anonymized.csv
```

For `epsilon=2.0`, this explicit split is:

```text
search_budget = 0.1
anonymization_budget = epsilon - search_budget = 1.9
```

You can also specify the same split as a ratio:

```bash
--dp-search-budget-ratio 0.05
```

Or ask for the ratio interactively:

```bash
--data-dependent --prompt-search-budget
```

The prompt accepts an empty value as the ARX GUI default:

```text
Please enter the search budget ratio [default: 0.10]:
```

Supplying a positive search budget implies data-dependent SafePub. Explicit values must satisfy `0 < search_budget < epsilon`, matching ARX's validation.

The data-dependent search starts from the top transformation, adds valid
predecessor transformations to a candidate set, and selects the next pivot with
the exponential mechanism. By default the expansion limit is the local hierarchy
lattice size minus one; you can override it with:

```bash
--search-expansion-limit 100
```

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

The first ARX-aligned utility metric implemented is `arx_precision`. It follows ARX's arithmetic-mean Precision formula for the current Python scope, which has no suppression and no microaggregation:

```text
attribute_value_i = selected_level_i / max_level_i
utility_value = arithmetic_mean(attribute_value_i)
```

This corresponds to ARX's default `Metric.createPrecisionMetric(..., ARITHMETIC_MEAN)` generalization-level component.

For data-dependent SafePub, candidate sampling uses ARX's Precision DP score
shape (`MetricMDNMPrecision#getScore`): lower generalization loss becomes a
higher score by multiplying the score with `-1`. The reported utility value
remains normal ARX Precision, where lower is better.

## Scope

This port currently focuses on the SafePub algorithmic core:

- Compute SafePub's sampling probability `beta` and anonymity threshold `k`.
- Sample a subset according to `beta`.
- Check `k`-anonymous equivalence classes on sampled records.
- Use the exponential mechanism for candidate selection.
- Select data-dependent generalization levels with an ARX-style exponential-mechanism search.
- Provide a tiny hierarchy-based tabular demo.
- Load input data and hierarchy definitions from CSV files.
- Accept ARX-style data-dependent search budgets with a 10% default, absolute epsilon override, or ratio override.

It does not attempt to reimplement the full ARX framework, GUI, metrics catalog,
suppression, microaggregation, or all hierarchy builders. This matches ARX's
constraint that differential privacy must not be combined with microaggregation.

## Numerical Note

ARX uses interval arithmetic for conservative floating-point bounds. This Python port follows the same SafePub formulae and ARX-compatible `k` loop with regular Python `float` arithmetic. It is suitable as a runnable port and experimentation base; production-grade privacy certification should add interval or arbitrary-precision bounds before being relied on for guarantees.
