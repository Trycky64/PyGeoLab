# PyGeoLab 1.1.1

[Version française](RELEASE_NOTES.fr.md)

PyGeoLab 1.1.1 is the polished public distribution of the 1.1 feature set. It adds a complete English interface and English-first public documentation while retaining French throughout. It also removes obsolete planning artifacts from the repository and packages both language documents.

## Highlights

- snapping to the grid, points, projections, and intersections;
- advanced construction tools, transformations, and dynamic measurements;
- rectangle and multiple selection with grouped commands and Undo/Redo;
- searchable, sortable, and editable Algebra and Properties panels;
- adaptive function curves and optional analysis overlays;
- animated sliders and a dedicated numerical analysis panel;
- recent files, autosave, crash recovery, and centralized preferences;
- full-document and selection PNG/SVG exports;
- English and French interface with automatic system language selection;
- documented shortcuts, keyboard navigation, and improved diagnostics.

## Compatibility and platforms

- `.pgl` projects from PyGeoLab 1.0 open without conversion;
- Python 3.12, 3.13, and 3.14 are validated;
- portable Windows x64 and Linux x64 archives are started before publication.

## Quick verification

1. Start PyGeoLab.
2. Open `examples/demo.pgl`.
3. Move A/B/C or animate slider `a`.
4. Check that objects, measurements, and curves update.
5. Try multiple selection and Undo/Redo.
6. Export the selection to PNG and the document to SVG.
7. Save and reopen the project.

## Distribution

The `Release` workflow produces `PyGeoLab-Windows-x64.zip` and `PyGeoLab-Linux-x64.tar.gz`.
