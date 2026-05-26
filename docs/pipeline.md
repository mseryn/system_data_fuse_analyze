# Pipeline Orchestrator (`src/pipeline`)


## Module Summary

- `pipeline/errors.py` — defines `StageError`, a lightweight wrapper around `RuntimeError` that carries stage and dataset metadata. Raising this error results in clear, contextual messages for CLI users.
- `pipeline/stages.py` — exposes `run_preprocessing`, `run_analysis`, and `run_visualization`. Each function:
  1. Loads the relevant configuration file.
  2. Resolves placeholders with CLI context.
  3. Applies validated overrides provided by the CLI.
  4. Executes the stage runner (`preprocessing.runner`, `analysis.data_postprocess`, `visualization.runner`).
  5. Writes the configuration file for the next stage.
  6. Wraps and logs any errors for consistent user feedback.
- `pipeline/__init__.py` simply re-exports the stage functions for convenient imports (`from pipeline import run_preprocessing`).


### Override Handling

`_context_from_overrides` extracts string/number overrides and merges them into the configuration context before placeholder expansion. Each stage function passes through the full `overrides` dictionary so runners can inspect or adjust behaviour.

### Configuration Persistence

After a successful run:

- `run_preprocessing`, `run_analysis`, and `run_visualization` do not write any files other than their primary output data. The config file is never modified by the pipeline.

All stage input/output paths are resolved from the user-authored `config/<dataset>.yml`. The config file is never written by the pipeline — the user specifies the complete pipeline up front and stages are run independently or in sequence.


## Extending the Pipeline

- To add a new dataset: create a `config/<dataset>.yml` file with a `stages` map containing `preprocessing`, `analysis`, and `visualization` sections. The CLI will automatically detect the dataset as long as the filename matches the requested dataset (lowercase)
- To add a new stage: introduce a new runner module and extend `VALID_STAGES`/`run_<stage>` in `stages.py`. Ensure that configurations are persisted in a predictable location
- To augment metadata between stages: enrich the dictionary returned by a stage runner (e.g. add new fields under `summary`) and update the orchestrator to propagate those values into the next configuration file.
