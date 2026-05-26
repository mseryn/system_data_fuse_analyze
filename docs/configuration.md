# Configuration Schema

All pipeline stages are configured via a single YAML file per dataset stored in the `config/` directory. Each dataset (e.g. `mit`, `polaris`) has one file containing a `stages` map with sections for each pipeline stage.

```
config/
  <dataset>.yml
```

The CLI (`src/main.py`) loads the relevant stages from the configuration fileand runs each stage with the desginated options

## Shared Conventions

- All paths are relative to the project root unless they are absolute.
- Every stage section accepts an **`enabled`** boolean key (default: `true`). Setting `enabled: false` opts a stage out of unattended multi-stage runs. The CLI `--stages` flag always overrides this.

---

## Preprocessing Configuration

### Polaris (`config/polaris.yml`)

```yaml
stages:
  preprocessing:
    paths:
      input_dir: data/raw/polaris/april_2024    # folder of *.csv.gz GPU telemetry files
      vnode_file: data/raw/polaris/vnode.csv      # PBS vnode/accounting CSV (main)
      job_comp_file: data/raw/polaris/job_comp.csv  # PBS accounting companion CSV
      output_dir: data/processed/polaris
      output_filename: april_2024_polaris_preprocessed.pkl.zst
```

**Fields consumed by `polaris_preprocessor.run_preprocessing`:**

| Key | Required | Description |
|-----|----------|-------------|
| `paths.input_dir` | yes | Folder of `*.csv.gz` GPU telemetry files. Defaults to the CLI `data_file` path if omitted. |
| `paths.vnode_file` | yes | PBS vnode/accounting CSV. |
| `paths.job_comp_file` | yes | PBS job composition CSV. |
| `paths.output_dir` | no | Output directory. Default: `data/processed/polaris`. |
| `paths.output_filename` | no | Output filename. Default: `polaris_preprocessed.pkl.zst`. |

> **Note:** A `parameters` block is reserved for future use but currently the Polaris preprocessor takes no parameters.

---

### MIT Supercloud (`config/mit.yml`)

```yaml
stages:
  preprocessing:
    paths:
      slurm_data: data/raw/mit/april_2021.csv   # Slurm accounting CSV
      trace_dir: data/raw/mit/traces              # base folder with cpu/ and gpu/ subdirectories
      output_dir: data/processed/mit
      output_filename: april_2021_mit_preprocessed.pkl
    parameters:
      # time_range: null   # optional: {start: <unix timestamp>, end: <unix timestamp>}
```

**Fields consumed by `supercloud_preprocessor.run_preprocessing`:**

| Key | Required | Description |
|-----|----------|-------------|
| `paths.slurm_data` | no | Slurm accounting CSV. Defaults to the CLI `data_file` path if omitted. |
| `paths.trace_dir` | **yes** | Base folder containing `cpu/` and `gpu/` trace subdirectories. |
| `paths.output_dir` | no | Output directory. Default: `data/processed/supercloud`. |
| `paths.output_filename` | no | Output filename. Default: `supercloud_preprocessed.pkl.zst`. |
| `parameters.time_range` | no | Dict with `start` and `end` Unix timestamps to filter jobs by `time_submit`. Omit or set to `null` to process all jobs. |

---

## Analysis Configuration

```yaml
stages:
  analysis:
    paths:
      input: data/processed/polaris/april_2024_polaris_preprocessed.pkl.zst
      output_dir: data/analysis/polaris
      output_filename: april_2024_polaris_analysis.pkl.zst
    options:
      force_intake: false
      force_combine: false
      join_domains: false
      domains_file: null
```

**Fields consumed by `data_postprocess.run_analysis_stage`:**

| Key | Required | Description |
|-----|----------|-------------|
| `paths.input` | yes | Path to the preprocessed artefact. |
| `paths.output_dir` | no | Output directory. Default: `data/analysis/<dataset>`. |
| `paths.output_filename` | no | Output filename. Default: `<input stem>_<dataset>_analysis.pkl.zst`. |
| `options.force_intake` | no | Passed to `getting_sumaries.run_analysis`. Re-runs per-job aggregation (intake) even if the output already exists. Default: `false`. |
| `options.force_combine` | no | Passed to `getting_sumaries.run_analysis`. Re-runs the combine step even if the output already exists. Default: `false`. |
| `options.join_domains` | no | If `true`, merges a domain/science-field label onto each job row after aggregation. Requires `domains_file`. Handled by `run_analysis_stage`, not `run_analysis`. Default: `false`. |
| `options.domains_file` | no | Path to a CSV with `PROJECT_NAME` and `SCIENCE_FIELD_SHORT` columns. Required when `join_domains` is `true`. |

The analysis stage has two layers:
- **`getting_sumaries.run_analysis`** — runs per-job intake and combine. Only reads `force_intake`, `force_combine`, `data_files`, and `combined_sums` (the last two are derived from `paths` by the stage runner).
- **`data_postprocess.run_analysis_stage`** — reads the config, calls `run_analysis`, then applies domain joining (`join_domains` / `domains_file`) and the outlier filter (`node_hours < 1e6`) itself before saving the final dataframe.

---

## Visualization Configuration

```yaml
stages:
  visualization:
    paths:
      input: data/analysis/polaris/april_2024_polaris_analysis.pkl.zst
      output_dir: figures/polaris/april_2024
    charts:           # or chart_sets — both keys are accepted
      - histograms
      - cdfs
```

**Fields consumed by `visualization.runner.run_visualization_stage`:**

| Key | Required | Description |
|-----|----------|-------------|
| `paths.input` | yes | Path to the analysis artefact written by the analysis stage. |
| `paths.output_dir` | no | Where rendered figures are written. Default: `figures/<dataset>`. |
| `charts` / `chart_sets` | no | List of chart modules to run. Supported values: `histograms`, `cdfs`. If omitted or empty, all available modules run. |

> **Note:** An `export.formats` key appeared in earlier config examples but is **not currently read** by the visualization runner.

---

## Stage Selection

All configuration lives in the YAML file. Edit it directly to change paths, options, or which stages are enabled. The CLI only controls which stages to run:

| Invocation | Behaviour |
|------------|-----------|
| `python src/main.py config/polaris.yml` | Run all stages with `enabled: true` in `config/polaris.yml`, in pipeline order. |
| `python src/main.py config/polaris.yml --stages analysis` | Run only the `analysis` stage. |
| `python src/main.py config/polaris.yml --stages analysis visualization` | Run `analysis` then `visualization`, regardless of `enabled` flags. |
| `python src/main.py config/polaris.yml --stages preprocessing` | Run only preprocessing; provide `data_file` if `paths.input_dir` is not set in the config. |
