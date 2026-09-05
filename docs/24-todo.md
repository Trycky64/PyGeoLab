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

- [ ] VIEW-001 — Créer Viewport.
- [ ] VIEW-002 — Monde vers écran.
- [ ] VIEW-003 — Écran vers monde.
- [ ] VIEW-004 — Pan.
- [ ] VIEW-005 — Zoom.
- [ ] VIEW-006 — Zoom sous curseur.
- [ ] VIEW-007 — Reset view.
- [ ] VIEW-008 — Grille adaptive.
- [ ] VIEW-009 — Axes.
- [ ] VIEW-010 — Graduations.

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

- [ ] MODEL-001 — Base GeoObject.
- [ ] MODEL-002 — UUID stable.
- [ ] MODEL-003 — Object naming.
- [ ] MODEL-004 — Object styles.
- [ ] MODEL-005 — Document.
- [ ] MODEL-006 — Object registry.
- [ ] MODEL-007 — Valid/invalid state.
- [ ] MODEL-008 — Visibility.
- [ ] MODEL-009 — Locking.
- [ ] MODEL-010 — Metadata.

## DEPENDENCY

- [ ] DEP-001 — Graph structure.
- [ ] DEP-002 — Add dependency.
- [ ] DEP-003 — Remove dependency.
- [ ] DEP-004 — Cycle detection.
- [ ] DEP-005 — Topological ordering.
- [ ] DEP-006 — Dirty propagation.
- [ ] DEP-007 — Incremental recompute.
- [ ] DEP-008 — Invalidity propagation.
- [ ] DEP-009 — Cascade deletion.
- [ ] DEP-010 — Dependency tests.

## RENDERING

- [ ] RENDER-001 — Renderer abstraction.
- [ ] RENDER-002 — Draw points.
- [ ] RENDER-003 — Draw segments.
- [ ] RENDER-004 — Draw lines.
- [ ] RENDER-005 — Draw circles.
- [ ] RENDER-006 — Draw polygons.
- [ ] RENDER-007 — Draw vectors.
- [ ] RENDER-008 — Draw labels.
- [ ] RENDER-009 — Draw selections.
- [ ] RENDER-010 — Clip infinite lines.
- [ ] RENDER-011 — Style system.
- [ ] RENDER-012 — Rendering cache.

## INTERACTION

- [ ] INT-001 — Interaction controller.
- [ ] INT-002 — Tool base class.
- [ ] INT-003 — Selection tool.
- [ ] INT-004 — Point tool.
- [ ] INT-005 — Segment tool.
- [ ] INT-006 — Line tool.
- [ ] INT-007 — Circle tool.
- [ ] INT-008 — Polygon tool.
- [ ] INT-009 — Midpoint tool.
- [ ] INT-010 — Intersection tool.
- [ ] INT-011 — Parallel tool.
- [ ] INT-012 — Perpendicular tool.
- [ ] INT-013 — Hit-testing.
- [ ] INT-014 — Drag.
- [ ] INT-015 — Preview geometry.
- [ ] INT-016 — Escape cancel.
- [ ] INT-017 — Multi-selection.
- [ ] INT-018 — Snapping.

## COMMANDS

- [ ] CMD-001 — Command interface.
- [ ] CMD-002 — History manager.
- [ ] CMD-003 — Create command.
- [ ] CMD-004 — Delete command.
- [ ] CMD-005 — Move command.
- [ ] CMD-006 — Rename command.
- [ ] CMD-007 — Style command.
- [ ] CMD-008 — Visibility command.
- [ ] CMD-009 — Undo.
- [ ] CMD-010 — Redo.
- [ ] CMD-011 — Composite command.
- [ ] CMD-012 — Drag coalescing.

## MATH

- [ ] MATH-001 — Tokenizer.
- [ ] MATH-002 — Parser.
- [ ] MATH-003 — AST nodes.
- [ ] MATH-004 — Number node.
- [ ] MATH-005 — Variable node.
- [ ] MATH-006 — Binary operators.
- [ ] MATH-007 — Unary operators.
- [ ] MATH-008 — Function calls.
- [ ] MATH-009 — Constants.
- [ ] MATH-010 — Evaluator.
- [ ] MATH-011 — Error reporting.
- [ ] MATH-012 — Dependency extraction.
- [ ] MATH-013 — Function object.
- [ ] MATH-014 — Sampling.
- [ ] MATH-015 — Discontinuity detection.
- [ ] MATH-016 — Numerical derivative.
- [ ] MATH-017 — Numerical integration.
- [ ] MATH-018 — Root finder.
- [ ] MATH-019 — Extrema.
- [ ] MATH-020 — Function intersections.

## VARIABLES

- [ ] VAR-001 — Numeric variable.
- [ ] VAR-002 — Slider model.
- [ ] VAR-003 — Slider UI.
- [ ] VAR-004 — Min/max.
- [ ] VAR-005 — Step.
- [ ] VAR-006 — Dependency updates.

## UI

- [ ] UI-001 — Algebra panel.
- [ ] UI-002 — Properties panel.
- [ ] UI-003 — Object tree/list.
- [ ] UI-004 — Context menu.
- [ ] UI-005 — Rename.
- [ ] UI-006 — Visibility toggle.
- [ ] UI-007 — Style editor.
- [ ] UI-008 — Coordinates editor.
- [ ] UI-009 — Function input.
- [ ] UI-010 — Slider dialog.
- [ ] UI-011 — Settings dialog.
- [ ] UI-012 — About dialog.
- [ ] UI-013 — Theme support.
- [ ] UI-014 — Keyboard navigation.

## PERSISTENCE

- [ ] SAVE-001 — Define `.pgl` format.
- [ ] SAVE-002 — Serializer.
- [ ] SAVE-003 — Deserializer.
- [ ] SAVE-004 — Schema validation.
- [ ] SAVE-005 — Object factories.
- [ ] SAVE-006 — Dependency restoration.
- [ ] SAVE-007 — Save.
- [ ] SAVE-008 — Save As.
- [ ] SAVE-009 — Open.
- [ ] SAVE-010 — New.
- [ ] SAVE-011 — Dirty document flag.
- [ ] SAVE-012 — Unsaved changes dialog.
- [ ] SAVE-013 — Version migration.
- [ ] SAVE-014 — Recent files.
- [ ] SAVE-015 — Autosave future.

## EXPORT

- [ ] EXP-001 — PNG export.
- [ ] EXP-002 — Export resolution.
- [ ] EXP-003 — Transparent background.
- [ ] EXP-004 — SVG export.
- [ ] EXP-005 — Vector objects.
- [ ] EXP-006 — Function paths.
- [ ] EXP-007 — Labels.

## TEST

- [x] TEST-001 — Geometry unit suite.
- [ ] TEST-002 — Dependency suite.
- [ ] TEST-003 — Math parser suite.
- [ ] TEST-004 — Persistence suite.
- [ ] TEST-005 — Command suite.
- [ ] TEST-006 — Integration constructions.
- [x] TEST-007 — UI smoke tests.
- [ ] TEST-008 — Save/load round-trip.
- [ ] TEST-009 — Regression fixtures.
- [ ] TEST-010 — Performance benchmark set.

## RELEASE

- [ ] REL-001 — Windows build.
- [ ] REL-002 — Linux build.
- [ ] REL-003 — Installer strategy.
- [ ] REL-004 — App icon.
- [ ] REL-005 — Version metadata.
- [ ] REL-006 — Changelog.
- [ ] REL-007 — Screenshots.
- [ ] REL-008 — Demo project.
- [ ] REL-009 — Portfolio video.
- [ ] REL-010 — Release 1.0.
