"""Unit and system tests for ValueTablePanel, ValueTableModel, and CSV export."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.ui.main_window import MainWindow
from pygeolab.ui.value_table_panel import ValueTableModel, ValueTablePanel


def test_value_table_model_basic(qapp: QApplication) -> None:
    del qapp
    headers = ["x", "f(x)"]
    rows = [["0", "0"], ["1", "1"], ["2", "4"]]
    model = ValueTableModel(headers, rows)

    assert model.rowCount() == 3
    assert model.columnCount() == 2
    assert model.headerData(0, Qt.Orientation.Horizontal) == "x"
    assert model.headerData(1, Qt.Orientation.Horizontal) == "f(x)"
    assert model.headerData(0, Qt.Orientation.Vertical) == "1"
    assert model.data(model.index(1, 1)) == "1"
    assert model.data(model.index(2, 1)) == "4"


def test_value_table_panel_cartesian_function(qapp: QApplication) -> None:
    del qapp
    doc = Document()
    doc.add(
        GeoObject(
            "function",
            "f",
            params={"variable": "x", "source": "x^2 - 1", "domain": [-2.0, 2.0]},
        )
    )

    panel = ValueTablePanel(doc)
    assert panel.function_combo.count() >= 1

    panel.start_spin.setValue(-2.0)
    panel.end_spin.setValue(2.0)
    panel.step_spin.setValue(1.0)
    panel.compute_table()

    assert panel._headers == ["x", "f(x)"]
    assert len(panel._rows) == 5  # -2, -1, 0, 1, 2
    # f(-2) = 3, f(-1) = 0, f(0) = -1, f(1) = 0, f(2) = 3
    assert panel._rows[0] == ["-2", "3"]
    assert panel._rows[1] == ["-1", "0"]
    assert panel._rows[2] == ["0", "-1"]
    assert panel._rows[3] == ["1", "0"]
    assert panel._rows[4] == ["2", "3"]

    csv_text = panel.to_csv_string()
    assert "x,f(x)" in csv_text
    assert "0,-1" in csv_text

    # Test clipboard copy
    panel.copy_to_clipboard()
    cb = QApplication.clipboard()
    if cb is not None:
        assert "f(x)" in cb.text()

    panel.dispose()
    panel.close()


def test_value_table_panel_parametric_curve(qapp: QApplication) -> None:
    del qapp
    doc = Document()
    doc.add(
        GeoObject(
            "parametric",
            "c_param",
            params={
                "parameter": "t",
                "x_source": "2 * cos(t)",
                "y_source": "2 * sin(t)",
                "t_min": 0.0,
                "t_max": 6.28,
            },
        )
    )

    panel = ValueTablePanel(doc)
    panel.start_spin.setValue(0.0)
    panel.end_spin.setValue(3.14159)
    panel.step_spin.setValue(1.0)
    panel.compute_table()

    assert panel._headers == ["t", "x(t)", "y(t)"]
    assert len(panel._rows) >= 4

    csv_text = panel.to_csv_string()
    assert "t,x(t),y(t)" in csv_text

    panel.dispose()
    panel.close()


def test_value_table_panel_polar_curve(qapp: QApplication) -> None:
    del qapp
    doc = Document()
    doc.add(
        GeoObject(
            "polar",
            "c_pol",
            params={
                "parameter": "theta",
                "r_source": "1 + cos(theta)",
                "theta_min": 0.0,
                "theta_max": 6.28,
            },
        )
    )

    panel = ValueTablePanel(doc)
    panel.start_spin.setValue(0.0)
    panel.end_spin.setValue(3.0)
    panel.step_spin.setValue(1.0)
    panel.compute_table()

    assert panel._headers == ["theta", "r(theta)", "x", "y"]
    assert len(panel._rows) == 4  # 0, 1, 2, 3

    csv_text = panel.to_csv_string()
    assert "theta,r(theta),x,y" in csv_text

    panel.dispose()
    panel.close()


def test_value_table_panel_validation_and_errors(qapp: QApplication, monkeypatch) -> None:
    del qapp
    doc = Document()
    doc.add(
        GeoObject(
            "function",
            "f",
            params={"variable": "x", "source": "1 / x"},
        )
    )

    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: None)
    panel = ValueTablePanel(doc)

    # Step <= 0
    panel.step_spin.setValue(0.0)
    panel.compute_table()
    assert len(panel._rows) == 0

    # Start > End
    panel.start_spin.setValue(5.0)
    panel.end_spin.setValue(1.0)
    panel.step_spin.setValue(1.0)
    panel.compute_table()
    assert len(panel._rows) == 0

    # Undefined values: x=0 for 1/x -> displayed as "indéfini"
    panel.start_spin.setValue(-1.0)
    panel.end_spin.setValue(1.0)
    panel.step_spin.setValue(1.0)
    panel.compute_table()
    assert len(panel._rows) == 3
    assert panel._rows[1][0] == "0"
    assert "indéfini" in panel._rows[1][1] or panel._rows[1][1] == "indéfini"

    panel.dispose()
    panel.close()


def test_main_window_value_table_integration(qapp: QApplication, monkeypatch) -> None:
    del qapp
    window = MainWindow(offer_recovery=False)
    monkeypatch.setattr(window, "_confirm_discard_changes", lambda: True)

    assert hasattr(window, "value_table_dock")
    assert hasattr(window, "value_table_panel")

    # Add a function into the document and test table refresh
    window.document.add(
        GeoObject(
            "function",
            "g",
            params={"variable": "x", "source": "2 * x + 3"},
        )
    )
    window.value_table_panel.refresh_functions()
    assert window.value_table_panel.function_combo.count() >= 1

    window.close()
