# 24 — Backlog détaillé

Les identifiants sont conçus pour être utilisés dans les issues et commits.

## PROJECT

- [x] PROJ-001 — Initialiser le repository.
- [x] PROJ-002 — Créer `pyproject.toml`.
- [x] PROJ-003 — Configurer src layout.
- [x] PROJ-004 — Ajouter licence.
- [x] PROJ-005 — Ajouter README racine.
- [x] PROJ-006 — Configurer Ruff.
- [x] PROJ-007 — Configurer type checker.
- [x] PROJ-008 — Configurer pytest.
- [x] PROJ-009 — Ajouter pre-commit.
- [x] PROJ-010 — Ajouter CI.

## APP

- [x] APP-001 — Créer l'entrypoint.
- [x] APP-002 — Créer QApplication.
- [x] APP-003 — Créer MainWindow.
- [x] APP-004 — Créer menu principal.
- [x] APP-005 — Créer toolbar.
- [x] APP-006 — Créer status bar.
- [x] APP-007 — Créer docks.
- [x] APP-008 — Gérer fermeture propre.

## VIEWPORT

- [x] VIEW-001 — Créer Viewport.
- [x] VIEW-002 — Monde vers écran.
- [x] VIEW-003 — Écran vers monde.
- [x] VIEW-004 — Pan.
- [x] VIEW-005 — Zoom.
- [x] VIEW-006 — Zoom sous curseur.
- [x] VIEW-007 — Reset view.
- [x] VIEW-008 — Grille adaptive.
- [x] VIEW-009 — Axes.
- [x] VIEW-010 — Graduations.

## GEOMETRY

- [x] GEO-001 — Point2D.
- [x] GEO-002 — Vector2D.
- [x] GEO-003 — Line2D.
- [x] GEO-004 — Segment2D.
- [x] GEO-005 — Ray2D.
- [x] GEO-006 — Circle2D.
- [x] GEO-007 — Polygon2D.
- [x] GEO-008 — Distance point-point.
- [x] GEO-009 — Distance point-line.
- [x] GEO-010 — Projection.
- [x] GEO-011 — Intersection line-line.
- [x] GEO-012 — Intersection line-circle.
- [x] GEO-013 — Intersection circle-circle.
- [x] GEO-014 — Parallel line.
- [x] GEO-015 — Perpendicular line.
- [x] GEO-016 — Midpoint.
- [x] GEO-017 — Perpendicular bisector.
- [x] GEO-018 — Angle bisector.
- [x] GEO-019 — Polygon area.
- [x] GEO-020 — Polygon perimeter.
- [x] GEO-021 — Reflection.
- [x] GEO-022 — Rotation.
- [x] GEO-023 — Translation.

## MODEL

- [x] MODEL-001 — Base GeoObject.
- [x] MODEL-002 — UUID stable.
- [x] MODEL-003 — Object naming.
- [x] MODEL-004 — Object styles.
- [x] MODEL-005 — Document.
- [x] MODEL-006 — Object registry.
- [x] MODEL-007 — Valid/invalid state.
- [x] MODEL-008 — Visibility.
- [x] MODEL-009 — Locking.
- [x] MODEL-010 — Metadata.

## DEPENDENCY

- [x] DEP-001 — Graph structure.
- [x] DEP-002 — Add dependency.
- [x] DEP-003 — Remove dependency.
- [x] DEP-004 — Cycle detection.
- [x] DEP-005 — Topological ordering.
- [x] DEP-006 — Dirty propagation.
- [x] DEP-007 — Incremental recompute.
- [x] DEP-008 — Invalidity propagation.
- [x] DEP-009 — Cascade deletion.
- [x] DEP-010 — Dependency tests.

## RENDERING

- [x] RENDER-001 — Renderer abstraction.
- [x] RENDER-002 — Draw points.
- [x] RENDER-003 — Draw segments.
- [x] RENDER-004 — Draw lines.
- [x] RENDER-005 — Draw circles.
- [x] RENDER-006 — Draw polygons.
- [x] RENDER-007 — Draw vectors.
- [x] RENDER-008 — Draw labels.
- [x] RENDER-009 — Draw selections.
- [x] RENDER-010 — Clip infinite lines.
- [x] RENDER-011 — Style system.
- [x] RENDER-012 — Rendering cache.

## INTERACTION

- [x] INT-001 — Interaction controller.
- [x] INT-002 — Tool base class.
- [x] INT-003 — Selection tool.
- [x] INT-004 — Point tool.
- [x] INT-005 — Segment tool.
- [x] INT-006 — Line tool.
- [x] INT-007 — Circle tool.
- [x] INT-008 — Polygon tool.
- [x] INT-009 — Midpoint tool.
- [x] INT-010 — Intersection tool.
- [x] INT-011 — Parallel tool.
- [x] INT-012 — Perpendicular tool.
- [x] INT-013 — Hit-testing.
- [x] INT-014 — Drag.
- [x] INT-015 — Preview geometry.
- [x] INT-016 — Escape cancel.
- [x] INT-017 — Multi-selection.
- [ ] INT-018 — Snapping.

## COMMANDS

- [x] CMD-001 — Command interface.
- [x] CMD-002 — History manager.
- [x] CMD-003 — Create command.
- [x] CMD-004 — Delete command.
- [x] CMD-005 — Move command.
- [x] CMD-006 — Rename command.
- [x] CMD-007 — Style command.
- [x] CMD-008 — Visibility command.
- [x] CMD-009 — Undo.
- [x] CMD-010 — Redo.
- [x] CMD-011 — Composite command.
- [x] CMD-012 — Drag coalescing.

## MATH

- [x] MATH-001 — Tokenizer.
- [x] MATH-002 — Parser.
- [x] MATH-003 — AST nodes.
- [x] MATH-004 — Number node.
- [x] MATH-005 — Variable node.
- [x] MATH-006 — Binary operators.
- [x] MATH-007 — Unary operators.
- [x] MATH-008 — Function calls.
- [x] MATH-009 — Constants.
- [x] MATH-010 — Evaluator.
- [x] MATH-011 — Error reporting.
- [x] MATH-012 — Dependency extraction.
- [x] MATH-013 — Function object.
- [x] MATH-014 — Sampling.
- [x] MATH-015 — Discontinuity detection.
- [x] MATH-016 — Numerical derivative.
- [x] MATH-017 — Numerical integration.
- [x] MATH-018 — Root finder.
- [x] MATH-019 — Extrema.
- [x] MATH-020 — Function intersections.

## VARIABLES

- [x] VAR-001 — Numeric variable.
- [x] VAR-002 — Slider model.
- [x] VAR-003 — Slider UI.
- [x] VAR-004 — Min/max.
- [x] VAR-005 — Step.
- [x] VAR-006 — Dependency updates.

## UI

- [x] UI-001 — Algebra panel.
- [x] UI-002 — Properties panel.
- [x] UI-003 — Object tree/list.
- [x] UI-004 — Context menu.
- [x] UI-005 — Rename.
- [x] UI-006 — Visibility toggle.
- [x] UI-007 — Style editor.
- [ ] UI-008 — Coordinates editor.
- [ ] UI-009 — Function input.
- [x] UI-010 — Slider dialog.
- [x] UI-011 — Settings dialog.
- [x] UI-012 — About dialog.
- [x] UI-013 — Theme support.
- [x] UI-014 — Keyboard navigation.

## PERSISTENCE

- [x] SAVE-001 — Define `.pgl` format.
- [x] SAVE-002 — Serializer.
- [x] SAVE-003 — Deserializer.
- [x] SAVE-004 — Schema validation.
- [x] SAVE-005 — Object factories.
- [x] SAVE-006 — Dependency restoration.
- [x] SAVE-007 — Save.
- [x] SAVE-008 — Save As.
- [x] SAVE-009 — Open.
- [x] SAVE-010 — New.
- [x] SAVE-011 — Dirty document flag.
- [x] SAVE-012 — Unsaved changes dialog.
- [x] SAVE-013 — Version migration.
- [ ] SAVE-014 — Recent files.
- [ ] SAVE-015 — Autosave future.

## EXPORT

- [x] EXP-001 — PNG export.
- [x] EXP-002 — Export resolution.
- [x] EXP-003 — Transparent background.
- [x] EXP-004 — SVG export.
- [x] EXP-005 — Vector objects.
- [x] EXP-006 — Function paths.
- [x] EXP-007 — Labels.

## TEST

- [x] TEST-001 — Geometry unit suite.
- [x] TEST-002 — Dependency suite.
- [x] TEST-003 — Math parser suite.
- [x] TEST-004 — Persistence suite.
- [x] TEST-005 — Command suite.
- [x] TEST-006 — Integration constructions.
- [x] TEST-007 — UI smoke tests.
- [x] TEST-008 — Save/load round-trip.
- [x] TEST-009 — Regression fixtures.
- [x] TEST-010 — Performance benchmark set.

## RELEASE

- [x] REL-001 — Windows build.
- [x] REL-002 — Linux build.
- [x] REL-003 — Installer strategy.
- [x] REL-004 — App icon.
- [x] REL-005 — Version metadata.
- [x] REL-006 — Changelog.
- [x] REL-007 — Screenshots.
- [x] REL-008 — Demo project.
- [ ] REL-009 — Portfolio video.
- [x] REL-010 — Release 1.0.
