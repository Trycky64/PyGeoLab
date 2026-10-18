"""Unit tests for DatasetObject model, CSV I/O, persistence, and UI integration."""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType

import pytest

from pygeolab.commands import ChangeParametersCommand, CommandHistory, CreateObjectCommand
from pygeolab.data import DatasetObject, read_csv
from pygeolab.geometry import Point2D
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.persistence import load_project, save_project
from pygeolab.ui.algebra_panel import AlgebraPanel
from pygeolab.ui.properties_panel import PropertiesPanel


def test_dataset_1d_creation_and_properties() -> None:
    values = [10.0, 25.5, 42.0]
    ds = DatasetObject.from_1d(values, name="Measurements", col_name="val")

    assert ds.name == "Measurements"
    assert ds.column_names == ("val",)
    assert ds.row_count == 3
    assert ds.col_count == 1
    assert not ds.is_empty
    assert ds.is_1d
    assert not ds.is_2d
    assert ds.column(0) == (10.0, 25.5, 42.0)
    assert ds.column("val") == (10.0, 25.5, 42.0)
    assert ds.x_values == (1.0, 2.0, 3.0)
    assert ds.y_values == (10.0, 25.5, 42.0)
    assert ds.points == (
        Point2D(1.0, 10.0),
        Point2D(2.0, 25.5),
        Point2D(3.0, 42.0),
    )


def test_dataset_2d_xy_creation_and_properties() -> None:
    x = [0.0, 1.5, 3.0]
    y = [2.0, 4.5, 7.0]
    ds = DatasetObject.from_xy(x, y, name="XYData", x_col="abscissa", y_col="ordinate")

    assert ds.name == "XYData"
    assert ds.column_names == ("abscissa", "ordinate")
    assert ds.row_count == 3
    assert ds.col_count == 2
    assert ds.is_2d
    assert not ds.is_1d
    assert ds.column("abscissa") == (0.0, 1.5, 3.0)
    assert ds.column("ordinate") == (2.0, 4.5, 7.0)
    assert ds.x_values == (0.0, 1.5, 3.0)
    assert ds.y_values == (2.0, 4.5, 7.0)
    assert ds.points == (
        Point2D(0.0, 2.0),
        Point2D(1.5, 4.5),
        Point2D(3.0, 7.0),
    )


def test_dataset_xy_length_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="même longueur"):
        DatasetObject.from_xy([1.0, 2.0], [3.0])


def test_dataset_strict_validation() -> None:
    # Empty or whitespace name
    with pytest.raises(ValueError, match="chaîne non vide"):
        DatasetObject(name="   ", column_names=("x",), rows=())

    # No columns
    with pytest.raises(ValueError, match="au moins une colonne"):
        DatasetObject(name="Valid", column_names=(), rows=())

    # Empty column name
    with pytest.raises(ValueError, match="ne peuvent pas être vides"):
        DatasetObject(name="Valid", column_names=("x", "  "), rows=())

    # Duplicate column names
    with pytest.raises(ValueError, match="doivent être uniques"):
        DatasetObject(name="Valid", column_names=("x", "x"), rows=())

    # Row length mismatch
    with pytest.raises(ValueError, match="attendues"):
        DatasetObject(name="Valid", column_names=("x", "y"), rows=((1.0, 2.0), (3.0,)))

    # Non-numeric value
    with pytest.raises(ValueError, match="non numérique"):
        DatasetObject(name="Valid", column_names=("x",), rows=((True,),))  # type: ignore[arg-type]

    # Non-finite value (NaN or Inf)
    with pytest.raises(ValueError, match="non finie"):
        DatasetObject(name="Valid", column_names=("x",), rows=((float("nan"),),))

    with pytest.raises(ValueError, match="non finie"):
        DatasetObject(name="Valid", column_names=("x",), rows=((float("inf"),),))


def test_dataset_metadata_and_immutability() -> None:
    meta = {"source": "lab_experiment", "sensor_id": 42}
    ds = DatasetObject.from_rows(
        ["colA", "colB"],
        [[1.0, 2.0], [3.0, 4.0]],
        name="Experiment",
        metadata=meta,
    )
    assert isinstance(ds.metadata, MappingProxyType)
    assert ds.metadata["source"] == "lab_experiment"
    assert ds.metadata["sensor_id"] == 42

    # Verify immutability: cannot mutate metadata
    with pytest.raises(TypeError):
        ds.metadata["source"] = "new"  # type: ignore[index]

    # with_rows copy
    ds2 = ds.with_rows([[10.0, 20.0]])
    assert ds2.row_count == 1
    assert ds2.column("colA") == (10.0,)
    assert ds.row_count == 2  # original unchanged

    # with_metadata copy
    ds3 = ds.with_metadata({"device": "test"})
    assert ds3.metadata["device"] == "test"
    assert "source" not in ds3.metadata


def test_dataset_column_indexing_and_key_errors() -> None:
    ds = DatasetObject.from_xy([1.0], [2.0])
    with pytest.raises(IndexError, match="hors bornes"):
        ds.column(5)
    with pytest.raises(KeyError, match="introuvable"):
        ds.column("non_existent")


def test_csv_import_and_export_round_trip() -> None:
    csv_text = "x,y\n1.0,2.5\n3.0,4.75\n"
    ds = DatasetObject.from_csv(csv_text, name="FromCSV")

    assert ds.name == "FromCSV"
    assert ds.column_names == ("x", "y")
    assert ds.row_count == 2
    assert ds.x_values == (1.0, 3.0)
    assert ds.y_values == (2.5, 4.75)

    exported = ds.to_csv()
    assert "x,y" in exported
    assert "1,2.5" in exported
    assert "3,4.75" in exported


def test_csv_delimiters_and_decimal_commas() -> None:
    # Semicolon delimiter with decimal comma
    csv_eu = "Temps;Vitesse\n0;0\n1,5;22,4\n3;45,6\n"
    ds = DatasetObject.from_csv(csv_eu, name="EUFormat")
    assert ds.column_names == ("Temps", "Vitesse")
    assert ds.column("Temps") == (0.0, 1.5, 3.0)
    assert ds.column("Vitesse") == (0.0, 22.4, 45.6)

    # Export with semicolon and decimal comma
    exported = ds.to_csv(delimiter=";", decimal=",")
    assert "Temps;Vitesse" in exported
    assert "1,5;22,4" in exported


def test_csv_without_header_and_single_column() -> None:
    csv_raw = "10.5\n20.25\n30.75\n"
    ds = DatasetObject.from_csv(csv_raw, has_header=False)
    assert ds.column_names == ("y",)
    assert ds.row_count == 3
    assert ds.column(0) == (10.5, 20.25, 30.75)


def test_csv_error_handling() -> None:
    # Empty CSV
    with pytest.raises(ValueError, match="vide"):
        read_csv("")

    # Only whitespace
    with pytest.raises(ValueError, match="vide"):
        read_csv("   \n\n  \n")

    # Exceeding max_rows
    big_csv = "x\n" + "\n".join(str(i) for i in range(50))
    with pytest.raises(ValueError, match="limite autorisée"):
        read_csv(big_csv, max_rows=10)

    # Inconsistent column count
    bad_rows = "x,y\n1,2\n3,4,5\n"
    with pytest.raises(ValueError, match="colonnes trouvées"):
        read_csv(bad_rows)

    # Non-numeric cell in data
    invalid_data = "x,y\n1,2\n3,NOT_A_NUMBER\n"
    with pytest.raises(ValueError, match="valeur numérique invalide"):
        read_csv(invalid_data)


def test_csv_file_read_utf8_bom(tmp_path: Path) -> None:
    file_path = tmp_path / "data_bom.csv"
    # Write with UTF-8 BOM
    file_path.write_text("\ufeffcol1,col2\n1.0,2.0\n", encoding="utf-8")
    ds = DatasetObject.from_csv(file_path)
    assert ds.column_names == ("col1", "col2")
    assert ds.row_count == 1
    assert ds.column(0) == (1.0,)


def test_document_dataset_integration_and_undo_redo() -> None:
    doc = Document()
    history = CommandHistory()

    ds = DatasetObject.from_xy([1.0, 2.0], [10.0, 20.0], name="D1")
    geo_obj = GeoObject(kind="dataset", name="D1", params=ds.to_dict())

    # Create via command
    cmd = CreateObjectCommand(doc, geo_obj)
    history.execute(cmd)

    retrieved = doc.get(geo_obj.id)
    assert retrieved.valid
    assert isinstance(retrieved.geometry, DatasetObject)
    assert retrieved.geometry.row_count == 2
    assert retrieved.geometry.points == (Point2D(1.0, 10.0), Point2D(2.0, 20.0))

    # Edit dataset params via ChangeParametersCommand
    updated_ds = ds.with_rows([[5.0, 50.0], [6.0, 60.0], [7.0, 70.0]])
    edit_cmd = ChangeParametersCommand(doc, geo_obj.id, updated_ds.to_dict())
    history.execute(edit_cmd)

    retrieved2 = doc.get(geo_obj.id)
    assert isinstance(retrieved2.geometry, DatasetObject)
    assert retrieved2.geometry.row_count == 3
    assert retrieved2.geometry.points[0] == Point2D(5.0, 50.0)

    # Undo edit
    history.undo()
    retrieved_after_undo = doc.get(geo_obj.id)
    assert isinstance(retrieved_after_undo.geometry, DatasetObject)
    assert retrieved_after_undo.geometry.row_count == 2

    # Redo edit
    history.redo()
    retrieved_after_redo = doc.get(geo_obj.id)
    assert isinstance(retrieved_after_redo.geometry, DatasetObject)
    assert retrieved_after_redo.geometry.row_count == 3


def test_dataset_persistence_roundtrip(tmp_path: Path) -> None:
    doc = Document()
    ds = DatasetObject.from_rows(
        ["Time", "Altitude"],
        [[0.0, 100.0], [1.0, 120.5], [2.0, 150.0]],
        name="FlightData",
        metadata={"unit": "meters"},
    )
    doc.add(GeoObject(kind="dataset", name="FlightData", params=ds.to_dict()))

    file_path = tmp_path / "dataset_project.pgl"
    save_project(doc, file_path)

    loaded_doc = load_project(file_path)
    loaded_obj = next(iter(loaded_doc.objects.values()))
    assert loaded_obj.name == "FlightData"
    assert loaded_obj.kind == "dataset"
    assert loaded_obj.valid
    assert isinstance(loaded_obj.geometry, DatasetObject)
    assert loaded_obj.geometry.column_names == ("Time", "Altitude")
    assert loaded_obj.geometry.row_count == 3
    assert loaded_obj.geometry.column("Altitude") == (100.0, 120.5, 150.0)
    assert loaded_obj.geometry.metadata["unit"] == "meters"


def test_algebra_and_properties_panel_dataset(qapp: object) -> None:
    doc = Document()
    ds = DatasetObject.from_xy([1.0, 2.0, 3.0], [4.0, 5.0, 6.0], name="D_Test")
    obj = doc.add(GeoObject(kind="dataset", name="D_Test", params=ds.to_dict()))

    # AlgebraPanel category and format
    algebra = AlgebraPanel(doc, execute_command=lambda cmd: None)
    assert algebra._category(obj.geometry) == "Jeux de données"
    assert "2 cols, 3 lignes" in algebra._format_value(obj)

    # PropertiesPanel card
    props = PropertiesPanel(doc, execute_command=lambda cmd: None)
    props.set_selection(frozenset({obj.id}))
    assert props._analytics_form.rowCount() > 0
    assert not props._analytics_widget.isHidden()
