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

## Functions, parametric and polar curves

Create a function with **Objects > New function**. Enter its name, independent variable, expression, and optional display domain. Existing numeric sliders referenced by name become dependencies automatically.

Create a parametric curve with **Objects > New parametric curve** by specifying $x(t)$, $y(t)$, the parameter name, and the interval $[t_{min}, t_{max}]$. Create a polar curve with **Objects > New polar curve** specifying $r(\theta)$ and angular units (radians or degrees). Discontinuities and singularities are automatically detected and rendered as disconnected branches.

Select a curve and use **Objects > Edit function** to change it. Expression errors are shown without blocking the document. **View > Functions** controls sampling quality and optional roots, extrema, intersections, and derivative overlays. Sampling adapts to zoom and separates discontinuities to avoid artificial asymptote segments.

## Conics

Create Euclidean conics from the toolbar or the **Objects** menu:
- **Ellipse**: defined by two foci and a point, or center and axes;
- **Parabola**: defined by a focus point and a directrix line;
- **Hyperbola**: defined by two foci and a point or parameter $a$.

The Properties panel displays detailed analytical cards for conics: Cartesian equation, foci coordinates, eccentricity, focal parameter, directrix equation, and asymptotes. Values can be selected and copied directly to the clipboard.

## Geometric loci and traces

Create a locus with **Objects > New locus**, selecting a target point and a driving variable (slider or constrained point on a curve). Loci are sampled dynamically over the driver domain using an isolated dependency subgraph.

Right-click any point to enable **Transient trace**. Moving the point or animating parent sliders leaves an on-screen trajectory that can be cleared with **Clear traces**.

## Multi-slider timeline

The bottom **Timeline** dock synchronizes multiple animated sliders. Use the transport buttons (**Play**, **Pause**, **Stop**), toggle looping or ping-pong mode, adjust duration and target FPS, and scrub dynamically across time. Shortcuts: **Space** toggles playback and **Escape** stops.

## Value table

The **Value table** dock evaluates Cartesian, parametric, or polar functions over regular intervals ($start$, $end$, $step$). It features a virtualized table supporting up to 50,000 rows, keyboard navigation, clipboard copying, and direct UTF-8 CSV export.

## Sliders

Create a slider from the Algebra panel or **Objects > New slider**. Set its value, minimum, maximum, and step. The Sliders panel supports direct entry, reset, keyboard adjustment, play/pause, speed, and ping-pong playback. Animation recomputes only descendants and does not add one Undo command per frame.

## Data, statistics, and modeling

PyGeoLab 1.3 provides a complete toolset for statistical analysis and tabular data workflows:

### Datasets (`DatasetObject`) and Spreadsheet Panel
- **Data Table Panel**: The dockable *Data* panel (tabified at the bottom of the window) provides a virtualized spreadsheet to view and edit observations. Add or delete rows and columns, copy and paste tabular ranges via TSV/CSV clipboard formats, and change the statistical plot mode.
- **CSV Import and Export**: Automatic delimiter sniffing (comma, semicolon, tab, space), UTF-8 encoding support with or without BOM, locale-aware decimal separator handling, and configurable missing value policies (error, skip, or fill).

### Descriptive and Bivariate Statistics
- **Univariate Metrics**: Selecting any dataset in the workspace immediately displays in the *Properties* panel its sample size, sum, mean, median, minimum, maximum, range, population and sample variance, standard deviation, quartiles $Q_1$ and $Q_3$, interquartile range (IQR), and Tukey outlier fences ($1.5 \times \text{IQR}$).
- **Bivariate Metrics**: For $(X, Y)$ paired series, PyGeoLab automatically calculates covariance, Pearson correlation coefficient $r$, coefficient of determination $R^2$, and the slope and intercept of the ordinary least squares (OLS) regression line.

### Statistical Visualizations
Choose from multiple rendering modes in the Data panel or the Properties panel:
- **Scatter plot**: Observation points with configurable disk radius, stroke color, and translucent fill opacity.
- **Regression line**: Overlaid points with the fitted continuous least-squares line clipped to the mathematical viewport.
- **Histogram**: Frequency distribution across regular intervals plotted on the horizontal axis.
- **Box plot**: Five-number summary box $[Q_1, Q_3]$, median line, whiskers connecting to non-outlier extremes, and highlighted outlier points.
- **Bar chart**: Discrete vertical columns proportional to observation values.

### Curve Fitting and Non-linear Regressions
- **Regression Models**: Fit polynomial regressions from degree 1 to 5, exponential curves ($y = a \cdot e^{b \cdot x}$), logarithmic curves ($y = a + b \cdot \ln(x)$), and power curves.
- **Dynamic Functions**: Any fitted regression result can be converted into a `FunctionObject` ready to be plotted or referenced in mathematical expressions safely without `eval()` or `exec()`.

### Geometric Integration and Dependency Graph
- **Dataset Generated from Objects**: Datasets can dynamically depend on a group of canvas points, polygon vertices, locus samples, or timeline sliders.
- **Objects Derived from Datasets**: Geometric points can follow dataset rows or the dataset centroid $(\bar{x}, \bar{y})$, and regression lines update reactively as parent points are dragged on the canvas.

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
