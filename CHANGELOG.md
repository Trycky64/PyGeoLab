# Changelog

[Version française](CHANGELOG.fr.md)

All notable changes to PyGeoLab are documented in this file.

## 1.2.0 — 2026-10-17

### Added

- Euclidean conics: ellipses (foci + point, center + axes), parabolas (focus + directrix), and hyperbolas (foci + point/parameter) with incremental dependency graph integration, bounding boxes, adaptive sampling, and analytical metrics (eccentricity, perimeter, area, focal parameter, directrix, asymptotes);
- Parametric curves $x(t), y(t)$ with safe parsing, slider dependency tracking, adaptive sampling, discontinuity handling, and interactive dialog;
- Polar curves $r(\theta)$ with angular mode selection (radians/degrees), automatic conversions, period wrapping, and custom evaluation;
- Analytical equation editing and live inspection in the Properties and Algebra panels with direct mouse copy;
- Geometric loci (`Locus2D`) with dependency-isolated sampling, lightweight recomputable persistence, and transient canvas traces;
- Global multi-slider animation timeline with playback controls (Play/Pause/Stop), scrubbing, loop/ping-pong modes, duration, and FPS settings;
- Value table panel (`ValueTablePanel`) with virtualized spreadsheet display, keyboard navigation, clipboard copy, and UTF-8 CSV export;
- Backward compatibility verification for v1.0 and v1.1 `.pgl` document archives.

## 1.1.1 — 2026-09-09

### Added

- complete English runtime catalogue with automatic system-language selection;
- persistent System, English, and French language preference;
- English README, user guide, changelog, and release notes with French counterparts;
- public package metadata and normalized cross-platform line endings.

### Changed

- public documentation now uses English as its entry language;
- Windows and Linux archives include English and French release documents.

### Removed

- completed internal checklist, superseded SVG mockups, and portfolio planning notes.

## 1.1.0 — 2026-09-09

### Added

- configurable snapping to the grid, points, projections, and intersections;
- rays, vectors, bisectors, projections, point-on-object, advanced circles, transformations, and dynamic measurements;
- rectangle and multiple selection, grouped editing, duplication, and display ordering;
- search, sorting, grouping, and direct editing in the Algebra and Properties panels;
- function creation and editing with adaptive sampling and optional analysis overlays;
- editable animated sliders with ping-pong playback and history-safe incremental updates;
- bounded numerical analysis for derivatives, integrals, roots, extrema, and intersections;
- recent files, atomic autosave, crash recovery, centralized preferences, and diagnostics;
- full-document and selection PNG/SVG exports and clipboard support;

### Improved

- cached function rendering and performance on large scenes;
- hit testing and selection cycling for overlapping objects;
- discontinuity detection and asymptote handling;
- keyboard navigation, contrast, accessible names, and shortcut help;
- automated stability coverage up to 10,000 objects and explicit Qt resource cleanup.

### Distribution

- Windows and Linux validation on Python 3.12, 3.13, and 3.14;
- PyInstaller executable smoke tests before archive creation;
- Windows and Linux metadata, icons, license, and release documentation in packages;
- verified compatibility with `.pgl` projects created by PyGeoLab 1.0.

## 1.0.0 — 2026-09-05

### Added

- immutable Euclidean geometry engine and incremental dependency graph;
- interactive 2D viewport, construction tools, and Undo/Redo;
- safe mathematical parser, function plotting, sliders, and numerical analysis;
- validated and versioned `.pgl` persistence;
- PNG/SVG export, themes, preferences, logging, and error handling;
- Windows/Linux PyInstaller builds and GitHub release workflow.
