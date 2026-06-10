"""Command-line interface for CSV-based SafePub anonymization."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Callable, Sequence, TextIO

from .csv_io import read_data_csv, read_hierarchies_from_paths, write_data_csv
from .criterion import DEFAULT_SEARCH_BUDGET_RATIO
from .tabular import safe_pub_anonymize


InputFunction = Callable[[str], str]


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI."""

    args = build_parser().parse_args(argv)
    input_func = input
    output = sys.stdout

    data_path = args.data or _prompt_for_existing_file(
        "Please select the input data CSV file: ",
        input_func=input_func,
        output=output,
    )
    quasi_identifiers = _normalize_quasi_identifiers(args.qi)
    if not quasi_identifiers:
        raw_qis = input_func(
            "Please enter quasi identifier columns separated by commas: "
        )
        quasi_identifiers = _normalize_quasi_identifiers([raw_qis])
    if not quasi_identifiers:
        raise ValueError("at least one quasi identifier is required")

    dp_search_budget_ratio = args.dp_search_budget_ratio
    if (
        args.data_dependent
        and args.prompt_search_budget
        and args.dp_search_budget == 0.0
        and dp_search_budget_ratio is None
    ):
        dp_search_budget_ratio = prompt_for_search_budget_ratio(
            input_func=input_func,
            output=output,
        )

    data_dependent, dp_search_budget = resolve_search_budget(
        epsilon=args.epsilon,
        data_dependent=args.data_dependent,
        dp_search_budget=args.dp_search_budget,
        dp_search_budget_ratio=dp_search_budget_ratio,
    )

    hierarchy_paths = parse_hierarchy_arguments(args.hierarchy)
    hierarchy_paths.update(
        prompt_for_missing_hierarchy_paths(
            quasi_identifiers,
            hierarchy_paths,
            input_func=input_func,
            output=output,
        )
    )

    has_header = _header_option_to_value(args.hierarchy_header)
    data = read_data_csv(data_path, delimiter=args.delimiter)
    hierarchies = read_hierarchies_from_paths(
        hierarchy_paths,
        delimiter=args.delimiter,
        has_header=has_header,
    )

    result = safe_pub_anonymize(
        data,
        quasi_identifiers,
        hierarchies,
        epsilon=args.epsilon,
        delta=args.delta,
        deterministic=args.deterministic,
        data_dependent=data_dependent,
        dp_search_budget=dp_search_budget,
        search_expansion_limit=args.search_expansion_limit,
        utility_metric=args.utility_metric,
    )

    output.write("SafePub anonymization completed\n")
    output.write(f"total epsilon: {args.epsilon:.12g}\n")
    output.write(f"data dependent: {data_dependent}\n")
    output.write(f"search budget: {dp_search_budget:.12g}\n")
    output.write(f"search budget ratio: {dp_search_budget / args.epsilon:.6f}\n")
    output.write(f"anonymization budget: {args.epsilon - dp_search_budget:.12g}\n")
    output.write(f"search strategy: {result.search_strategy}\n")
    if result.search_expansion_limit is not None:
        output.write(f"search expansion limit: {result.search_expansion_limit}\n")
    if result.search_result is not None:
        output.write(f"search steps: {len(result.search_result.steps) - 1}\n")
        output.write(f"search stopped early: {result.search_result.stopped_early}\n")
        output.write(f"search best score: {result.search_result.best_score:.12g}\n")
    output.write(f"levels: {result.levels}\n")
    output.write(f"k: {result.k}\n")
    output.write(f"beta: {result.beta:.12f}\n")
    output.write(f"sampled rows: {len(result.sampled_indices)} / {len(data)}\n")
    output.write(f"utility metric: {result.utility.metric}\n")
    output.write(f"aggregate function: {result.utility.aggregate_function}\n")
    output.write(f"utility value: {result.utility.value:.6f}\n")

    output_path = args.output
    if output_path is None and args.prompt_output:
        raw_output = input_func(
            "Please enter the output CSV file path, or leave blank to skip writing: "
        ).strip()
        output_path = raw_output or None

    if output_path is not None:
        write_data_csv(
            output_path,
            result.rows,
            fieldnames=list(data[0].keys()),
            delimiter=args.delimiter or ",",
        )
        output.write(f"output CSV: {Path(output_path).expanduser()}\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(
        description="Run the SafePub Python port on CSV data."
    )
    parser.add_argument("--data", help="Input data CSV path. Prompts if omitted.")
    parser.add_argument(
        "--qi",
        "--quasi-identifiers",
        nargs="+",
        help="Quasi identifier column names. Accepts space or comma separated values.",
    )
    parser.add_argument(
        "--hierarchy",
        action="append",
        default=[],
        metavar="ATTRIBUTE=CSV",
        help="Hierarchy CSV for a quasi identifier. Missing ones are prompted.",
    )
    parser.add_argument("--epsilon", type=float, required=True)
    parser.add_argument("--delta", type=float, required=True)
    parser.add_argument(
        "--data-dependent",
        action="store_true",
        help="Use ARX-style data-dependent SafePub. Generalization levels are "
        "selected with the exponential mechanism. If no search budget is "
        "supplied, defaults to 10%% of epsilon like ARX GUI.",
    )
    parser.add_argument(
        "--dp-search-budget",
        "--search-budget",
        type=float,
        default=0.0,
        help="Absolute epsilon budget reserved for data-dependent search. "
        "Must satisfy 0 < budget < epsilon. Supplying a positive value implies "
        "--data-dependent.",
    )
    parser.add_argument(
        "--dp-search-budget-ratio",
        "--search-budget-ratio",
        type=float,
        help="Fraction of epsilon reserved for data-dependent search, e.g. 0.05 "
        "means 5%%. Mutually exclusive with --dp-search-budget. Defaults to 0.10 "
        "when --data-dependent is used without an explicit budget.",
    )
    parser.add_argument(
        "--prompt-search-budget",
        action="store_true",
        help="When --data-dependent is used and no search budget is supplied, "
        "ask for a search budget ratio. Empty input uses the ARX GUI default "
        "of 0.10.",
    )
    parser.add_argument(
        "--search-expansion-limit",
        "--expansion-limit",
        type=int,
        help="Maximum number of data-dependent search expansions. Defaults to "
        "the local hierarchy lattice size minus one.",
    )
    parser.add_argument("--deterministic", action="store_true")
    parser.add_argument("--delimiter", help="CSV delimiter. Auto-detected if omitted.")
    parser.add_argument("--output", help="Output anonymized CSV path.")
    parser.add_argument(
        "--utility-metric",
        default="arx_precision",
        choices=("arx_precision", "precision"),
        help="Utility metric used to compare candidate generalization levels.",
    )
    parser.add_argument(
        "--prompt-output",
        action="store_true",
        help="Ask for an output path interactively when --output is omitted.",
    )
    parser.add_argument(
        "--hierarchy-header",
        choices=("auto", "yes", "no"),
        default="auto",
        help="Whether hierarchy CSV files contain a header row. Default: auto.",
    )
    return parser


def parse_hierarchy_arguments(values: Sequence[str]) -> dict[str, str]:
    """Parse `ATTRIBUTE=CSV` CLI hierarchy arguments."""

    result: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"hierarchy argument must be ATTRIBUTE=CSV: {value!r}")
        attribute, path = value.split("=", 1)
        attribute = attribute.strip()
        path = path.strip()
        if not attribute or not path:
            raise ValueError(f"hierarchy argument must be ATTRIBUTE=CSV: {value!r}")
        result[attribute] = path
    return result


def resolve_search_budget(
    *,
    epsilon: float,
    data_dependent: bool,
    dp_search_budget: float,
    dp_search_budget_ratio: float | None,
) -> tuple[bool, float]:
    """Resolve and validate ARX-style data-dependent search budget inputs."""

    if epsilon <= 0:
        raise ValueError("epsilon must be > 0")
    if dp_search_budget < 0:
        raise ValueError("dp_search_budget must be >= 0")
    if dp_search_budget_ratio is not None:
        if dp_search_budget > 0:
            raise ValueError(
                "--dp-search-budget and --dp-search-budget-ratio are mutually exclusive"
            )
        if dp_search_budget_ratio <= 0 or dp_search_budget_ratio >= 1:
            raise ValueError("dp_search_budget_ratio must be in (0, 1)")
        dp_search_budget = epsilon * dp_search_budget_ratio
    elif data_dependent and dp_search_budget == 0:
        dp_search_budget = epsilon * DEFAULT_SEARCH_BUDGET_RATIO

    resolved_data_dependent = data_dependent or dp_search_budget > 0
    if resolved_data_dependent:
        if dp_search_budget >= epsilon:
            raise ValueError("dp_search_budget must be smaller than epsilon")
    return resolved_data_dependent, dp_search_budget


def prompt_for_search_budget_ratio(
    *,
    input_func: InputFunction = input,
    output: TextIO = sys.stdout,
) -> float:
    """Prompt for a data-dependent search budget ratio."""

    while True:
        raw_value = input_func(
            "Please enter the search budget ratio [default: 0.10]: "
        ).strip()
        if raw_value == "":
            return DEFAULT_SEARCH_BUDGET_RATIO
        try:
            ratio = float(raw_value)
        except ValueError:
            output.write("Please enter a numeric ratio in (0, 1).\n")
            continue
        if 0.0 < ratio < 1.0:
            return ratio
        output.write("Search budget ratio must be in (0, 1).\n")


def prompt_for_missing_hierarchy_paths(
    quasi_identifiers: Sequence[str],
    existing_paths: dict[str, str] | None = None,
    *,
    input_func: InputFunction = input,
    output: TextIO = sys.stdout,
) -> dict[str, str]:
    """Prompt for hierarchy CSV files not already provided."""

    existing_paths = existing_paths or {}
    prompted: dict[str, str] = {}
    for attribute in quasi_identifiers:
        if attribute in existing_paths:
            continue
        prompted[attribute] = _prompt_for_existing_file(
            f'Please select the file for the generalization hierarchy for "{attribute}": ',
            input_func=input_func,
            output=output,
        )
    return prompted


def _prompt_for_existing_file(
    prompt: str,
    *,
    input_func: InputFunction,
    output: TextIO,
) -> str:
    while True:
        path = input_func(prompt).strip()
        if Path(path).expanduser().is_file():
            return path
        output.write(f"File not found: {path}\n")


def _normalize_quasi_identifiers(values: Sequence[str] | None) -> tuple[str, ...]:
    if not values:
        return ()
    result: list[str] = []
    for value in values:
        for part in value.split(","):
            cleaned = part.strip()
            if cleaned:
                result.append(cleaned)
    return tuple(result)


def _header_option_to_value(option: str) -> bool | None:
    if option == "yes":
        return True
    if option == "no":
        return False
    return None


if __name__ == "__main__":
    raise SystemExit(main())
