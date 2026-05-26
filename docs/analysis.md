# Analysis Modules

### Constants & Globals

- `TIMESTEP = 10` — assumed sampling interval in seconds, used when integrating time series metrics.
- `TOP_LEVEL_DIR` — absolute path to the repository root, computed to access datasets under `data/`.

### Function: `intake(threshold=2, do_ris=False, verbose_log=True)`

Purpose:
- Loads raw pickled data (currently hard-coded list under `files`).
- Groups records by `job_id` and computes summary statistics across GPU metrics, memory allocations, and resource imbalance metrics.

Notable behaviour:
- Uses a `measurements` dictionary of lambda functions to compute standard aggregations (`mean`, `max`, `stddev`, etc.).
- Renames several GPU columns to maintain consistent naming (e.g. `gpu_pct_utilization` → `gpu_utilization`).
- Builds per-job summaries capturing runtime, node hours, queue, user/project metadata, per-GPU utilization, and derived metrics like `time_to_gpu_use`.
- Optionally integrates `utils.get_RI` when `do_ris=True`, to compute resource imbalance metrics.
- Writes a `*_sums.pkl.zst` file for each processed input.


### Function: `run_analysis_stage(dataset, config, project_root, overrides)`

Purpose:
- Acts as a bridge between the legacy analysis code and the new pipeline orchestrator.
- Consumes the merged configuration, validates paths, and returns metadata for downstream stages.

Behaviour:
- Resolves the analysis input file (honouring CLI overrides).
- Determines output directory and filename (again respecting overrides).
- Logs the key paths and selected options.
- Computes `include_detailed` by checking CLI overrides first, then the configuration, and finally dataset defaults.
- Returns:
  - `analysis_file` — relative path to the (placeholder) analysis artefact.
  - `summary` — includes input path, output path, and detailed-analysis status.
  - `metadata` — passes along derived features and notes stored in the configuration.
  - `recommended_charts` — dataset-specific defaults (e.g. MIT includes GPU-oriented charts).

