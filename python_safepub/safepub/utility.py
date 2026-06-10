"""Utility metrics aligned with ARX metric formulas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class UtilityResult:
    """Calculated utility metric values."""

    metric: str
    aggregate_function: str
    value: float
    values_by_attribute: Mapping[str, float]


def arx_precision(
    quasi_identifiers: Sequence[str],
    levels: Sequence[int],
    max_levels: Sequence[int],
    *,
    generalization_factor: float = 1.0,
    weights: Mapping[str, float] | None = None,
) -> UtilityResult:
    """Return ARX's arithmetic-mean Precision information loss.

    This implements the generalization-level part of ARX's Precision metric:

    - `MetricMDPrecision#getInformationLossInternal`, via the lower-bound
      formula in `MetricMDNMPrecision#getLowerBoundInternal`
    - `ILMultiDimensionalArithmeticMean#getAggregate`

    The current Python anonymizer has no suppression and no microaggregation,
    so this is the ARX Precision value for that scope. With ARX's default
    `gsFactor=0.5`, the generalization factor is `1.0`.
    """

    if not quasi_identifiers:
        raise ValueError("at least one quasi-identifier is required")
    if len(quasi_identifiers) != len(levels) or len(levels) != len(max_levels):
        raise ValueError("quasi_identifiers, levels, and max_levels must align")
    if generalization_factor < 0.0:
        raise ValueError("generalization_factor must be >= 0")

    values_by_attribute: dict[str, float] = {}
    aggregate = 0.0
    dimensions = float(len(quasi_identifiers))

    for attribute, level, max_level in zip(quasi_identifiers, levels, max_levels):
        if level < 0:
            raise ValueError("generalization levels must be >= 0")
        if max_level < 0:
            raise ValueError("maximum generalization levels must be >= 0")

        dimension_value = (
            0.0
            if max_level == 0
            else (float(level) / float(max_level)) * generalization_factor
        )
        weight = 1.0 if weights is None else float(weights.get(attribute, 1.0))
        values_by_attribute[attribute] = dimension_value
        aggregate += (dimension_value / dimensions) * weight

    return UtilityResult(
        metric="arx_precision",
        aggregate_function="ARITHMETIC_MEAN",
        value=aggregate,
        values_by_attribute=values_by_attribute,
    )


def arx_precision_dp_score(
    quasi_identifiers: Sequence[str],
    levels: Sequence[int],
    max_levels: Sequence[int],
    *,
    record_count: int,
    k: int,
    suppressed_count: int = 0,
) -> float:
    """Return ARX's Precision score for SafePub's exponential mechanism.

    ARX uses a score function for data-dependent differential privacy instead
    of the normal information-loss value. For the current Python scope there is
    no suppression and no microaggregation, so `suppressed_count` defaults to
    zero. The value is negated because ARX's exponential mechanism expects
    larger scores to be better.
    """

    if not quasi_identifiers:
        raise ValueError("at least one quasi-identifier is required")
    if len(quasi_identifiers) != len(levels) or len(levels) != len(max_levels):
        raise ValueError("quasi_identifiers, levels, and max_levels must align")
    if record_count < 0:
        raise ValueError("record_count must be >= 0")
    if k < 0:
        raise ValueError("k must be >= 0")
    if suppressed_count < 0 or suppressed_count > record_count:
        raise ValueError("suppressed_count must be in [0, record_count]")

    dimensions = float(len(quasi_identifiers))
    unsuppressed_count = record_count - suppressed_count
    score = 0.0

    for level, max_level in zip(levels, max_levels):
        if level < 0:
            raise ValueError("generalization levels must be >= 0")
        if max_level < 0:
            raise ValueError("maximum generalization levels must be >= 0")

        value = 0.0 if max_level == 0 else float(level) / float(max_level)
        score += (float(unsuppressed_count) * value) + float(suppressed_count)

    score *= -1.0 / dimensions
    if k > 1:
        score /= float(k - 1)
    return score
