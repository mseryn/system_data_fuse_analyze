from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

from preprocessing.polaris_preprocessor import run_preprocessing as _run_polaris
from preprocessing.supercloud_preprocessor import run_preprocessing as _run_supercloud
from pipeline.errors import StageError


logger = logging.getLogger(__name__)

# Maps dataset name → preprocessing function.
# Each function must accept (config, data_path, project_root) and return a dict
# with at least: processed_file, derived_features, summary, notes.
_PREPROCESSORS = {
    "polaris": _run_polaris,
    "mit": _run_supercloud,
}


def run_preprocessing_stage(
    dataset: str,
    config: Dict[str, Any],
    data_path: Path | None,
    project_root: Path,
    overrides: Dict[str, Any],
) -> Dict[str, Any]:
    dataset_key = dataset.lower()

    if dataset_key not in _PREPROCESSORS:
        raise StageError(
            "preprocessing",
            dataset,
            f"No preprocessor registered for dataset '{dataset_key}'. "
            f"Available: {', '.join(sorted(_PREPROCESSORS))}.",
        )

    # Apply CLI overrides into the config parameters block before handing off.
    parameters = config.setdefault("parameters", {})
    if overrides.get("time_range") is not None:
        parameters["time_range"] = overrides["time_range"]
    if overrides.get("granularity_seconds") is not None:
        parameters["granularity_seconds"] = overrides["granularity_seconds"]
    if overrides.get("input_root") and data_path is not None:
        config.setdefault("paths", {})["input"] = str(
            Path(overrides["input_root"]) / data_path.name
        )

    preprocessor = _PREPROCESSORS[dataset_key]
    logger.info("Running %s preprocessor for dataset '%s'", preprocessor.__module__, dataset_key)

    try:
        result = preprocessor(config, data_path, project_root)
    except FileNotFoundError as exc:
        raise StageError("preprocessing", dataset, str(exc)) from exc
    except StageError:
        raise
    except Exception as exc:
        logger.exception("Preprocessing failed for dataset '%s'", dataset_key)
        raise StageError("preprocessing", dataset, str(exc)) from exc

    if not result.get("processed_file"):
        raise StageError(
            "preprocessing",
            dataset,
            "Preprocessor did not return 'processed_file'.",
        )

    return result
