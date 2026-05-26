# CLI Reference (`src/main.py`)

The CLI orchestrator is the primary entry point for running the pipeline. It reads the dataset name from the config file, validates paths, and emits clear errors when prerequisites are missing. All pipeline behaviour is configured via the YAML config file — the CLI has no override flags.

## Usage

```
python3 src/main.py <config> [data_file] [options]
```

- `<config>` — path to the YAML configuration file (e.g. `config/polaris.yml`). The file must contain a top-level `dataset:` key identifying the dataset.
- `[data_file]` — optional raw data file passed to the preprocessing stage. Only needed when `paths.input_dir` is not set in the config file.

### Examples

```bash
# Run all enabled stages for Polaris
python3 src/main.py config/polaris.yml

# Run only the preprocessing stage (input_dir is in the config)
python3 src/main.py config/polaris.yml --stages preprocessing

# Run preprocessing with an explicit data file (overrides paths.input_dir)
python3 src/main.py config/polaris.yml data/raw_polaris.csv --stages preprocessing

# Run specific stages
python3 src/main.py config/mit.yml --stages analysis visualization
```

## Options

| Option | Description |
| ------ | ----------- |
| `--stages STAGE [STAGE ...]` | Explicitly select which stages to run (`preprocessing`, `analysis`, `visualization`). Overrides the `enabled` flags in the config. Stages always execute in pipeline order regardless of the order listed here. |
| `--log-level LEVEL` | Python logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). Default: `INFO`. |

## Stage enabling

Each stage section in the YAML config has an `enabled` key:

```yaml
stages:
  preprocessing:
    enabled: false
  analysis:
    enabled: true
  visualization:
    enabled: true
```

When `--stages` is not passed, only stages with `enabled: true` are run. When `--stages` is passed, those stages run unconditionally (the `enabled` flags are ignored).

## Error Handling

- Missing configuration files or data artefacts raise a `StageError`, producing user-friendly messages like:
  ```
  Error: [preprocessing:polaris] Input data file 'raw.pkl.zst' not found.
  ```
- Known stage errors exit with code `2`; all other errors exit with code `1`.

## Logging

Use `--log-level DEBUG` for detailed output from stage runners, including resolved paths.

