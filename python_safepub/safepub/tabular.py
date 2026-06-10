"""Small hierarchy-based tabular utilities for running SafePub in Python."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import product
from math import prod
from typing import Mapping, Sequence

from .criterion import EDDifferentialPrivacy
from .search import DataDependentEDDPSearch, SearchResult
from .utility import UtilityResult, arx_precision, arx_precision_dp_score


Row = Mapping[str, str]
Hierarchy = Mapping[str, Sequence[str]]
Hierarchies = Mapping[str, Hierarchy]
Levels = tuple[int, ...]


@dataclass(frozen=True)
class TabularAnonymizationResult:
    """Result from the minimal tabular SafePub anonymizer."""

    levels: Levels
    k: int
    beta: float
    sampled_indices: tuple[int, ...]
    equivalence_class_counts: Mapping[tuple[str, ...], int]
    rows: tuple[dict[str, str], ...]
    quality_loss: float
    utility: UtilityResult
    search_strategy: str
    search_expansion_limit: int | None
    search_result: SearchResult[Levels] | None


def safe_pub_anonymize(
    data: Sequence[Row],
    quasi_identifiers: Sequence[str],
    hierarchies: Hierarchies,
    *,
    epsilon: float,
    delta: float,
    deterministic: bool = False,
    data_dependent: bool = False,
    dp_search_budget: float | None = None,
    search_expansion_limit: int | None = None,
    utility_metric: str = "arx_precision",
) -> TabularAnonymizationResult:
    """Run a minimal hierarchy-based SafePub anonymization.

    For data-independent SafePub this enumerates all hierarchy-level
    transformations and chooses the lowest utility loss that satisfies
    SafePub's `k` threshold on the beta-sampled subset. For data-dependent
    SafePub it mirrors ARX's `DataDependentEDDPAlgorithm`: start at the top
    transformation and use the exponential mechanism to select predecessor
    transformations from a candidate set.
    """

    _validate_inputs(data, quasi_identifiers, hierarchies)
    criterion = EDDifferentialPrivacy(
        epsilon,
        delta,
        data_dependent=data_dependent,
        dp_search_budget=dp_search_budget,
        deterministic=deterministic,
    )
    initialization = criterion.initialize(len(data))
    sampled_indices = initialization.sampled_indices

    max_levels = _max_levels(quasi_identifiers, hierarchies)
    if data_dependent:
        (
            best_levels,
            best_counts,
            search_result,
            resolved_expansion_limit,
        ) = _find_levels_data_dependent(
            data,
            quasi_identifiers,
            hierarchies,
            max_levels,
            criterion,
            sampled_indices,
            deterministic=deterministic,
            search_expansion_limit=search_expansion_limit,
        )
        search_strategy = "exponential_mechanism"
    else:
        best_levels, best_counts = _find_levels_exhaustive(
            data,
            quasi_identifiers,
            hierarchies,
            max_levels,
            criterion,
            sampled_indices,
            utility_metric,
        )
        search_result = None
        resolved_expansion_limit = None
        search_strategy = "exhaustive"

    if best_levels is None or best_counts is None:
        raise ValueError(
            "No hierarchy-level transformation satisfied SafePub k-anonymity "
            f"for k={criterion.k} on {len(sampled_indices)} sampled rows"
        )

    utility = calculate_utility(quasi_identifiers, best_levels, max_levels, utility_metric)

    return TabularAnonymizationResult(
        levels=best_levels,
        k=criterion.k,
        beta=criterion.beta,
        sampled_indices=sampled_indices,
        equivalence_class_counts=dict(best_counts),
        rows=tuple(
            dict(generalize_row(row, quasi_identifiers, hierarchies, best_levels))
            for row in data
        ),
        quality_loss=utility.value,
        utility=utility,
        search_strategy=search_strategy,
        search_expansion_limit=resolved_expansion_limit,
        search_result=search_result,
    )


def generalize_row(
    row: Row,
    quasi_identifiers: Sequence[str],
    hierarchies: Hierarchies,
    levels: Levels,
) -> Row:
    """Return a row with quasi-identifiers generalized at the given levels."""

    result = dict(row)
    for attribute, level in zip(quasi_identifiers, levels):
        result[attribute] = generalize_value(row[attribute], hierarchies[attribute], level)
    return result


def generalize_value(value: str, hierarchy: Hierarchy, level: int) -> str:
    """Return one generalized value from a hierarchy."""

    if value not in hierarchy:
        if level == 0:
            return value
        return "*"
    path = hierarchy[value]
    if level < 0:
        raise ValueError("generalization level must be >= 0")
    if level >= len(path):
        return path[-1]
    return path[level]


def equivalence_class_counts(
    data: Sequence[Row],
    quasi_identifiers: Sequence[str],
    hierarchies: Hierarchies,
    levels: Levels,
    indices: Sequence[int] | None = None,
) -> Counter[tuple[str, ...]]:
    """Count equivalence classes for the selected row indices."""

    selected_indices = range(len(data)) if indices is None else indices
    counts: Counter[tuple[str, ...]] = Counter()
    for index in selected_indices:
        key = tuple(
            generalize_value(data[index][attribute], hierarchies[attribute], level)
            for attribute, level in zip(quasi_identifiers, levels)
        )
        counts[key] += 1
    return counts


def precision_loss(levels: Levels, max_levels: Levels) -> float:
    """Return the default ARX Precision value for hierarchy levels.

    Deprecated compatibility wrapper. Use `calculate_utility(...).value`.
    """

    quasi_identifiers = tuple(f"qi_{index}" for index in range(len(levels)))
    return arx_precision(quasi_identifiers, levels, max_levels).value


def calculate_utility(
    quasi_identifiers: Sequence[str],
    levels: Levels,
    max_levels: Levels,
    metric: str = "arx_precision",
) -> UtilityResult:
    """Calculate a utility metric for the selected generalization levels."""

    normalized_metric = metric.lower().replace("-", "_")
    if normalized_metric in {"arx_precision", "precision"}:
        return arx_precision(quasi_identifiers, levels, max_levels)
    raise ValueError(f"unsupported utility metric: {metric}")


def utility_loss(
    quasi_identifiers: Sequence[str],
    levels: Levels,
    max_levels: Levels,
    metric: str = "arx_precision",
) -> float:
    """Return the scalar value used for candidate comparison."""

    return calculate_utility(quasi_identifiers, levels, max_levels, metric).value


def _find_levels_exhaustive(
    data: Sequence[Row],
    quasi_identifiers: Sequence[str],
    hierarchies: Hierarchies,
    max_levels: Levels,
    criterion: EDDifferentialPrivacy,
    sampled_indices: Sequence[int],
    utility_metric: str,
) -> tuple[Levels | None, Counter[tuple[str, ...]] | None]:
    """Find the best transformation by exhaustive enumeration."""

    best_levels: Levels | None = None
    best_counts: Counter[tuple[str, ...]] | None = None
    best_loss = float("inf")

    for levels in _enumerate_levels(max_levels):
        counts = equivalence_class_counts(
            data,
            quasi_identifiers,
            hierarchies,
            levels,
            sampled_indices,
        )
        if _counts_satisfy_k(counts, criterion):
            loss = utility_loss(quasi_identifiers, levels, max_levels, utility_metric)
            if loss < best_loss:
                best_levels = levels
                best_counts = counts
                best_loss = loss

    return best_levels, best_counts


def _find_levels_data_dependent(
    data: Sequence[Row],
    quasi_identifiers: Sequence[str],
    hierarchies: Hierarchies,
    max_levels: Levels,
    criterion: EDDifferentialPrivacy,
    sampled_indices: Sequence[int],
    *,
    deterministic: bool,
    search_expansion_limit: int | None,
) -> tuple[
    Levels | None,
    Counter[tuple[str, ...]] | None,
    SearchResult[Levels] | None,
    int,
]:
    """Find a transformation using ARX-style data-dependent DP search."""

    resolved_expansion_limit = (
        _default_expansion_limit(max_levels)
        if search_expansion_limit is None
        else int(search_expansion_limit)
    )
    if resolved_expansion_limit < 0:
        raise ValueError("search_expansion_limit must be >= 0")

    counts_cache: dict[Levels, Counter[tuple[str, ...]]] = {}
    valid_cache: dict[Levels, bool] = {}

    def counts_for(levels: Levels) -> Counter[tuple[str, ...]]:
        if levels not in counts_cache:
            counts_cache[levels] = equivalence_class_counts(
                data,
                quasi_identifiers,
                hierarchies,
                levels,
                sampled_indices,
            )
        return counts_cache[levels]

    def is_valid(levels: Levels) -> bool:
        if levels not in valid_cache:
            valid_cache[levels] = _counts_satisfy_k(counts_for(levels), criterion)
        return valid_cache[levels]

    top = max_levels
    if not is_valid(top):
        return None, None, None, resolved_expansion_limit

    def predecessors(levels: Levels) -> list[Levels]:
        result: list[Levels] = []
        for index, level in enumerate(levels):
            if level <= 0:
                continue
            predecessor = tuple(
                level_value - 1 if level_index == index else level_value
                for level_index, level_value in enumerate(levels)
            )
            if is_valid(predecessor):
                result.append(predecessor)
        return result

    def score(levels: Levels) -> float:
        if not is_valid(levels):
            raise ValueError(
                "data-dependent SafePub search received a non-anonymous candidate"
            )
        return arx_precision_dp_score(
            quasi_identifiers,
            levels,
            max_levels,
            record_count=len(sampled_indices),
            k=criterion.k,
        )

    search = DataDependentEDDPSearch(
        top=top,
        predecessors=predecessors,
        score=score,
        expansion_limit=resolved_expansion_limit,
        epsilon_search=criterion.dp_search_budget,
        deterministic=deterministic,
    )
    search_result = search.traverse()
    best_levels = search_result.best
    return best_levels, counts_for(best_levels), search_result, resolved_expansion_limit


def _counts_satisfy_k(
    counts: Counter[tuple[str, ...]],
    criterion: EDDifferentialPrivacy,
) -> bool:
    return bool(counts) and criterion.are_classes_anonymous(counts.values())


def _validate_inputs(
    data: Sequence[Row],
    quasi_identifiers: Sequence[str],
    hierarchies: Hierarchies,
) -> None:
    if not data:
        raise ValueError("data must contain at least one row")
    if not quasi_identifiers:
        raise ValueError("at least one quasi-identifier is required")
    for attribute in quasi_identifiers:
        if attribute not in hierarchies:
            raise ValueError(f"missing hierarchy for quasi-identifier {attribute!r}")
        for row in data:
            if attribute not in row:
                raise ValueError(f"row is missing quasi-identifier {attribute!r}")


def _max_levels(quasi_identifiers: Sequence[str], hierarchies: Hierarchies) -> Levels:
    result: list[int] = []
    for attribute in quasi_identifiers:
        max_depth = max(len(path) for path in hierarchies[attribute].values())
        result.append(max(0, max_depth - 1))
    return tuple(result)


def _enumerate_levels(max_levels: Levels) -> list[Levels]:
    levels = [
        tuple(values)
        for values in product(*(range(max_level + 1) for max_level in max_levels))
    ]
    return sorted(levels, key=lambda item: (sum(item), item))


def _default_expansion_limit(max_levels: Levels) -> int:
    """Return a finite ARX-style expansion limit for the local lattice."""

    return max(0, prod(max_level + 1 for max_level in max_levels) - 1)
