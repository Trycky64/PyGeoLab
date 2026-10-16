# PyGeoLab 1.2.0

[Version française](RELEASE_NOTES.fr.md)

PyGeoLab 1.2.0 is a major feature release introducing Euclidean conics, parametric and polar curves, direct analytical equation editing, geometric loci with transient traces, a multi-slider animation timeline, and a virtualized value table panel.

## Highlights

- **Conics**: Ellipses, parabolas, and hyperbolas with full geometric representations, directrix, asymptotes, eccentricity, and analytical property cards;
- **Parametric curves**: $x(t), y(t)$ with safe expression parsing, adaptive sampling, discontinuity handling, and slider dependency integration;
- **Polar curves**: $r(\theta)$ with support for radians and degrees, periodicity handling, and dedicated dialog;
- **Analytical editing**: Real-time formula editing and analytical property inspection with direct clipboard copy;
- **Geometric loci & Traces**: Dynamic loci evaluation using isolated subgraphs, lightweight persistence without storing sample points, and transient canvas traces;
- **Multi-slider Timeline**: Transport bar (Play/Pause/Stop), scrubbing, duration, speed, and looping/ping-pong modes for synchronizing multiple animations;
- **Value tables**: High-performance virtualized table panel for Cartesian, parametric, and polar functions with UTF-8 CSV export and clipboard copying;
- **Snapping, Measurements & Transformations**: Continued support for Euclidean transformations, numerical analysis, dynamic measurements, and SVG/PNG exports.

## Compatibility and platforms

- `.pgl` projects from PyGeoLab 1.0 and 1.1 open without conversion;
- Python 3.12, 3.13, and 3.14 are validated with 85%+ test coverage;
- Portable Windows x64 and Linux x64 executables built with PyInstaller.

## Quick verification

1. Start PyGeoLab.
2. Open `examples/demo.pgl`.
3. Animate the timeline or play multi-sliders with `Space`.
4. Check that ellipses, parametric curves, polar roses, and loci update interactively.
5. Open the Value Table dock and export values to CSV.
6. Try multiple selection and Undo/Redo.
7. Export the scene to PNG and SVG.
8. Save and reopen the project.

## Distribution

The `Release` workflow produces `PyGeoLab-Windows-x64.zip` and `PyGeoLab-Linux-x64.tar.gz`.
