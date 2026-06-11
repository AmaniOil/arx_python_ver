# IHIS SafePub Anonymization Report

Generated on: 2026-06-11

## Input

- Data CSV: `data/ihis.csv` (1,193,504 records)
- Quasi identifiers (9): `YEAR`, `QUARTER`, `REGION`, `PERNUM`, `AGE`,
  `MARSTAT`, `SEX`, `RACEA`, `EDUC`
- Hierarchy CSVs: `data/ihis_hierarchy_<ATTRIBUTE>.csv`
- Hierarchy coverage was verified before the run: every distinct data value
  of all nine attributes is covered by its hierarchy.

## SafePub Parameters

- `epsilon`: `2.0`
- `delta`: `1e-7` (following the recommendation `delta < 1/records`;
  `1/1,193,504 ≈ 8.4e-7`)
- `data_dependent`: `true`
- `dp_search_budget_ratio`: `0.10`
- `dp_search_budget`: `0.2`
- `anonymization_budget`: `1.8`
- `beta`: `0.834701111778`
- `k`: `133`
- sampled rows in this run: `995,819 / 1,193,504`

## Data-Dependent Search

- search strategy: `exponential_mechanism`
- score function: `arx_precision`
- search expansion limit: `30` (explicit; the local lattice has 25,920
  transformations, so the lattice-size default is impractical — the lattice
  depth is `sum(max_levels) = 21`, so 30 expansions can reach any depth, and
  the per-step budget `0.2/30` matches the adult run's `0.2/29` almost
  exactly)
- search steps executed: `30`
- search stopped early: `false`
- maximum hierarchy levels: `(5, 2, 2, 3, 4, 2, 1, 1, 1)`
- selected best score: `-5095.160578`

## Selected Generalization Levels

The quasi identifiers were evaluated in this order:
`YEAR, QUARTER, REGION, PERNUM, AGE, MARSTAT, SEX, RACEA, EDUC`.

- selected levels: `(4, 0, 0, 2, 4, 1, 0, 0, 0)`
- `YEAR`: level `4`, generalized to 40-year intervals (e.g. `1980-2019`)
- `QUARTER`: level `0`, kept as the original value
- `REGION`: level `0`, kept as the original value
- `PERNUM`: level `2`, generalized to groups of four (e.g. `0-3`)
- `AGE`: level `4`, fully generalized to `*`
- `MARSTAT`: level `1`, generalized to spouse-presence categories
- `SEX`: level `0`, kept as the original value
- `RACEA`: level `0`, kept as the original value
- `EDUC`: level `0`, kept as the original value

## Suppression

Following SafePub, the released dataset is the beta-sampled subset, and
sampled records in equivalence classes smaller than `k` are suppressed:

- sampled rows: `995,819`
- suppressed sampled rows (class < k): `218,722`
- non-sampled rows (suppressed in output): `197,685`
- released rows: `777,097 / 1,193,504` (about 65%)

The output CSV mirrors ARX's output handle: one row per input record, with
suppressed records written as `*` in every column (`416,407` such rows).

## Output

- Output CSV: `python_safepub/outputs/ihis_safepub_anonymized.csv`
- Output rows, including header: `1,193,505`
- Fully suppressed output rows: `416,407`
- Unsuppressed equivalence classes: `1,468`
- Smallest unsuppressed equivalence class: `133 = k`
- Largest equivalence class: `4,268`
  (`1980-2019, Quarter 2, South, 0-3, *, spouse present, Female, White,
  High school graduate`)

## Utility

Mirroring Java ARX, the utility reported for a data-dependent DP solution is
its `ILScore` (higher is better):

```text
utility value (ARX ILScore) = -5095.160578
```

For analysis purposes (not part of SafePub's reported output, available via
`result.utility`), the conventional `arx_precision` of this solution is:

```text
unsuppressed = 995,819 - 218,722 = 777,097
arx_precision = mean over 9 dimensions of
                (unsuppressed * level_i/max_i + suppressed) / sampled
              = 0.476870
```

## Notes

- Runtime was roughly 13 minutes on the full dataset (pure-Python
  implementation, about 2.5 s per transformation check on 1.19M rows).
  `data/ihis_subset.csv` (119,350 records) is available for faster
  experiments.
- The IHIS data and hierarchies were copied from the ARX benchmark data
  archive into `data/`; they are kept local (untracked) for now.
- Reproduce with:

```powershell
$env:PYTHONPATH = 'python_safepub'
python -m safepub.cli `
  --data data/ihis.csv `
  --qi YEAR QUARTER REGION PERNUM AGE MARSTAT SEX RACEA EDUC `
  --hierarchy YEAR=data/ihis_hierarchy_YEAR.csv `
  --hierarchy QUARTER=data/ihis_hierarchy_QUARTER.csv `
  --hierarchy REGION=data/ihis_hierarchy_REGION.csv `
  --hierarchy PERNUM=data/ihis_hierarchy_PERNUM.csv `
  --hierarchy AGE=data/ihis_hierarchy_AGE.csv `
  --hierarchy MARSTAT=data/ihis_hierarchy_MARSTAT.csv `
  --hierarchy SEX=data/ihis_hierarchy_SEX.csv `
  --hierarchy RACEA=data/ihis_hierarchy_RACEA.csv `
  --hierarchy EDUC=data/ihis_hierarchy_EDUC.csv `
  --epsilon 2.0 `
  --delta 0.0000001 `
  --data-dependent `
  --search-expansion-limit 30 `
  --delimiter ';' `
  --hierarchy-header no `
  --output python_safepub/outputs/ihis_safepub_anonymized.csv
```
