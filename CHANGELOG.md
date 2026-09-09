# Changelog

[Version française](CHANGELOG.fr.md)

All notable changes to PyGeoLab are documented in this file.

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
