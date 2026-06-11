# Adult SafePub Anonymization Report

Generated on: 2026-06-10

## Input

- Data CSV: `data/adult.csv`
- Quasi identifiers: `age`, `sex`, `workclass`
- Hierarchy CSVs:
  - `age`: `data/adult_hierarchy_age.csv`
  - `sex`: `data/adult_hierarchy_sex.csv`
  - `workclass`: `data/adult_hierarchy_workclass.csv`

## SafePub Parameters

- `epsilon`: `2.0`
- `delta`: `1e-5`
- `data_dependent`: `true`
- `dp_search_budget_ratio`: `0.10`
- `dp_search_budget`: `0.2`
- `anonymization_budget`: `1.8`
- `beta`: `0.834701111778`
- `k`: `92`
- sampled rows in this run: `25174 / 30162`

## Data-Dependent Search

- search strategy: `exponential_mechanism`
- search expansion limit: `29`
- search steps executed: `29`
- search stopped early: `false`
- maximum hierarchy levels: `(4, 1, 2)`
- selected best score: `-115.195970696`

The search starts from the top transformation `(4, 1, 2)`. Following ARX's
`DataDependentEDDPAlgorithm`, every lattice predecessor is a candidate:
equivalence classes smaller than `k` are folded into the DP score as
suppressed records (`MetricMDNMPrecision#getScore`) instead of being filtered
out, so the search can descend through transformations with small classes and
ran all 29 expansions.

## Selected Generalization Levels

The quasi identifiers were evaluated in this order: `age`, `sex`, `workclass`.

- selected levels: `(2, 0, 0)`
- `age`: level `2`, generalized to ten-year intervals (e.g. `30-39`)
- `sex`: level `0`, kept as the original value
- `workclass`: level `0`, kept as the original value

## Suppression

Following SafePub, the released dataset is the beta-sampled subset, and
sampled records in equivalence classes smaller than `k` are suppressed:

- sampled rows: `25174`
- suppressed sampled rows (class < k): `1559`
- non-sampled rows (suppressed in output): `4988`
- released rows: `23615 / 30162`

The output CSV mirrors ARX's output handle: one row per input record, with
suppressed records written as `*` in every column (`6547` such rows).

## Utility Metric

Mirroring Java ARX, the utility reported for a data-dependent DP solution is
its `ILScore` (`MetricMDNMPrecision#getScore`, transferred unchanged to the
result by `ARXLattice`): a negative value where higher is better.

```text
utility value (ARX ILScore) = -115.195970696
```

For analysis purposes (not part of SafePub's reported output, available via
`result.utility`), the conventional `arx_precision` value of this solution —
ARX's arithmetic-mean Precision including record suppression
(`MetricMDNMPrecision#getInformationLossInternal` normalized by the
sampled-subset size) — is:

```text
attribute_value_i = (unsuppressed * level_i / max_level_i + suppressed) / sampled
utility_value     = arithmetic_mean(attribute_value_i)
```

Lower is better. The selected result has:

```text
unsuppressed = 25174 - 1559 = 23615
age:        (23615 * 2/4 + 1559) / 25174 = 0.531033
sex:        (23615 * 0/1 + 1559) / 25174 = 0.061929
workclass:  (23615 * 0/2 + 1559) / 25174 = 0.061929
arx_precision = (0.531033 + 0.061929 + 0.061929) / 3 = 0.218274
```

This metric is implemented in `safepub.utility.arx_precision`.

For comparison, the previous implementation (no suppression, candidates
filtered by the sampled `k` threshold) stopped after one search step and
selected `(4, 0, 2)` with `arx_precision = 0.666667`. With ARX-style
suppression the search reaches a far less generalized release.

## Output

- Output CSV: `python_safepub/outputs/adult_safepub_anonymized.csv`
- Output rows, including header: `30163`
- Fully suppressed output rows: `6547`
- Smallest unsuppressed equivalence class over `(age, sex, workclass)`: `94 >= k`

## Current Implementation Note

This was generated with the current Python SafePub-style tabular
implementation: SafePub `beta/k` calculation, beta sampling, ARX-style
data-dependent privacy-budget splitting, exponential-mechanism
generalization-level selection over the full local lattice, and ARX-style
record suppression (sub-`k` classes and non-sampled records). Microaggregation
is intentionally not included, matching ARX's validation rule that
differential privacy must not be combined with microaggregation.
