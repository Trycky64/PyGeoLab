"""Comprehensive robustness unit tests for CSV import/export (PyGeoLab 1.3 Section 8).

Verifies:
- Delimiter detection (comma, semicolon, tab, space).
- Decimal separator detection (dot vs comma).
- UTF-8 and Unicode file paths and content.
- Optional header inference and explicit header override.
- Missing values handling policies (error, skip, fill).
- Row and column limits.
- Precise error messages with line and column numbers.
- File-level and string-level I/O.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pygeolab.data.csv_io import (
    detect_decimal_separator,
    detect_delimiter,
    read_csv,
    read_csv_file,
    write_csv,
    write_csv_file,
)
from pygeolab.data.dataset import DatasetObject


def test_detect_delimiter_and_decimals() -> None:
    assert detect_delimiter("1.0,2.0\n3.0,4.0") == ","
    assert detect_delimiter("1,0;2,0\n3,0;4,0") == ";"
    assert detect_delimiter("1.0\t2.0\n3.0\t4.0") == "\t"
    assert detect_delimiter("1.0 2.0\n3.0 4.0") == " "
    assert detect_delimiter("") == ","

    # Decimal separator detection
    assert detect_decimal_separator("1.5,2.5", ",") == "."
    assert detect_decimal_separator("1,5;2,5", ";") == ","
    assert detect_decimal_separator("1.5;2.5", ";") == "."


def test_read_csv_unicode_path_and_utf8(tmp_path: Path) -> None:
    unicode_dir = tmp_path / "dossier_accentué_€_α"
    unicode_dir.mkdir()
    csv_file = unicode_dir / "mes_données_test_★.csv"

    # CSV with UTF-8 BOM, accents in header, and semicolon delimiter
    content = "\ufeffAbscisse (µm);Ordonnée (m/s)\n1,25;3,50\n2,50;7,00\n"
    csv_file.write_text(content, encoding="utf-8")

    headers, rows = read_csv(csv_file)
    assert headers == ("Abscisse (µm)", "Ordonnée (m/s)")
    assert len(rows) == 2
    assert rows[0] == (1.25, 3.50)
    assert rows[1] == (2.50, 7.00)

    # Test via convenience read_csv_file
    h2, r2 = read_csv_file(str(csv_file))
    assert h2 == headers
    assert r2 == rows


def test_read_csv_missing_values_policies() -> None:
    csv_data = "x,y\n1.0,2.0\n3.0,NA\n5.0,6.0\n"

    # Policy "error": raises ValueError
    with pytest.raises(ValueError, match="valeur manquante"):
        read_csv(csv_data, missing_policy="error")

    # Policy "skip": row 2 is dropped
    headers, rows_skip = read_csv(csv_data, missing_policy="skip")
    assert headers == ("x", "y")
    assert len(rows_skip) == 2
    assert rows_skip == ((1.0, 2.0), (5.0, 6.0))

    # Policy "fill": NA is replaced by fill_value (-999.0)
    _, rows_fill = read_csv(csv_data, missing_policy="fill", fill_value=-999.0)
    assert len(rows_fill) == 3
    assert rows_fill[1] == (3.0, -999.0)

    # Invalid policy
    with pytest.raises(ValueError, match="Politique de valeurs manquantes invalide"):
        read_csv(csv_data, missing_policy="invalid")


def test_read_csv_optional_headers() -> None:
    data_without_header = "10.0,20.0\n30.0,40.0\n"

    # Auto-detection: recognizes numbers in first row -> no header
    h_auto, r_auto = read_csv(data_without_header, has_header=None)
    assert h_auto == ("x", "y")
    assert len(r_auto) == 2

    # Explicit has_header=False
    h_false, r_false = read_csv(data_without_header, has_header=False)
    assert h_false == ("x", "y")
    assert len(r_false) == 2

    # Explicit has_header=True (uses first row as header)
    h_true, r_true = read_csv(data_without_header, has_header=True)
    assert h_true == ("10.0", "20.0")
    assert len(r_true) == 1
    assert r_true[0] == (30.0, 40.0)


def test_read_csv_size_limits() -> None:
    data = "a,b\n1,2\n3,4\n5,6\n7,8\n"

    with pytest.raises(ValueError, match="limite autorisée"):
        read_csv(data, max_rows=2)

    with pytest.raises(ValueError, match="limite autorisée"):
        read_csv(data, max_cols=1)


def test_read_csv_error_cases(tmp_path: Path) -> None:
    # Missing file path
    with pytest.raises(FileNotFoundError, match="introuvable"):
        read_csv(tmp_path / "non_existant.csv")

    # Empty content
    with pytest.raises(ValueError, match="vide"):
        read_csv("")

    with pytest.raises(ValueError, match="vide"):
        read_csv("   \n   \n")

    # Inconsistent column count across rows
    with pytest.raises(ValueError, match="colonnes trouvées"):
        read_csv("x,y\n1,2\n3,4,5\n")

    # Non-numeric text in cell
    with pytest.raises(ValueError, match="valeur numérique invalide"):
        read_csv("x,y\n1,abc\n")


def test_write_csv_and_file_io(tmp_path: Path) -> None:
    cols = ("Temps", "Vitesse")
    rows = ((0.0, 10.5), (1.0, 20.25))

    # String export with custom delimiter and comma decimal
    csv_str = write_csv(cols, rows, delimiter=";", decimal=",", include_header=True)
    assert "Temps;Vitesse" in csv_str
    assert "0;10,5" in csv_str

    # File export with Unicode path
    target = tmp_path / "export_données_€" / "result.csv"
    write_csv_file(target, cols, rows, delimiter=";", decimal=",")
    assert target.exists()

    # Read back and verify
    h, r = read_csv(target)
    assert h == cols
    assert r == rows


def test_dataset_from_csv_and_to_csv_file(tmp_path: Path) -> None:
    file_path = tmp_path / "ds.csv"
    file_path.write_text("x,y\n1.0,2.0\n3.0,N/A\n", encoding="utf-8")

    # from_csv with fill policy
    ds = DatasetObject.from_csv(file_path, name="LoadedDS", missing_policy="fill", fill_value=0.0)
    assert ds.name == "LoadedDS"
    assert ds.row_count == 2
    assert ds.rows[1] == (3.0, 0.0)

    # Export to file
    out_path = tmp_path / "ds_out.csv"
    ds.to_csv_file(out_path)
    assert out_path.exists()
    assert "LoadedDS" not in out_path.read_text(encoding="utf-8")  # CSV contains data, not name
    assert "x,y" in out_path.read_text(encoding="utf-8")
