# Visualization Layer


## Runner: `run_visualization_stage`


### Input Parameters

- `dataset` — dataset identifier (`mit`, `polaris`, `bluewater`). Used to select defaults in `DATASET_VISUALIZATION_DEFAULTS`.
- `config` — visualization configuration dictionary (YAML with placeholders resolved and CLI overrides applied).
- `project_root` — repository root, ensures output directories are interpreted consistently.
- `overrides` — dictionary of CLI-specified overrides (input path, output dir, module list).

### Behaviour

1. **Input Resolution** — if `--vis-input` was provided, it is resolved relative to the project root unless already absolute. Otherwise, `config["paths"]["input"]` is used.
2. **Output Directory** — merges overrides and configuration; directories are created eagerly.
3. **Module Selection** — the runner favours `overrides["modules"]`. If not provided, it reads the YAML `chart_sets`. If that list is empty, dataset defaults (e.g. `overview`, `gpu`, `queues`) are used.
4. **Logging** — emits an `INFO` log summarizing dataset, input path, output directory, and selected modules. Missing inputs raise `FileNotFoundError` and are converted to `StageError` by the pipeline.
5. **Return Value** — produces a manifest containing a synthetic artefact list (one entry per module) and a summary dictionary. When visualization code is wired up, the artefact list should reference actual files written to disk.

### Extending the Runner

- Hook actual plotting functions into this stage by importing the desired module(s) and invoking their `run_all`/`plot` functions based on the selected modules.
- Update the artefact list to include the filenames (relative to `project_root`) produced by each plotting routine.

## Visualization Modules Library

The `src/visualization/` directory contains numerous plotting scripts developed during exploratory analysis. Common modules include:

- `filled_area_charts.py` — GPU count and node-hour trends.
- `composite_chart.py` — mixed charts combining queue metrics and utilization.
- `proportion_bar_charts.py` — resource usage breakdowns.
- `correlate.py`, `pearson_heatmap.py` — correlation-based plots.
- `horizontal_bars.py`, `job_decomposition_horizontal_bars.py` — job-specific summaries.
- `imbalance_factor_plots.py`, `stats_by_queue.py`, `resource_use_plots_cleaned_up.py` — specialised analysis by queue or resource class.

Most modules expose a `run_all(df, ...)` or similarly named function that expects either the full dataframe or precomputed aggregates. Before integrating a module with the CLI-driven pipeline, verify:

1. Input signature — does it expect raw or aggregated data? Does it require additional metadata (e.g. unused workloads)?
2. Output behaviour — does it write figures to disk, return Plotly figures, or display inline?
3. Dependencies — ensure required packages are listed in `requirements.txt` and available in the runtime environment.

## Recommended Workflow for Module Integration

1. Use the preprocessing stage to persist a cleaned dataset with the columns the visualization module needs.
2. Implement the analysis stage to compute aggregates and store them in a well-defined artefact (e.g. `data/analysis/<dataset>/<file>.pkl`).
3. Update `run_visualization_stage` to load that artefact, select the requested modules, and invoke them.
4. Record the output filenames in the returned `artifacts` list for traceability.

By documenting module expectations and keeping the runner generic, teams can selectively enable visualizations per dataset while maintaining a coherent CLI experience.
