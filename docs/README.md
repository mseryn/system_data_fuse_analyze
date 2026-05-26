# Documentation Index

This directory contains in-depth documentation for the prototype HPC visualization pipeline.

- `overview.md` — big-picture architecture and data flow.
- `configuration.md` — YAML schema for preprocessing, analysis, and visualization stages.
- `cli.md` — command reference for `src/main.py`, including override behaviour and logging controls.
- `pipeline.md` — details on the orchestrator utilities (`pipeline` package) and cross-stage error handling.
- `preprocessing.md` — behaviour of the preprocessing runner, feature detection, and override resolution.
- `analysis.md` — notes on the legacy analysis module (`data_postprocess.py`) plus interaction with the new runner.
- `visualization.md` — documentation covering the visualization runner and available plotting modules.
