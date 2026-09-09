# PyGeoLab 1.1 user guide

[Français](user-guide.fr.md) · **English**

## Workspace

The center canvas contains the dynamic construction. The Algebra, Properties, Sliders, and Numerical Analysis panels show and edit the same document. Use **View** to show or hide panels and **Home** to reset the viewport.

Pan with the middle mouse button and zoom with the wheel. The grid spacing adapts to the current zoom level.

## Construction tools

Choose a tool from the toolbar, then click the required objects or positions:

- **Point** creates a free point.
- **Segment**, **Line**, **Ray**, and **Vector** use two points.
- **Circle** uses a center and a point on the circle.
- **Polygon** accepts several vertices and finishes on the first point.
- **Midpoint**, **Intersection**, **Parallel**, and **Perpendicular** create dependent objects.
- **Perpendicular bisector**, **Angle bisector**, and **Projection** build standard constructions.
- **Point on object** constrains a point to a supported curve.
- **Center-radius circle** and **Circumcircle** provide advanced circle definitions.
- **Distance** and **Angle** create dynamic measurements.
- **Translation**, **Rotation**, **Point reflection**, **Line reflection**, and **Scaling** create transformed objects.

The status bar reports the active tool and the canvas shows a preview. Press **Esc** to cancel an unfinished construction.

## Snapping

Snapping can target the grid, existing points, projections onto objects, and nearby intersections. Toggle it with **M** or in **View > Snapping**. Hold **Alt** while clicking to suspend snapping temporarily. Preferences control the global state and pixel threshold.

## Selection and grouped editing

Click an object to select it. Drag an empty canvas area to select by rectangle. **Ctrl** toggles individual objects and **Shift** extends the selection. Repeated clicks cycle through overlapping objects.

Use **Ctrl+A** to select all, **Ctrl+Shift+A** to clear, **Delete** to remove the selection, and **Ctrl+D** to duplicate independent objects. The canvas context menu controls visibility, locking, duplication, and display order. Grouped style edits are available in Properties and participate in Undo/Redo.

## Algebra and Properties

The Algebra panel supports text filtering, name/type sorting, and configurable grouping. Double-click a name to rename it. Visibility and locking can be changed directly in the tree. Invalid objects show their error details.

Properties edits names, numeric parameters, visibility, locking, color, width, point size, line style, labels, and fill opacity. It also lists parents and descendants and can select either group.

## Functions

Create a function with **Objects > New function**. Enter its name, independent variable, expression, and optional display domain. Existing numeric sliders referenced by name become dependencies automatically.

Select a function and use **Objects > Edit function** to change it. Expression errors are shown without blocking the document. **View > Functions** controls sampling quality and optional roots, extrema, intersections, and derivative overlays. Sampling adapts to zoom and separates discontinuities to avoid artificial asymptote segments.

## Sliders

Create a slider from the Algebra panel or **Objects > New slider**. Set its value, minimum, maximum, and step. The Sliders panel supports direct entry, reset, keyboard adjustment, play/pause, speed, and ping-pong playback. Animation recomputes only descendants and does not add one Undo command per frame.

## Numerical analysis and measurements

The Numerical Analysis panel computes derivatives, integrals, roots, extrema, and function intersections over a bounded interval. Configure tolerance and sample count before calculating. Results are limited to a safe count, and invalid domains or discontinuities produce a readable message.

Length, area, and angle measurements remain linked to their source objects and update after edits or slider animation.

## Files, autosave, and recovery

Projects use the validated JSON `.pgl` format. PyGeoLab 1.1 opens version 1 files created by PyGeoLab 1.0. **File > Recent files** removes missing entries automatically and provides a clear action.

Autosave writes a separate recovery file atomically at the configured interval. After an interrupted session, startup offers to restore or ignore it. A normal save removes obsolete recovery data.

## Preferences and language

Preferences centralize language, theme, grid, axes, labels, snapping, default styles, export quality, transparency, and autosave. Choose **System**, **English**, or **Français** for the interface language; a language change applies after restart. **Restore defaults** resets the complete preference set.

## Export and clipboard

PNG and SVG exports can target the current viewport, the complete document, or the selection. PNG supports transparency, custom dimensions, and a resolution factor. SVG includes curves and labels with clipping. The current viewport can also be copied to the clipboard as PNG or SVG.

## Main shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+N`, `Ctrl+O`, `Ctrl+S` | New, open, save |
| `Ctrl+Z`, `Ctrl+Y` | Undo, redo |
| `Delete` | Delete selection |
| `Ctrl+A`, `Ctrl+Shift+A` | Select all, clear selection |
| `Ctrl+D` | Duplicate selection |
| `S`, `P`, `G`, `D`, `C`, `Y` | Select, point, segment, line, circle, polygon |
| `M` | Toggle snapping |
| `Home` | Reset view |
| `Esc` | Cancel current construction |
| `F1` | Show all active shortcuts |

## Diagnostics

**Help > Open log folder** opens rotating logs. **Help > Copy system information** copies the PyGeoLab version, build identifier, Python, PySide6, Qt, and operating system details for bug reports.
