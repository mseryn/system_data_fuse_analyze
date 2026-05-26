# HPC System Data Suite: Fuse and Analyze in One Place

This project wires together preprocessing, analysis, and visualization stages for HPC telemetry datasets. The CLI orchestrator (`src/main.py`) reads dataset-specific YAML templates and runs the requested stages. See the `docs/` directory for detailed module-by-module documentation and configuration references.

## Getting Started

1. Install dependencies (Recommended to use a virtual env):
   ```
   pip install -r requirements.txt
   ```
2. Place raw data files under `data/` (default search path).

## Running the Pipeline

Stages are executed one at a time, feeding outputs forward. All configuration lives in the dataset YAML — edit it directly to change paths, options, or which stages are enabled. Logging defaults to `INFO`.

1. **Preprocessing** – consumes the raw data and writes a processed pickle.
   ```
   python3 src/main.py config/mit.yml --stages preprocessing
   ```
   Supply a `data_file` argument if `paths.input_dir` is not set in the config:
   ```
   python3 src/main.py config/mit.yml february_18.pkl.zst --stages preprocessing
   ```

2. **Analysis** – reads the preprocessed data and writes an analysis artefact.
   ```bash
   python3 src/main.py config/mit.yml --stages analysis
   ```

3. **Visualization** – renders figures from the analysis artefact.
   ```bash
   python3 src/main.py config/mit.yml --stages visualization
   ```

Run all enabled stages in one go:
```bash
python3 src/main.py config/mit.yml
```

Adjust the config file (`config/mit.yml`, `config/polaris.yml`, etc.) to match the dataset you are processing.

### Optional Logging Controls

Use `--log-level` on any command to change verbosity:

```bash
python3 src/main.py preprocessing polaris my_data.pkl.zst --log-level DEBUG
```

## Configuration Layout

Template files live under `config/` and are grouped by stage:

```
config/
  mit.yml
  polaris.yml
```

The CLI reads `dataset:` from the YAML file and uses the `stages` map to configure each stage.

## Error Handling & Diagnostics

- Missing data files or configs raise clear messages that include the stage and dataset, e.g.:
  ```
  Error: [preprocessing:mit] Input data file 'february_18.pkl.zst' not found. Checked: /data/february_18.pkl.zst, ...
  ```
- The preprocessing stage inspects the dataset columns (unless `--no-detect-features` is used) and reports missing features, GPU metric availability, and timestamps.
- Logs show which paths and options were resolved, making it easier to verify configuration behavior.

> **Note:** The current stage runners contain placeholder logic—you will need to plug in the actual preprocessing, analysis, and visualization routines for end-to-end execution.
