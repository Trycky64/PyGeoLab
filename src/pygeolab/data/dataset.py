"""Immutable domain representation of numerical datasets.

Provides multi-column tabular data structures, 1D and 2D series representations,
strict validation, metadata tracking, CSV serialization, and point coordinate extraction.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

from pygeolab.data.csv_io import read_csv, write_csv
from pygeolab.geometry import Point2D


@dataclass(frozen=True, slots=True)
class DatasetObject:
    """An immutable, strictly-validated numerical dataset.

    Can represent single numerical series (1D), paired series (X/Y), or arbitrary
    multi-column tables where all observations are finite floating-point values.
    """

    name: str = "Dataset"
    column_names: tuple[str, ...] = ("x", "y")
    rows: tuple[tuple[float, ...], ...] = ()
    metadata: MappingProxyType[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Le nom du dataset doit être une chaîne non vide")

        if not isinstance(self.column_names, (tuple, list)) or len(self.column_names) == 0:
            raise ValueError("Un dataset doit posséder au moins une colonne")

        cols = tuple(str(c).strip() for c in self.column_names)
        if any(not c for c in cols):
            raise ValueError("Les noms de colonnes ne peuvent pas être vides")
        if len(set(cols)) != len(cols):
            raise ValueError("Les noms de colonnes doivent être uniques")
        object.__setattr__(self, "column_names", cols)

        validated_rows: list[tuple[float, ...]] = []
        expected_cols = len(cols)
        for i, row in enumerate(self.rows):
            if not isinstance(row, (tuple, list)) or len(row) != expected_cols:
                found_len = len(row) if isinstance(row, (tuple, list)) else "non-liste"
                raise ValueError(
                    f"Ligne {i + 1} : {found_len} valeurs trouvées, {expected_cols} attendues"
                )
            parsed_cells: list[float] = []
            for j, cell in enumerate(row):
                if isinstance(cell, bool) or not isinstance(cell, (int, float)):
                    raise ValueError(
                        f"Ligne {i + 1}, colonne {j + 1} ({cols[j]}) : "
                        f"valeur non numérique {cell!r}"
                    )
                val = float(cell)
                if not math.isfinite(val):
                    raise ValueError(
                        f"Ligne {i + 1}, colonne {j + 1} ({cols[j]}) : valeur non finie ({val})"
                    )
                parsed_cells.append(val)
            validated_rows.append(tuple(parsed_cells))
        object.__setattr__(self, "rows", tuple(validated_rows))

        # Ensure metadata is an immutable MappingProxyType
        if not isinstance(self.metadata, MappingProxyType):
            raw_meta = dict(self.metadata) if isinstance(self.metadata, Mapping) else {}
            object.__setattr__(self, "metadata", MappingProxyType(raw_meta))

    @property
    def row_count(self) -> int:
        """Total number of rows in the dataset."""
        return len(self.rows)

    @property
    def col_count(self) -> int:
        """Total number of columns in the dataset."""
        return len(self.column_names)

    @property
    def is_empty(self) -> bool:
        """True if the dataset has no rows."""
        return self.row_count == 0

    @property
    def is_1d(self) -> bool:
        """True if the dataset has exactly one column."""
        return self.col_count == 1

    @property
    def is_2d(self) -> bool:
        """True if the dataset has two or more columns."""
        return self.col_count >= 2

    def column(self, index_or_name: int | str) -> tuple[float, ...]:
        """Extract a single column by 0-based index or column name."""
        if isinstance(index_or_name, str):
            if index_or_name not in self.column_names:
                raise KeyError(f"Colonne introuvable : {index_or_name!r}")
            idx = self.column_names.index(index_or_name)
        else:
            idx = index_or_name
            if not 0 <= idx < self.col_count:
                raise IndexError(f"Index de colonne {idx} hors bornes [0, {self.col_count - 1}]")
        return tuple(row[idx] for row in self.rows)

    @property
    def x_values(self) -> tuple[float, ...]:
        """Extract the X numerical series (column 0 if 2D, or 1..N indices if 1D)."""
        if self.is_2d:
            return self.column(0)
        return tuple(float(i + 1) for i in range(self.row_count))

    @property
    def y_values(self) -> tuple[float, ...]:
        """Extract the Y numerical series (column 1 if 2D, or column 0 if 1D)."""
        if self.is_2d:
            return self.column(1)
        if self.is_1d:
            return self.column(0)
        return ()

    @property
    def points(self) -> tuple[Point2D, ...]:
        """Convert paired (X, Y) series to immutable Point2D instances."""
        return tuple(Point2D(x, y) for x, y in zip(self.x_values, self.y_values, strict=False))

    def with_rows(self, new_rows: Sequence[Sequence[float]]) -> DatasetObject:
        """Return a copy with updated rows, keeping name, columns, and metadata."""
        return DatasetObject(
            name=self.name,
            column_names=self.column_names,
            rows=tuple(tuple(float(v) for v in r) for r in new_rows),
            metadata=self.metadata,
        )

    def with_metadata(self, new_metadata: Mapping[str, Any]) -> DatasetObject:
        """Return a copy with updated metadata."""
        return DatasetObject(
            name=self.name,
            column_names=self.column_names,
            rows=self.rows,
            metadata=MappingProxyType(dict(new_metadata)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize dataset parameters into a JSON-compatible dictionary for GeoObject."""
        return {
            "column_names": list(self.column_names),
            "rows": [list(row) for row in self.rows],
            "metadata": dict(self.metadata),
        }

    def to_csv(
        self,
        delimiter: str = ",",
        decimal: str = ".",
        include_header: bool = True,
    ) -> str:
        """Export dataset contents to a formatted CSV string."""
        return write_csv(
            self.column_names,
            self.rows,
            delimiter=delimiter,
            decimal=decimal,
            include_header=include_header,
        )

    @classmethod
    def from_1d(
        cls,
        values: Sequence[float],
        name: str = "Dataset",
        col_name: str = "y",
        metadata: Mapping[str, Any] | None = None,
    ) -> DatasetObject:
        """Construct a 1D dataset from a single series of values."""
        rows = tuple((float(v),) for v in values)
        meta = MappingProxyType(dict(metadata or {}))
        return cls(name=name, column_names=(col_name,), rows=rows, metadata=meta)

    @classmethod
    def from_xy(
        cls,
        x: Sequence[float],
        y: Sequence[float],
        name: str = "Dataset",
        x_col: str = "x",
        y_col: str = "y",
        metadata: Mapping[str, Any] | None = None,
    ) -> DatasetObject:
        """Construct a 2D dataset from paired X and Y coordinate series."""
        if len(x) != len(y):
            raise ValueError(
                f"Les séries X et Y doivent avoir la même longueur ({len(x)} != {len(y)})"
            )
        rows = tuple((float(xi), float(yi)) for xi, yi in zip(x, y, strict=True))
        meta = MappingProxyType(dict(metadata or {}))
        return cls(name=name, column_names=(x_col, y_col), rows=rows, metadata=meta)

    @classmethod
    def from_rows(
        cls,
        column_names: Sequence[str],
        rows: Sequence[Sequence[float]],
        name: str = "Dataset",
        metadata: Mapping[str, Any] | None = None,
    ) -> DatasetObject:
        """Construct a dataset from column names and a sequence of numerical rows."""
        meta = MappingProxyType(dict(metadata or {}))
        return cls(
            name=name,
            column_names=tuple(str(c) for c in column_names),
            rows=tuple(tuple(float(v) for v in r) for r in rows),
            metadata=meta,
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], name: str = "Dataset") -> DatasetObject:
        """Reconstruct a dataset from a serialized dictionary mapping."""
        cols = tuple(str(c) for c in data.get("column_names", ("x", "y")))
        raw_rows = data.get("rows", ())
        rows = tuple(tuple(float(v) for v in r) for r in raw_rows)
        raw_meta = data.get("metadata", {})
        metadata = raw_meta if isinstance(raw_meta, Mapping) else {}
        meta_proxy = MappingProxyType(dict(metadata))
        return cls(name=name, column_names=cols, rows=rows, metadata=meta_proxy)

    @classmethod
    def from_csv(
        cls,
        source: str | Path,
        name: str = "Dataset",
        delimiter: str | None = None,
        has_header: bool | None = None,
        decimal: str | None = None,
        max_rows: int = 100_000,
    ) -> DatasetObject:
        """Construct a dataset from CSV text or a file path."""
        headers, rows = read_csv(
            source,
            delimiter=delimiter,
            has_header=has_header,
            decimal=decimal,
            max_rows=max_rows,
        )
        return cls(name=name, column_names=headers, rows=rows)
