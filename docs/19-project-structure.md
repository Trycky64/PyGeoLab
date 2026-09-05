# 19 — Arborescence cible

```text
PyGeoLab/
├── pyproject.toml
├── README.md
├── LICENSE
├── CHANGELOG.md
├── docs/
├── src/
│   └── pygeolab/
│       ├── __init__.py
│       ├── __main__.py
│       ├── app.py
│       │
│       ├── geometry/
│       │   ├── point.py
│       │   ├── vector.py
│       │   ├── line.py
│       │   ├── segment.py
│       │   ├── circle.py
│       │   ├── polygon.py
│       │   ├── intersections.py
│       │   └── transforms.py
│       │
│       ├── math_engine/
│       │   ├── tokenizer.py
│       │   ├── parser.py
│       │   ├── ast_nodes.py
│       │   ├── evaluator.py
│       │   └── numerical.py
│       │
│       ├── model/
│       │   ├── document.py
│       │   ├── objects.py
│       │   ├── styles.py
│       │   └── variables.py
│       │
│       ├── dependency/
│       │   ├── graph.py
│       │   ├── resolver.py
│       │   └── validation.py
│       │
│       ├── commands/
│       │   ├── base.py
│       │   ├── create.py
│       │   ├── delete.py
│       │   ├── move.py
│       │   └── properties.py
│       │
│       ├── rendering/
│       │   ├── viewport.py
│       │   ├── renderer.py
│       │   ├── grid.py
│       │   ├── hit_test.py
│       │   └── function_sampler.py
│       │
│       ├── interaction/
│       │   ├── controller.py
│       │   ├── selection.py
│       │   └── tools/
│       │
│       ├── persistence/
│       │   ├── serializer.py
│       │   ├── loader.py
│       │   ├── validation.py
│       │   └── migrations/
│       │
│       └── ui/
│           ├── main_window.py
│           ├── geometry_view.py
│           ├── algebra_panel.py
│           ├── properties_panel.py
│           └── dialogs/
│
└── tests/
    ├── unit/
    ├── integration/
    └── ui/
```

Cette arborescence est une cible et pourra évoluer lorsque l'implémentation révélera des besoins concrets.
