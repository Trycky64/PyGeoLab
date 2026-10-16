"""Editable property panel for the currently selected document object."""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import replace
from typing import cast

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from pygeolab.commands import (
    ChangeLockCommand,
    ChangeNumberValueCommand,
    ChangeParametersCommand,
    ChangeStyleCommand,
    ChangeVisibilityCommand,
    Command,
    CompositeCommand,
    MovePointCommand,
    RenameObjectCommand,
)
from pygeolab.geometry import (
    EPSILON,
    Circle2D,
    Ellipse2D,
    Hyperbola2D,
    Line2D,
    Parabola2D,
    Point2D,
    Ray2D,
    Segment2D,
    Vector2D,
    analyze_circle,
    analyze_ellipse,
    analyze_hyperbola,
    analyze_line,
    analyze_parabola,
    analyze_ray,
    analyze_segment,
    angle_between_lines,
    are_lines_orthogonal,
    are_lines_parallel,
    are_points_collinear,
    distance_point_to_line,
    distance_point_to_point,
    format_number,
    midpoint,
    project_point_on_line,
)
from pygeolab.geometry.intersections import IntersectionKind, line_line
from pygeolab.math_engine.functions import ParametricFunctionObject
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.model.styles import Style


class PropertiesPanel(QWidget):
    """Edit common object metadata using reversible history commands."""

    selectionRequested = Signal(object)

    def __init__(
        self,
        document: Document,
        execute_command: Callable[[Command], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._document = document
        self._execute_command = execute_command
        self._object_id: str | None = None
        self._object_ids: frozenset[str] = frozenset()
        self._updating = False
        self._changing_parameter = False
        self._refresh_scheduled = False
        self._empty = QLabel(self.tr("Sélectionnez un objet"), self)
        self._name = QLineEdit(self)
        self._visible = QCheckBox(self)
        self._locked = QCheckBox(self)
        self._color = QPushButton(self.tr("Choisir…"), self)
        self._width = QDoubleSpinBox(self)
        self._width.setRange(0.5, 20)
        self._width.setSingleStep(0.5)
        self._point_size = QDoubleSpinBox(self)
        self._point_size.setRange(1, 30)
        self._line_style = QComboBox(self)
        self._line_style.addItems(["solid", "dash", "dot"])
        self._label = QCheckBox(self)
        self._opacity = QDoubleSpinBox(self)
        self._opacity.setRange(0, 1)
        self._opacity.setSingleStep(0.05)
        self._parents = QLabel("—", self)
        self._descendants = QLabel("—", self)
        self._select_parents_button = QPushButton(self.tr("Sélectionner les parents"), self)
        self._select_descendants_button = QPushButton(self.tr("Sélectionner les descendants"), self)
        self._parameters_widget = QWidget(self)
        self._parameters_form = QFormLayout(self._parameters_widget)
        self._parameters_form.setContentsMargins(0, 0, 0, 0)
        self._parameter_editors: dict[str, QDoubleSpinBox] = {}
        self._analytics_widget = QWidget(self)
        self._analytics_form = QFormLayout(self._analytics_widget)
        self._analytics_form.setContentsMargins(0, 0, 0, 0)
        form = QFormLayout(self)
        form.addRow(self._empty)
        form.addRow(self.tr("Nom"), self._name)
        form.addRow(self.tr("Visible"), self._visible)
        form.addRow(self.tr("Verrouillé"), self._locked)
        form.addRow(self.tr("Couleur"), self._color)
        form.addRow(self.tr("Épaisseur"), self._width)
        form.addRow(self.tr("Taille du point"), self._point_size)
        form.addRow(self.tr("Style de ligne"), self._line_style)
        form.addRow(self.tr("Afficher le label"), self._label)
        form.addRow(self.tr("Opacité du remplissage"), self._opacity)
        form.addRow(self.tr("Dépendances"), self._parents)
        form.addRow(self._select_parents_button)
        form.addRow(self.tr("Descendants"), self._descendants)
        form.addRow(self._select_descendants_button)
        form.addRow(self.tr("Paramètres"), self._parameters_widget)
        form.addRow(self.tr("Propriétés analytiques"), self._analytics_widget)
        self._name.editingFinished.connect(self._rename)
        self._visible.toggled.connect(self._change_visibility)
        self._locked.toggled.connect(self._change_locked)
        self._color.clicked.connect(self._choose_color)
        self._width.valueChanged.connect(lambda _value: self._change_style("width"))
        self._point_size.valueChanged.connect(lambda _value: self._change_style("point_size"))
        self._line_style.currentTextChanged.connect(lambda _value: self._change_style("line_style"))
        self._label.toggled.connect(lambda _value: self._change_style("show_label"))
        self._opacity.valueChanged.connect(lambda _value: self._change_style("fill_opacity"))
        self._select_parents_button.clicked.connect(self._select_parents)
        self._select_descendants_button.clicked.connect(self._select_descendants)
        self._unsubscribe = document.subscribe(self._document_changed)
        self.refresh()

    def set_document(self, document: Document) -> None:
        """Switch document subscriptions and clear stale selection."""
        self._unsubscribe()
        self._document = document
        self._object_id = None
        self._object_ids = frozenset()
        self._unsubscribe = document.subscribe(self._document_changed)
        self.refresh()

    def dispose(self) -> None:
        """Release the document subscription before the widget is destroyed."""
        self._unsubscribe()

    def set_selection(self, object_ids: frozenset[str] | set[str]) -> None:
        """Inspect one object or expose common style controls for multiple objects."""
        self._object_ids = frozenset(
            object_id for object_id in object_ids if object_id in self._document.objects
        )
        self._object_id = next(iter(self._object_ids)) if len(self._object_ids) == 1 else None
        self.refresh()

    def refresh(self) -> None:
        """Synchronize controls from the immutable current object value."""
        objects = [
            self._document.get(object_id)
            for object_id in self._object_ids
            if object_id in self._document.objects
        ]
        obj = objects[0] if objects else None
        enabled = bool(objects)
        single = len(objects) == 1
        self._empty.setText(
            self.tr("Sélectionnez un objet")
            if not objects
            else self.tr(f"{len(objects)} objets sélectionnés")
        )
        self._empty.setVisible(not single)
        widgets = (
            self._visible,
            self._locked,
            self._color,
            self._width,
            self._point_size,
            self._line_style,
            self._label,
            self._opacity,
        )
        for widget in widgets:
            widget.setEnabled(enabled)
        self._name.setEnabled(single)
        parent_ids = frozenset(parent_id for item in objects for parent_id in item.dependencies)
        descendant_ids = self._document.descendants(self._object_ids) if objects else frozenset()
        self._parents.setText(self._object_names(parent_ids))
        self._descendants.setText(self._object_names(descendant_ids))
        self._select_parents_button.setEnabled(bool(parent_ids))
        self._select_descendants_button.setEnabled(bool(descendant_ids))
        self._refresh_parameters(obj if single else None)
        self._refresh_analytics(objects)
        if obj is None:
            return
        self._updating = True
        try:
            self._name.setText(obj.name)
            self._visible.setChecked(obj.visible)
            self._locked.setChecked(obj.locked)
            self._width.setValue(obj.style.width)
            self._point_size.setValue(obj.style.point_size)
            self._line_style.setCurrentText(obj.style.line_style)
            self._label.setChecked(obj.style.show_label)
            self._opacity.setValue(obj.style.fill_opacity)
            self._color.setText(obj.style.color)
        finally:
            self._updating = False

    def _rename(self) -> None:
        if self._updating or self._object_id is None:
            return
        obj = self._document.get(self._object_id)
        name = self._name.text().strip()
        if name and name != obj.name:
            self._execute_command(RenameObjectCommand(self._document, obj.id, name))

    def _change_visibility(self, visible: bool) -> None:
        if self._updating or not self._object_ids:
            return
        commands = [
            ChangeVisibilityCommand(self._document, object_id, visible)
            for object_id in self._object_ids
            if self._document.get(object_id).visible != visible
        ]
        self._execute_commands(commands)

    def _change_locked(self, locked: bool) -> None:
        if self._updating or not self._object_ids:
            return
        commands = [
            ChangeLockCommand(self._document, object_id, locked)
            for object_id in self._object_ids
            if self._document.get(object_id).locked != locked
        ]
        self._execute_commands(commands)

    def _choose_color(self) -> None:
        if not self._object_ids:
            return
        color = QColorDialog.getColor(parent=self)
        if color.isValid():
            self._apply_style_value("color", color.name())

    def _change_style(self, field: str) -> None:
        if self._updating or not self._object_ids:
            return
        values: dict[str, str | float | bool] = {
            "width": self._width.value(),
            "point_size": self._point_size.value(),
            "line_style": self._line_style.currentText(),
            "show_label": self._label.isChecked(),
            "fill_opacity": self._opacity.value(),
        }
        self._apply_style_value(field, values[field])

    def _apply_style_value(self, field: str, value: str | float | bool) -> None:
        commands: list[Command] = []
        for object_id in self._object_ids:
            obj = self._document.get(object_id)
            style = _replace_style_value(obj.style, field, value)
            if style != obj.style:
                commands.append(ChangeStyleCommand(self._document, object_id, style))
        self._execute_commands(commands)

    def _execute_commands(self, commands: Sequence[Command]) -> None:
        if not commands:
            return
        self._execute_command(commands[0] if len(commands) == 1 else CompositeCommand(commands))

    def _refresh_parameters(self, obj: GeoObject | None) -> None:
        while self._parameters_form.rowCount():
            self._parameters_form.removeRow(0)
        self._parameter_editors.clear()
        if obj is None:
            self._parameters_widget.setEnabled(False)
            return

        point_geom = obj.geometry if isinstance(obj.geometry, Point2D) else None
        editable: tuple[str, ...]
        if point_geom is not None and not obj.params:
            editable = ("x", "y")
        else:
            editable = _editable_parameter_names(obj.kind)

        for key in editable:
            raw_val = obj.params.get(key)
            if key in ("x", "y") and point_geom is not None:
                raw_val = point_geom.x if key == "x" else point_geom.y
            if isinstance(raw_val, bool) or not isinstance(raw_val, (int, float)):
                continue
            if not math.isfinite(raw_val):
                continue

            editor = QDoubleSpinBox(self._parameters_widget)
            editor.setDecimals(6)
            editor.setRange(-1e9, 1e9)
            editor.setSingleStep(0.1)

            # A parameter is dependent if it is point coordinate on a dependent object
            is_dependent = bool(obj.dependencies) and key in ("x", "y")

            if is_dependent:
                editor.setEnabled(False)
                editor.setToolTip(self.tr("Objet dépendant : calculé automatiquement"))
            elif obj.locked:
                editor.setEnabled(False)
                editor.setToolTip(self.tr("Objet verrouillé"))

            if key in ("radius", "a", "b"):
                editor.setMinimum(1e-6)
            elif obj.kind == "number" and key == "value":
                minimum = obj.params.get("minimum", -1e9)
                maximum = obj.params.get("maximum", 1e9)
                if isinstance(minimum, (int, float)) and isinstance(maximum, (int, float)):
                    editor.setRange(float(minimum), float(maximum))
            elif key == "index":
                editor.setDecimals(0)
                editor.setSingleStep(1)

            editor.setValue(float(raw_val))
            if not is_dependent and not obj.locked:
                editor.valueChanged.connect(
                    lambda new_value, parameter=key: self._change_parameter(parameter, new_value)
                )
            self._parameters_form.addRow(key, editor)
            self._parameter_editors[key] = editor
        self._parameters_widget.setEnabled(bool(self._parameter_editors))

    def _refresh_analytics(self, objects: Sequence[GeoObject]) -> None:
        while self._analytics_form.rowCount():
            self._analytics_form.removeRow(0)

        if not objects:
            self._analytics_widget.setVisible(False)
            return

        def add_row(label: str, value: str) -> None:
            val_lbl = QLabel(value, self._analytics_widget)
            val_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self._analytics_form.addRow(label, val_lbl)

        if len(objects) == 1:
            geom = objects[0].geometry
            if isinstance(geom, Point2D):
                add_row(
                    self.tr("Coordonnées"),
                    f"({format_number(geom.x)}, {format_number(geom.y)})",
                )
                r = math.hypot(geom.x, geom.y)
                theta_deg = math.degrees(math.atan2(geom.y, geom.x))
                add_row(
                    self.tr("Coordonnées polaires"),
                    f"r = {format_number(r)}, θ = {format_number(theta_deg)}°",
                )
            elif isinstance(geom, Line2D):
                analysis = analyze_line(geom)
                add_row(self.tr("Équation cartésienne"), analysis.cartesian_equation)
                add_row(self.tr("Équation réduite"), analysis.slope_intercept_equation)
                slope_str = (
                    format_number(analysis.slope)
                    if analysis.slope is not None
                    else self.tr("Indéfinie (droite verticale)")
                )
                add_row(self.tr("Pente"), slope_str)
                add_row(
                    self.tr("Vecteur directeur"),
                    f"({format_number(-geom.b)}, {format_number(geom.a)})",
                )
            elif isinstance(geom, Circle2D):
                c_analysis = analyze_circle(geom)
                add_row(self.tr("Équation canonique"), c_analysis.canonical_equation)
                add_row(self.tr("Équation générale"), c_analysis.general_equation)
                add_row(self.tr("Rayon"), format_number(geom.radius))
                add_row(self.tr("Périmètre"), format_number(geom.perimeter))
                add_row(self.tr("Aire"), format_number(geom.area))
            elif isinstance(geom, Ellipse2D):
                e_res = analyze_ellipse(geom)
                add_row(self.tr("Équation"), str(e_res["equation"]))
                add_row(self.tr("Centre"), str(e_res["center"]))
                add_row(self.tr("Demi-grand axe a"), format_number(float(e_res["a"])))
                add_row(self.tr("Demi-petit axe b"), format_number(float(e_res["b"])))
                add_row(self.tr("Distance focale c"), format_number(float(e_res["c"])))
                add_row(self.tr("Excentricité"), format_number(float(e_res["eccentricity"])))
                add_row(self.tr("Foyers"), str(e_res["foci"]))
                add_row(self.tr("Périmètre"), format_number(float(e_res["perimeter"])))
                add_row(self.tr("Aire"), format_number(float(e_res["area"])))
            elif isinstance(geom, Parabola2D):
                p_res = analyze_parabola(geom)
                add_row(self.tr("Équation"), str(p_res["equation"]))
                add_row(self.tr("Sommet"), str(p_res["vertex"]))
                add_row(self.tr("Foyer"), str(p_res["focus"]))
                add_row(self.tr("Paramètre p"), format_number(float(p_res["parameter"])))
                add_row(self.tr("Directrice"), str(p_res["directrix"]))
            elif isinstance(geom, Hyperbola2D):
                h_res = analyze_hyperbola(geom)
                add_row(self.tr("Équation"), str(h_res["equation"]))
                add_row(self.tr("Centre"), str(h_res["center"]))
                add_row(self.tr("Demi-axe a"), format_number(float(h_res["a"])))
                add_row(self.tr("Demi-axe b"), format_number(float(h_res["b"])))
                add_row(self.tr("Excentricité"), format_number(float(h_res["eccentricity"])))
                add_row(self.tr("Foyers"), str(h_res["foci"]))
                add_row(self.tr("Sommets"), str(h_res["vertices"]))
                add_row(self.tr("Asymptote 1"), str(h_res["asymptote1"]))
                add_row(self.tr("Asymptote 2"), str(h_res["asymptote2"]))
            elif isinstance(geom, Segment2D):
                s_analysis = analyze_segment(geom)
                add_row(self.tr("Longueur"), format_number(float(s_analysis["length"])))
                add_row(
                    self.tr("Milieu"),
                    f"({format_number(float(s_analysis['midpoint_x']))}, "
                    f"{format_number(float(s_analysis['midpoint_y']))})",
                )
                add_row(self.tr("Droite support"), str(s_analysis["line_equation"]))
            elif isinstance(geom, Ray2D):
                r_analysis = analyze_ray(geom)
                add_row(
                    self.tr("Origine"),
                    f"({format_number(float(r_analysis['origin_x']))}, "
                    f"{format_number(float(r_analysis['origin_y']))})",
                )
                add_row(self.tr("Droite support"), str(r_analysis["line_equation"]))
            elif isinstance(geom, ParametricFunctionObject):
                add_row(
                    self.tr("Équation paramétrique"),
                    f"x({geom.parameter}) = {geom.x_source}, y({geom.parameter}) = {geom.y_source}",
                )
                add_row(
                    self.tr("Intervalle du paramètre"),
                    f"[{format_number(geom.t_min)}, {format_number(geom.t_max)}]",
                )
                if geom.external_dependencies:
                    add_row(
                        self.tr("Dépendances"),
                        ", ".join(sorted(geom.external_dependencies)),
                    )

        elif len(objects) == 2:
            g1, g2 = objects[0].geometry, objects[1].geometry
            if isinstance(g1, Point2D) and isinstance(g2, Point2D):
                dist = distance_point_to_point(g1, g2)
                mid = midpoint(g1, g2)
                vec = Vector2D.between(g1, g2)
                add_row(self.tr("Distance"), format_number(dist))
                add_row(
                    self.tr("Milieu"),
                    f"({format_number(mid.x)}, {format_number(mid.y)})",
                )
                add_row(
                    self.tr("Vecteur"),
                    f"({format_number(vec.x)}, {format_number(vec.y)})",
                )
            elif (isinstance(g1, Point2D) and isinstance(g2, Line2D)) or (
                isinstance(g2, Point2D) and isinstance(g1, Line2D)
            ):
                pt = g1 if isinstance(g1, Point2D) else cast(Point2D, g2)
                line = g2 if isinstance(g2, Line2D) else cast(Line2D, g1)
                dist = distance_point_to_line(pt, line)
                proj = project_point_on_line(pt, line)
                add_row(self.tr("Distance"), format_number(dist))
                add_row(
                    self.tr("Projection"),
                    f"({format_number(proj.x)}, {format_number(proj.y)})",
                )
            elif isinstance(g1, Line2D) and isinstance(g2, Line2D):
                ang = angle_between_lines(g1, g2)
                ang_deg = math.degrees(ang)
                add_row(
                    self.tr("Angle"),
                    f"{format_number(ang_deg)}° ({format_number(ang)} rad)",
                )
                is_par = are_lines_parallel(g1, g2)
                is_ortho = are_lines_orthogonal(g1, g2)
                add_row(
                    self.tr("Parallèles"),
                    self.tr("Oui") if is_par else self.tr("Non"),
                )
                add_row(
                    self.tr("Orthogonales"),
                    self.tr("Oui") if is_ortho else self.tr("Non"),
                )
                res = line_line(g1, g2)
                if res.kind == IntersectionKind.ONE and res.points:
                    inter_pt = res.points[0]
                    add_row(
                        self.tr("Intersection"),
                        f"({format_number(inter_pt.x)}, {format_number(inter_pt.y)})",
                    )
                else:
                    add_row(self.tr("Intersection"), self.tr("Aucune (parallèles)"))
            elif (isinstance(g1, Point2D) and isinstance(g2, Circle2D)) or (
                isinstance(g2, Point2D) and isinstance(g1, Circle2D)
            ):
                pt = g1 if isinstance(g1, Point2D) else cast(Point2D, g2)
                circ = g2 if isinstance(g2, Circle2D) else cast(Circle2D, g1)
                dist_center = distance_point_to_point(pt, circ.center)
                add_row(self.tr("Distance au centre"), format_number(dist_center))
                if abs(dist_center - circ.radius) <= EPSILON:
                    pos = self.tr("Sur le cercle")
                elif dist_center < circ.radius:
                    pos = self.tr("Intérieur")
                else:
                    pos = self.tr("Extérieur")
                add_row(self.tr("Position"), pos)

        elif len(objects) == 3:
            if all(isinstance(o.geometry, Point2D) for o in objects):
                p1 = cast(Point2D, objects[0].geometry)
                p2 = cast(Point2D, objects[1].geometry)
                p3 = cast(Point2D, objects[2].geometry)
                col = are_points_collinear(p1, p2, p3)
                add_row(
                    self.tr("Colinéaires"),
                    self.tr("Oui") if col else self.tr("Non"),
                )

        self._analytics_widget.setVisible(self._analytics_form.rowCount() > 0)

    def _change_parameter(self, key: str, value: float) -> None:
        if self._updating or self._object_id is None:
            return
        if not math.isfinite(value):
            return
        obj = self._document.get(self._object_id)
        if obj.locked:
            return
        if key in ("x", "y") and obj.dependencies:
            return

        if obj.kind == "point":
            raw_x = obj.params.get("x", 0.0)
            raw_y = obj.params.get("y", 0.0)
            cur_x = float(raw_x) if isinstance(raw_x, (int, float)) else 0.0
            cur_y = float(raw_y) if isinstance(raw_y, (int, float)) else 0.0
            new_x = float(value) if key == "x" else cur_x
            new_y = float(value) if key == "y" else cur_y
            if not (math.isfinite(new_x) and math.isfinite(new_y)):
                return
            before = Point2D(cur_x, cur_y)
            after = Point2D(new_x, new_y)
            if before != after:
                self._changing_parameter = True
                try:
                    self._execute_command(MovePointCommand(self._document, obj.id, before, after))
                finally:
                    self._changing_parameter = False
            return

        if obj.kind == "circle_radius" and key == "radius" and value <= 0:
            return
        if obj.kind in ("ellipse_center", "hyperbola") and key in ("a", "b") and value <= 0:
            return
        if obj.kind == "scale" and key == "factor" and value == 0:
            return

        if obj.kind == "number" and key == "value":
            self._changing_parameter = True
            try:
                self._execute_command(ChangeNumberValueCommand(self._document, obj.id, value))
            finally:
                self._changing_parameter = False
            return

        params = dict(obj.params)
        params[key] = int(value) if key == "index" else value
        if params != dict(obj.params):
            self._changing_parameter = True
            try:
                self._execute_command(ChangeParametersCommand(self._document, obj.id, params))
            finally:
                self._changing_parameter = False

    def _select_parents(self) -> None:
        parent_ids = frozenset(
            parent_id
            for object_id in self._object_ids
            for parent_id in self._document.get(object_id).dependencies
        )
        if parent_ids:
            self.selectionRequested.emit(parent_ids)

    def _select_descendants(self) -> None:
        descendants = self._document.descendants(self._object_ids)
        if descendants:
            self.selectionRequested.emit(descendants)

    def _object_names(self, object_ids: frozenset[str]) -> str:
        names = [obj.name for obj in self._document.objects.values() if obj.id in object_ids]
        return ", ".join(names) if names else "—"

    def _document_changed(self) -> None:
        if not self._changing_parameter:
            self.refresh()
            return
        if not self._refresh_scheduled:
            self._refresh_scheduled = True
            QTimer.singleShot(0, self._run_scheduled_refresh)

    def _run_scheduled_refresh(self) -> None:
        self._refresh_scheduled = False
        self.refresh()


def _replace_style_value(style: Style, field: str, value: str | float | bool) -> Style:
    if field == "color" and isinstance(value, str):
        return replace(style, color=value)
    if field == "line_style" and isinstance(value, str):
        return replace(style, line_style=value)
    if field == "show_label" and isinstance(value, bool):
        return replace(style, show_label=value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        numeric = float(value)
        if field == "width":
            return replace(style, width=numeric)
        if field == "point_size":
            return replace(style, point_size=numeric)
        if field == "fill_opacity":
            return replace(style, fill_opacity=numeric)
    raise ValueError(f"Propriété de style invalide : {field}")


def _editable_parameter_names(kind: str) -> tuple[str, ...]:
    return {
        "point": ("x", "y"),
        "number": ("value",),
        "circle_radius": ("radius",),
        "intersection": ("index",),
        "point_on": ("t",),
        "rotate": ("angle",),
        "scale": ("factor",),
        "ellipse_center": ("b",),
        "hyperbola": ("a",),
    }.get(kind, ())
