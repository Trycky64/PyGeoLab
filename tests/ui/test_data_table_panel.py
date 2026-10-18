"""Unit and UI tests for DataTablePanel lightweight spreadsheet (PyGeoLab 1.3 Section 5)."""

import uuid

from PySide6.QtCore import Qt

from pygeolab.commands import CommandHistory
from pygeolab.data.dataset import DatasetObject
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.model.styles import Style
from pygeolab.ui.data_table_panel import DatasetTableModel, DataTablePanel


def test_dataset_table_model_basic_operations() -> None:
    model = DatasetTableModel()
    ds = DatasetObject.from_xy([1.0, 2.0], [10.0, 20.0], name="TestDS")
    model.set_dataset(ds)

    assert model.rowCount() == 2
    assert model.columnCount() == 2
    assert model.headerData(0, Qt.Orientation.Horizontal) == "x"
    assert model.headerData(1, Qt.Orientation.Horizontal) == "y"

    # Read data
    idx_00 = model.index(0, 0)
    assert model.data(idx_00) == "1"

    # Edit data
    success = model.setData(idx_00, "15.5")
    assert success
    assert model.data(idx_00) == "15.5"

    # Reject non-numeric input
    fail = model.setData(idx_00, "invalid_num")
    assert not fail

    # Add row
    model.add_row([3.0, 30.0])
    assert model.rowCount() == 3

    # Add column
    model.add_column("z")
    assert model.columnCount() == 3
    assert model.headerData(2, Qt.Orientation.Horizontal) == "z"

    # Convert back to DatasetObject
    res_ds = model.to_dataset("ExportedDS")
    assert res_ds.name == "ExportedDS"
    assert res_ds.row_count == 3
    assert res_ds.col_count == 3


def test_data_table_panel_ui_lifecycle(qtbot) -> None:
    doc = Document()
    history = CommandHistory()
    ds = DatasetObject.from_xy([1.0, 2.0, 3.0], [4.0, 5.0, 6.0], name="DS1")
    obj = GeoObject(
        id=str(uuid.uuid4()),
        name="DS1",
        kind="dataset",
        geometry=ds,
        params=ds.to_dict(),
        style=Style(),
    )
    doc.add(obj)

    panel = DataTablePanel(doc, history.execute)
    panel.refresh()

    assert panel._dataset_combo.count() == 1
    assert panel._model.rowCount() == 3

    # Add row through UI button
    panel._btn_add_row.click()
    assert panel._model.rowCount() == 4

    # Add column through UI button
    panel._btn_add_col.click()
    assert panel._model.columnCount() == 3

    # Delete column
    panel._table_view.setCurrentIndex(panel._model.index(0, 2))
    panel._btn_del_col.click()
    assert panel._model.columnCount() == 2

    # Select and delete row
    panel._table_view.selectRow(3)
    panel._btn_del_row.click()
    assert panel._model.rowCount() == 3

    # Copy selection
    panel._table_view.selectAll()
    panel.copy_selection()

    # Change plot mode combo
    panel._plot_kind_combo.setCurrentIndex(1)  # regression
    updated_obj = doc.get(obj.id)
    assert isinstance(updated_obj.geometry, DatasetObject)
    assert updated_obj.geometry.plot_kind == "regression"

    # Dataset switching
    ds2 = DatasetObject.from_1d([100.0, 200.0], name="DS2")
    obj2 = GeoObject(
        id=str(uuid.uuid4()),
        name="DS2",
        kind="dataset",
        geometry=ds2,
        params=ds2.to_dict(),
        style=Style(),
    )
    doc.add(obj2)
    panel.refresh()
    assert panel._dataset_combo.count() == 2
    panel._dataset_combo.setCurrentIndex(1)
    assert panel._active_object_id == obj2.id
    assert panel._model.columnCount() == 1
    assert panel._model.rowCount() == 2


def test_data_table_panel_empty_dataset(qtbot) -> None:
    doc = Document()
    panel = DataTablePanel(doc)
    qtbot.addWidget(panel)
    panel.refresh()
    assert panel._active_object_id is None
    assert panel._model.rowCount() == 0
