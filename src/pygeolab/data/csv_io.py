"""Robust CSV parsing and serialization for numerical datasets.

Supports automatic delimiter detection, decimal separator handling,
Unicode and UTF-8-sig encoding, optional headers, and strict validation.
"""

from __future__ import annotations

import csv
import io
import math
from collections.abc import Sequence
from pathlib import Path


def detect_delimiter(sample: str) -> str:
    """Sniff the most likely delimiter among ',', ';', '\t', or ' '."""
    lines = [line.strip() for line in sample.splitlines() if line.strip()]
    if not lines:
        return ","
    # Check frequency of candidates on non-empty lines
    candidates = (",", ";", "\t", " ")
    scores: dict[str, int] = {c: 0 for c in candidates}
    for line in lines[:10]:
        for c in candidates:
            count = line.count(c)
            if count > 0:
                scores[c] += count
    best = max(candidates, key=lambda c: scores[c])
    return best if scores[best] > 0 else ","


def detect_decimal_separator(sample: str, delimiter: str) -> str:
    """Sniff whether numbers in sample use '.' or ',' as decimal point."""
    if delimiter == ",":
        return "."  # If comma is column delimiter, decimal point is dot
    lines = [line.strip() for line in sample.splitlines() if line.strip()]
    comma_count = 0
    dot_count = 0
    for line in lines[:20]:
        tokens = line.split(delimiter)
        for token in tokens:
            token = token.strip()
            if "," in token:
                comma_count += 1
            if "." in token:
                dot_count += 1
    return "," if comma_count > dot_count else "."


def read_csv(
    source: str | Path,
    delimiter: str | None = None,
    has_header: bool | None = None,
    decimal: str | None = None,
    max_rows: int = 100_000,
) -> tuple[tuple[str, ...], tuple[tuple[float, ...], ...]]:
    """Parse CSV text or file into column names and numerical rows.

    Raises ValueError with descriptive context if the data is invalid,
    contains non-numerical cells outside the header, or exceeds max_rows.
    """
    if isinstance(source, Path):
        try:
            content = source.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            content = source.read_text(encoding="latin-1")
    else:
        content = source

    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        raise ValueError("Le fichier ou contenu CSV est vide")

    sample = "\n".join(lines[:25])
    actual_delimiter = delimiter if delimiter is not None else detect_delimiter(sample)
    actual_decimal = (
        decimal if decimal is not None else detect_decimal_separator(sample, actual_delimiter)
    )

    reader = csv.reader(io.StringIO(content), delimiter=actual_delimiter)
    raw_rows: list[list[str]] = []
    for row in reader:
        # Strip each cell, ignore empty rows
        stripped = [cell.strip() for cell in row]
        if any(cell != "" for cell in stripped):
            raw_rows.append(stripped)

    if not raw_rows:
        raise ValueError("Aucune donnée exploitable trouvée dans le CSV")

    # Determine header
    first_row = raw_rows[0]
    inferred_header = False
    if has_header is None:
        # If any element in first row cannot be parsed as a float, it's a header
        for cell in first_row:
            cleaned = cell.replace(actual_decimal, ".") if actual_decimal != "." else cell
            try:
                float(cleaned)
            except ValueError:
                inferred_header = True
                break
    else:
        inferred_header = has_header

    start_idx = 0
    if inferred_header:
        raw_headers = first_row
        start_idx = 1
    else:
        num_cols = len(first_row)
        if num_cols == 1:
            raw_headers = ["y"]
        elif num_cols == 2:
            raw_headers = ["x", "y"]
        else:
            raw_headers = [f"col_{i + 1}" for i in range(num_cols)]

    expected_cols = len(raw_headers)
    if expected_cols == 0:
        raise ValueError("Le tableau CSV ne contient aucune colonne")

    # Clean headers (avoid empty, ensure unique)
    headers: list[str] = []
    seen: dict[str, int] = {}
    for i, h in enumerate(raw_headers):
        base_name = h if h else f"col_{i + 1}"
        if base_name in seen:
            seen[base_name] += 1
            headers.append(f"{base_name}_{seen[base_name]}")
        else:
            seen[base_name] = 1
            headers.append(base_name)

    data_rows: list[tuple[float, ...]] = []
    for line_num, row in enumerate(raw_rows[start_idx:], start=start_idx + 1):
        if len(data_rows) >= max_rows:
            raise ValueError(
                f"La taille du fichier dépasse la limite autorisée ({max_rows} lignes)"
            )
        if len(row) != expected_cols:
            raise ValueError(
                f"Ligne {line_num} : {len(row)} colonnes trouvées, {expected_cols} attendues"
            )
        parsed_row: list[float] = []
        for col_idx, cell in enumerate(row):
            cleaned = cell.replace(actual_decimal, ".") if actual_decimal != "." else cell
            try:
                val = float(cleaned)
            except ValueError as exc:
                col_name = headers[col_idx]
                raise ValueError(
                    f"Ligne {line_num}, colonne {col_idx + 1} ({col_name}) : "
                    f"valeur numérique invalide '{cell}'"
                ) from exc
            if not math.isfinite(val):
                raise ValueError(
                    f"Ligne {line_num}, colonne {col_idx + 1} : valeur non finie (NaN ou Infini)"
                )
            parsed_row.append(val)
        data_rows.append(tuple(parsed_row))

    return tuple(headers), tuple(data_rows)


def write_csv(
    column_names: Sequence[str],
    rows: Sequence[Sequence[float]],
    delimiter: str = ",",
    decimal: str = ".",
    include_header: bool = True,
) -> str:
    """Format column names and numerical rows into a valid CSV string."""
    output = io.StringIO()
    writer = csv.writer(output, delimiter=delimiter, lineterminator="\n")
    if include_header:
        writer.writerow(list(column_names))
    for row in rows:
        formatted_row: list[str] = []
        for val in row:
            s = f"{val:.10g}"
            if decimal != ".":
                s = s.replace(".", decimal)
            formatted_row.append(s)
        writer.writerow(formatted_row)
    return output.getvalue()
