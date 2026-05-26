# Preprocessing Runner (`src/preprocessing/runner.py`)


## Function: `run_preprocessing_stage(dataset, config, data_path, project_root, overrides)`

### Arguments

- `dataset` — dataset identifier (`mit`, `polaris`), used for default selection and logging.
- `config` — merged configuration dictionary (YAML + placeholder expansion + CLI overrides).
- `data_path` — fully qualified path to the raw dataset file.
- `project_root` — repository root, used to compute relative output paths.
- `overrides` — dictionary of CLI-derived overrides (`input_root`, `time_range`, `granularity_seconds`, etc.).

### Behaviour

1. **Default Lookup**
   - `DATASET_PREPROCESSING_DEFAULTS` maps dataset identifiers to default features and whether detailed analysis should be enabled downstream
   - `config["parameters"]` is ensured to exist, providing a consistent location for time range and granularity.

2. **Granularity & Time Range Resolution**
   - If CLI overrides are supplied, they overwrite the YAML values (`parameters.time_range`, `parameters.granularity_seconds`).
   - The active values are captured in the `summary` metadata and propagated into the generated analysis configuration.

3. **Output Path Construction**
   - Combines `paths.output_dir` and `paths.output_filename`. The directory is created if missing.
   - Relative paths are converted to project-relative strings before returning.

4. **Feature Detection**
   - Unless `--no-detect-features` is provided, the runner samples the raw data using `pandas.read_pickle`.
   - It determines:
     - `present_features` — features listed in the config that were found in the dataset.
     - `missing_features` — expected features not present (logged as warnings).
     - `gpu_columns` — any column containing `"gpu"`, used to set `has_gpu_metrics`.
   - If detection fails (e.g. file too large or malformed), a warning is given and processing continues

5. **Summary & Return Value**
   - Returns a dictionary with:
     - `processed_file` — relative path to the would-be output artefact (placeholder until real processing is wired up).
     - `derived_features` — final feature list used for detection.
     - `summary` — metadata consumed by `pipeline.stages.run_preprocessing`.
     - `notes` — reminder that the implementation is currently a placeholder.

