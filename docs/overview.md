# Project Overview

The prototype HPC visualization pipeline is organized around three major stages:

1. **Preprocessing** — load raw scheduler / telemetry exports, clean them, derive features, and persist intermediate artifacts.
2. **Analysis** — aggregate the preprocessed data, compute summaries, and prepare downstream inputs for plotting.
3. **Visualization** — render figures and export static or interactive artifacts for reports.


## High-Level Flow

```text
raw data (data/<file>) ──┐
                         ▼
               preprocessing stage
                   - config: config/<dataset>.yml  (stages.preprocessing)
                   - output: data/processed/<dataset>/...
                         ▼
                  analysis stage
                   - config: config/<dataset>.yml  (stages.analysis)
                   - output: data/analysis/<dataset>/...
                         ▼
               visualization stage
                   - config: config/<dataset>.yml  (stages.visualization)
                   - output: figures/<dataset>/<job>/...
```

Each stage consumes the configuration produced by the preceding step, optionally merges CLI overrides, and persists a fresh configuration for the next stage. 

## Key Packages

- `src/main.py` — CLI dispatcher. Parses arguments, performs validation, and defers to the pipeline orchestrator.
- `src/pipeline/` — orchestration helpers:
  - `stages.py` holds the high-level `run_preprocessing`, `run_analysis`, and `run_visualization` functions.
  - `errors.py` defines `StageError` for consistent user-facing messages.
- `src/preprocessing/runner.py` — dataset-aware preprocessing entry point. Handles feature detection, timestamp granularity, and metadata exporting.
- `src/analysis/data_postprocess.py` — legacy analysis module. Offers `intake`, `combine_pickles`, and other utilities used during exploratory data analysis.
- `src/visualization/runner.py` — wrapper around visualization module selection and artefact bookkeeping.

The documentation in this folder explains the responsibilities and interactions of these components in more detail.
