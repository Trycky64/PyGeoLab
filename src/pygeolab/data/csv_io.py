"""Robust CSV parsing and serialization for numerical datasets.

Supports automatic delimiter detection, decimal separator handling,
Unicode and UTF-8-sig encoding, optional headers, missing values policy,
file path handling, and strict domain validation.
"""

from __future__ import annotations

import csv
import io
import math
from collections.abc import Sequence
from pathlib import Path

MISSING_TOKENS = frozenset({"", "na", "n/a", "nan", "null", "?", "-", "none"})


def detect_delimiter(sample: str) -> str:
    """Sniff the most likely delimiter among ',', ';', '\t', or ' '."""
    lines = [line.strip() for line in sample.splitlines() if line.strip()]
    if not lines:
        return ","

    candidates = (";", "\t", ",", " ")
    # Check consistency: delimiter should appear the same non-zero
    # number of times on each sample line
    consistent_candidates: list[tuple[int, str]] = []
    for c in candidates:
        counts = [line.count(c) for line in lines[:10]]
        first_count = counts[0]
        if first_count > 0 and all(cnt == first_count for cnt in counts):
            # Prioritize ';' and '\t' because ',' and ' ' can appear inside values or numbers
            priority = 2 if c in (";", "\t") else 1
            consistent_candidates.append((priority, c))

    if consistent_candidates:
        consistent_candidates.sort(key=lambda item: item[0], reverse=True)
        return consistent_candidates[0][1]

    scores: dict[str, int] = {c: 0 for c in candidates}
    for line in lines[:10]:
        for c in candidates:
            scores[c] += line.count(c)

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
    missing_policy: str = "error",  # "error", "skip", "fill"
    fill_value: float = 0.0,
    max_rows: int = 100_000,
    max_cols: int = 1_000,
) -> tuple[tuple[str, ...], tuple[tuple[float, ...], ...]]:
    """Parse CSV text or file path into column names and numerical rows.

    Raises ValueError with descriptive context if data is invalid,
    contains missing values violating policy, or exceeds size limits.
    Raises FileNotFoundError if source is a missing file path.
    """
    if missing_policy not in ("error", "skip", "fill"):
        raise ValueError(
            f"Politique de valeurs manquantes invalide : {missing_policy!r} "
            "(attendu : 'error', 'skip' ou 'fill')"
        )

    content: str
    if isinstance(source, Path):
        if not source.exists() or not source.is_file():
            raise FileNotFoundError(f"Fichier CSV introuvable : {source}")
        try:
            content = source.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            content = source.read_text(encoding="latin-1")
    elif isinstance(source, str) and "\n" not in source and "\r" not in source:
        p = Path(source)
        if p.exists() and p.is_file():
            try:
                content = p.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError:
                content = p.read_text(encoding="latin-1")
        else:
            content = source
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
    if expected_cols > max_cols:
        raise ValueError(
            f"Le nombre de colonnes ({expected_cols}) dépasse la limite autorisée ({max_cols})"
        )

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
        skip_row = False
        for col_idx, cell in enumerate(row):
            is_missing = cell.lower() in MISSING_TOKENS
            if is_missing:
                if missing_policy == "error":
                    col_name = headers[col_idx]
                    raise ValueError(
                        f"Ligne {line_num}, colonne {col_idx + 1} ({col_name}) : "
                        f"valeur manquante '{cell}'"
                    )
                elif missing_policy == "skip":
                    skip_row = True
                    break
                else:  # "fill"
                    parsed_row.append(fill_value)
                    continue

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

        if not skip_row:
            data_rows.append(tuple(parsed_row))

    return tuple(headers), tuple(data_rows)


def read_csv_file(
    path: str | Path,
    delimiter: str | None = None,
    has_header: bool | None = None,
    decimal: str | None = None,
    missing_policy: str = "error",
    fill_value: float = 0.0,
    max_rows: int = 100_000,
    max_cols: int = 1_000,
) -> tuple[tuple[str, ...], tuple[tuple[float, ...], ...]]:
    """Convenience helper to read CSV directly from a file path."""
    return read_csv(
        Path(path),
        delimiter=delimiter,
        has_header=has_header,
        decimal=decimal,
        missing_policy=missing_policy,
        fill_value=fill_value,
        max_rows=max_rows,
        max_cols=max_cols,
    )


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


def write_csv_file(
    path: str | Path,
    column_names: Sequence[str],
    rows: Sequence[Sequence[float]],
    delimiter: str = ",",
    decimal: str = ".",
    include_header: bool = True,
    encoding: str = "utf-8",
) -> None:
    """Write formatted CSV content directly to disk with proper encoding."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    content = write_csv(
        column_names=column_names,
        rows=rows,
        delimiter=delimiter,
        decimal=decimal,
        include_header=include_header,
    )
    target.write_text(content, encoding=encoding)
