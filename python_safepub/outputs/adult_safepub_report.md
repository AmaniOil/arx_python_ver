# Adult SafePub Anonymization Report

Generated on: 2026-06-04

## Input

- Data CSV: `data/adult.csv`
- Quasi identifiers: `age`, `sex`, `workclass`
- Hierarchy CSVs:
  - `age`: `/Users/takumisugiyama/Desktop/ARX_materials/adult_hierarchy_age.csv`
  - `sex`: `/Users/takumisugiyama/Desktop/ARX_materials/adult_hierarchy_sex.csv`
  - `workclass`: `/Users/takumisugiyama/Desktop/ARX_materials/adult_hierarchy_workclass.csv`

## SafePub Parameters

- `epsilon`: `2.0`
- `delta`: `1e-5`
- `data_dependent`: `true`
- `dp_search_budget_ratio`: `0.10`
- `dp_search_budget`: `0.2`
- `anonymization_budget`: `1.8`
- `beta`: `0.834701111778`
- `k`: `92`
- sampled rows in this run: `25149 / 30162`

## Data-Dependent Search

- search strategy: `exponential_mechanism`
- search expansion limit: `29`
- search steps executed: `1`
- search stopped early: `true`
- maximum hierarchy levels: `(4, 1, 2)`
- selected best score: `-184.241758242`

The search starts from the top transformation `(4, 1, 2)`. In this run, the
exponential mechanism selected `(4, 0, 2)` as the next pivot. No lower
predecessor transformation still satisfied SafePub's sampled `k` threshold, so
the search stopped early.

## Selected Generalization Levels

The quasi identifiers were evaluated in this order: `age`, `sex`, `workclass`.

- selected levels: `(4, 0, 2)`
- `age`: level `4`, generalized to `*`
- `sex`: level `0`, kept as the original value
- `workclass`: level `2`, generalized to `*`

## Utility Metric

The current Python implementation now reports the metric as `arx_precision`.
For the current no-suppression and no-microaggregation scope, this follows ARX's
arithmetic-mean Precision formula:

```text
attribute_value_i = selected_level_i / max_level_i
utility_value = arithmetic_mean(attribute_value_i)
```

Lower is better. The selected result has:

```text
arx_precision = (4/4 + 0/1 + 2/2) / 3 = 0.666667
```

This metric is implemented in `safepub.utility.arx_precision`.

## Output

- Output CSV: `python_safepub/outputs/adult_safepub_anonymized.csv`
- Output rows, including header: `30163`
- Full-output equivalence classes over `(age, sex, workclass)`:
  - `(*, Male, *)`: `20380`
  - `(*, Female, *)`: `9782`
- Minimum full-output equivalence class size: `9782`

## Current Implementation Note

This was generated with the current Python SafePub-style tabular implementation:
SafePub `beta/k` calculation, beta sampling, k-anonymity checking, ARX-style
data-dependent privacy-budget splitting, and exponential-mechanism
generalization-level selection. Microaggregation is intentionally not included,
matching ARX's validation rule that differential privacy must not be combined
with microaggregation.
