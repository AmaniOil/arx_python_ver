"""Runnable SafePub Python-port demo."""

from __future__ import annotations

from pprint import pprint

from .parameters import ParameterCalculation
from .tabular import safe_pub_anonymize


def main() -> None:
    epsilon = 2.0
    delta = 0.3

    parameters = ParameterCalculation(epsilon, delta).as_parameters()
    print("SafePub parameters")
    pprint(parameters)
    print()

    data = [
        {"age": "34", "gender": "male", "zipcode": "81667"},
        {"age": "45", "gender": "female", "zipcode": "81675"},
        {"age": "66", "gender": "male", "zipcode": "81925"},
        {"age": "70", "gender": "female", "zipcode": "81931"},
        {"age": "34", "gender": "female", "zipcode": "81931"},
        {"age": "70", "gender": "male", "zipcode": "81931"},
        {"age": "45", "gender": "male", "zipcode": "81931"},
        {"age": "52", "gender": "female", "zipcode": "81925"},
        {"age": "39", "gender": "male", "zipcode": "81667"},
        {"age": "61", "gender": "female", "zipcode": "81675"},
        {"age": "44", "gender": "male", "zipcode": "81925"},
        {"age": "73", "gender": "female", "zipcode": "81931"},
        {"age": "36", "gender": "female", "zipcode": "81667"},
        {"age": "58", "gender": "male", "zipcode": "81675"},
        {"age": "48", "gender": "female", "zipcode": "81925"},
        {"age": "64", "gender": "male", "zipcode": "81931"},
        {"age": "42", "gender": "male", "zipcode": "81667"},
        {"age": "57", "gender": "female", "zipcode": "81675"},
        {"age": "69", "gender": "male", "zipcode": "81925"},
        {"age": "31", "gender": "female", "zipcode": "81931"},
    ]

    hierarchies = {
        "age": {
            "31": ("31", "<50", "*"),
            "34": ("34", "<50", "*"),
            "36": ("36", "<50", "*"),
            "39": ("39", "<50", "*"),
            "42": ("42", "<50", "*"),
            "44": ("44", "<50", "*"),
            "45": ("45", "<50", "*"),
            "48": ("48", "<50", "*"),
            "52": ("52", ">=50", "*"),
            "57": ("57", ">=50", "*"),
            "58": ("58", ">=50", "*"),
            "61": ("61", ">=50", "*"),
            "64": ("64", ">=50", "*"),
            "66": ("66", ">=50", "*"),
            "69": ("69", ">=50", "*"),
            "70": ("70", ">=50", "*"),
            "73": ("73", ">=50", "*"),
        },
        "gender": {
            "male": ("male", "*"),
            "female": ("female", "*"),
        },
        "zipcode": {
            "81667": ("81667", "8166*", "816**", "81***", "8****", "*****"),
            "81675": ("81675", "8167*", "816**", "81***", "8****", "*****"),
            "81925": ("81925", "8192*", "819**", "81***", "8****", "*****"),
            "81931": ("81931", "8193*", "819**", "81***", "8****", "*****"),
        },
    }

    result = safe_pub_anonymize(
        data,
        ("age", "gender", "zipcode"),
        hierarchies,
        epsilon=epsilon,
        delta=delta,
        deterministic=True,
        data_dependent=True,
    )

    print("Data-dependent tabular anonymization result")
    print(f"levels: {result.levels}")
    print(f"utility value (ARX ILScore, higher is better): {result.score:.12g}")
    print(f"k: {result.k}")
    print(f"beta: {result.beta:.12f}")
    print(f"sampled rows: {len(result.sampled_indices)} / {len(data)}")
    print(f"suppressed sampled rows (class < k): {result.suppressed_sample_count}")
    print(f"non-sampled rows (suppressed in output): {result.non_sampled_count}")
    print("equivalence classes on sampled rows:")
    pprint(dict(result.equivalence_class_counts))
    print("first five output rows:")
    pprint(result.rows[:5])

    fixed = safe_pub_anonymize(
        data,
        ("age", "gender", "zipcode"),
        hierarchies,
        epsilon=epsilon,
        delta=delta,
        deterministic=True,
        generalization_degree="medium",
    )

    print()
    print("Data-independent (fixed MEDIUM scheme) result")
    print(f"levels: {fixed.levels}")
    print(f"suppressed sampled rows (class < k): {fixed.suppressed_sample_count}")
    print(
        f"utility value (safepub_precision, lower is better): {fixed.quality_loss:.6f}"
    )


if __name__ == "__main__":
    main()
