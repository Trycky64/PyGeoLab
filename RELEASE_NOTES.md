# PyGeoLab 1.3.0

[Version française](RELEASE_NOTES.fr.md)

PyGeoLab 1.3.0 is a major feature release introducing numerical datasets, descriptive and bivariate statistics, five statistical visualization modes, a lightweight spreadsheet editor, non-linear curve fitting models, and reactive integration with the geometric dependency graph.

## Highlights

- **Datasets (`DatasetObject`)**: Immutable tabular domain model with strict numeric validation, 1D and 2D series, and metadata tracking;
- **Descriptive Statistics**: Instant calculation of count, sum, mean, median, min, max, range, sample/population variance, standard deviation, quartiles, IQR, and Tukey outlier detection;
- **Bivariate Statistics**: Covariance, Pearson correlation coefficient, ordinary least squares linear regression, $R^2$, residuals, and point predictions;
- **Statistical Visualizations**: Scatter plots, linear regression lines, histograms, box plots, and bar charts with hit-testing, selection, and SVG/PNG exports;
- **Lightweight Spreadsheet (`DataTablePanel`)**: Dockable table editor with row/column insertion and deletion, keyboard navigation, copy/paste from clipboard (TSV), and read-only protection for dynamically computed datasets;
- **Curve Fitting & Regressions**: High-accuracy polynomial (degree 1 to 5), exponential, logarithmic, and power fits generating valid and safe `FunctionObject` instances without `eval()` or `exec()`;
- **Dependency Graph Integration**: Reactively generate datasets from canvas points, polygon vertices, locus trajectories, timeline sliders, or sampled functions; derive points and regression lines dynamically;
- **Robust CSV I/O**: Multi-line delimiter sniffing, decimal separator auto-detection, UTF-8/BOM support, Unicode paths, and configurable missing value handling (error, skip, fill);
- **Demonstration Project**: Bundled `examples/stats_modeling.pgl` illustrating reactive statistics on moving points and curve fitting.

## Compatibility and platforms

- `.pgl` projects from PyGeoLab 1.0, 1.1, and 1.2 open without conversion;
- Python 3.12, 3.13, and 3.14 are validated with 85%+ test coverage;
- Portable Windows x64 and Linux x64 executables built with PyInstaller.

## Quick verification

1. Start PyGeoLab.
2. Open `examples/stats_modeling.pgl`.
3. Drag point `P1` or `P2` on the canvas: observe that `NuageMobile`, the centroid point `G_moyen`, and the regression line `Droite_OLS` update in real time.
4. Select `NuageMobile` and inspect the univariate and bivariate statistics in the Properties panel.
5. Switch the plot mode to Histogram, Box plot, or Bar chart in the Data panel.
6. Test CSV export and import.
7. Save and reopen the project.

## Distribution

The `Release` workflow produces `PyGeoLab-Windows-x64.zip` and `PyGeoLab-Linux-x64.tar.gz`.
