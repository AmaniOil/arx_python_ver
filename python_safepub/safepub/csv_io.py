"""CSV helpers for data and generalization hierarchies."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Mapping, Sequence

from .tabular import Hierarchy, Hierarchies, Row


DEFAULT_DELIMITERS = ",;\t|"
HEADER_MARKERS = {"value", "raw", "original", "level0", "level_0", "元値"}


def read_data_csv(
    path: str | Path,
    *,
    delimiter: str | None = None,
    encoding: str = "utf-8-sig",
    strip: bool = True,
) -> tuple[dict[str, str], ...]:
    """Read a header-based input data CSV into row dictionaries."""

    csv_path = _resolve_existing_path(path)
    with csv_path.open("r", newline="", encoding=encoding) as handle:
        sample = handle.read(4096)
        handle.seek(0)
        dialect = _dialect_from_sample(sample, delimiter)
        reader = csv.DictReader(handle, dialect=dialect)
        if not reader.fieldnames:
            raise ValueError(f"data CSV has no header row: {csv_path}")

        fieldnames = [_clean_cell(name, strip) for name in reader.fieldnames]
        _validate_fieldnames(fieldnames, csv_path)

        rows: list[dict[str, str]] = []
        for row in reader:
            cleaned = {
                fieldname: _clean_cell(row.get(original, ""), strip)
                for original, fieldname in zip(reader.fieldnames, fieldnames)
            }
            if any(value != "" for value in cleaned.values()):
                rows.append(cleaned)

    if not rows:
        raise ValueError(f"data CSV contains no data rows: {csv_path}")
    return tuple(rows)


def read_hierarchy_csv(
    path: str | Path,
    *,
    delimiter: str | None = None,
    encoding: str = "utf-8-sig",
    strip: bool = True,
    has_header: bool | None = None,
) -> Hierarchy:
    """Read an ARX-style hierarchy CSV.

    Expected row shape:

    ```text
    raw_value,level1_value,level2_value,...
    ```

    The returned tuple includes the raw value as level 0, which matches the
    in-memory hierarchy format used by `tabular.py`.
    """

    csv_path = _resolve_existing_path(path)
    with csv_path.open("r", newline="", encoding=encoding) as handle:
        sample = handle.read(4096)
        handle.seek(0)
        dialect = _dialect_from_sample(sample, delimiter)
        reader = csv.reader(handle, dialect=dialect)
        rows = [
            tuple(_clean_cell(cell, strip) for cell in row)
            for row in reader
            if row and any(_clean_cell(cell, strip) != "" for cell in row)
        ]

    if not rows:
        raise ValueError(f"hierarchy CSV contains no rows: {csv_path}")

    if has_header is True or (has_header is None and _looks_like_header(rows[0])):
        rows = rows[1:]

    hierarchy: dict[str, tuple[str, ...]] = {}
    expected_width: int | None = None
    for line_number, row in enumerate(rows, start=1):
        if len(row) < 1 or row[0] == "":
            raise ValueError(f"hierarchy CSV has an empty raw value at row {line_number}")
        if expected_width is None:
            expected_width = len(row)
        elif len(row) != expected_width:
            raise ValueError(
                "hierarchy CSV rows must have the same number of columns: "
                f"{csv_path}, row {line_number}"
            )
        if row[0] in hierarchy:
            raise ValueError(f"duplicate hierarchy raw value {row[0]!r}: {csv_path}")
        hierarchy[row[0]] = row

    if not hierarchy:
        raise ValueError(f"hierarchy CSV contains no hierarchy rows: {csv_path}")
    return hierarchy


def read_hierarchies_from_paths(
    paths_by_attribute: Mapping[str, str | Path],
    *,
    delimiter: str | None = None,
    encoding: str = "utf-8-sig",
    strip: bool = True,
    has_header: bool | None = None,
) -> Hierarchies:
    """Read multiple hierarchy CSV files keyed by quasi-identifier name."""

    return {
        attribute: read_hierarchy_csv(
            path,
            delimiter=delimiter,
            encoding=encoding,
            strip=strip,
            has_header=has_header,
        )
        for attribute, path in paths_by_attribute.items()
    }


def write_data_csv(
    path: str | Path,
    rows: Sequence[Row],
    *,
    fieldnames: Sequence[str] | None = None,
    delimiter: str = ",",
    encoding: str = "utf-8",
) -> None:
    """Write row dictionaries to a header-based CSV file."""

    if not rows:
        raise ValueError("rows must contain at least one row")
    output_path = Path(path).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_fieldnames = list(fieldnames or rows[0].keys())

    with output_path.open("w", newline="", encoding=encoding) as handle:
        writer = csv.DictWriter(handle, fieldnames=resolved_fieldnames, delimiter=delimiter)
        writer.writeheader()
        for row in rows:
            writer.writerow({fieldname: row.get(fieldname, "") for fieldname in resolved_fieldnames})


def _resolve_existing_path(path: str | Path) -> Path:
    csv_path = Path(path).expanduser()
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file does not exist: {csv_path}")
    if not csv_path.is_file():
        raise ValueError(f"CSV path is not a file: {csv_path}")
    return csv_path


def _dialect_from_sample(sample: str, delimiter: str | None) -> csv.Dialect:
    if delimiter is not None:
        return _single_delimiter_dialect(delimiter)
    try:
        return csv.Sniffer().sniff(sample, delimiters=DEFAULT_DELIMITERS)
    except csv.Error:
        return csv.get_dialect("excel")


def _single_delimiter_dialect(delimiter: str) -> csv.Dialect:
    if len(delimiter) != 1:
        raise ValueError("delimiter must be exactly one character")

    class SingleDelimiterDialect(csv.excel):
        pass

    SingleDelimiterDialect.delimiter = delimiter
    return SingleDelimiterDialect


def _clean_cell(value: object, strip: bool) -> str:
    text = "" if value is None else str(value)
    return text.strip() if strip else text


def _validate_fieldnames(fieldnames: Sequence[str], path: Path) -> None:
    if any(fieldname == "" for fieldname in fieldnames):
        raise ValueError(f"data CSV contains an empty header name: {path}")
    if len(set(fieldnames)) != len(fieldnames):
        raise ValueError(f"data CSV contains duplicate header names: {path}")


def _looks_like_header(row: Sequence[str]) -> bool:
    lowered = [cell.lower() for cell in row]
    if lowered and lowered[0] in HEADER_MARKERS:
        return True
    return any(cell.startswith("level") for cell in lowered[1:])
