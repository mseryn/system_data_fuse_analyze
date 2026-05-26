from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from preprocessing.runner import run_preprocessing_stage
from analysis.data_postprocess import run_analysis_stage
from visualization.runner import run_visualization_stage
from .errors import StageError


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineContext:
    project_root: Path
    config_dir: Path

    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _ensure_data_file(
    context: PipelineContext,
    data_file: str,
    dataset: str,
    input_root: Optional[str] = None,
) -> Path:
    candidate_paths = []
    if input_root:
        root_path = Path(input_root).expanduser()
        candidate_paths.append(root_path / data_file)
    candidate_paths.append(context.data_dir / data_file)

    for candidate in candidate_paths:
        if candidate.exists():
            return candidate

    search_paths = ", ".join(str(path) for path in candidate_paths)
    raise StageError(
        "preprocessing",
        dataset,
        f"Input data file '{data_file}' not found. Checked: {search_paths}.",
    )


def _load_stage_config(
    context: PipelineContext,
    dataset: str,
    stage: str,
) -> tuple[Dict[str, Any], Path]:
    """Load the stage-specific sub-config from the unified dataset config file."""
    unified_path = context.config_dir / f"{dataset}.yml"
    if not unified_path.exists():
        raise StageError(
            stage,
            dataset,
            f"Configuration file missing at {unified_path}. Ensure a dataset config file exists.",
        )
    unified = _load_yaml(unified_path)
    if not unified:
        raise StageError(stage, dataset, f"Configuration file at {unified_path} is empty.")
    stages = unified.get("stages", {})
    if stage not in stages:
        raise StageError(
            stage,
            dataset,
            f"No '{stage}' section found in {unified_path}.",
        )
    return stages[stage] or {}, unified_path


def is_stage_enabled(
    context: PipelineContext,
    dataset: str,
    stage: str,
) -> bool:
    """Return whether a stage is enabled in the dataset config.

    A stage is enabled if its ``enabled`` key is absent (defaults to True) or
    explicitly set to ``true``.  Setting ``enabled: false`` opts it out of
    unattended / multi-stage runs.
    """
    unified_path = context.config_dir / f"{dataset}.yml"
    if not unified_path.exists():
        return False
    unified = _load_yaml(unified_path)
    stage_cfg = unified.get("stages", {}).get(stage, {}) or {}
    return bool(stage_cfg.get("enabled", True))


def run_preprocessing(
    dataset: str,
    data_file: Optional[str],
    context: PipelineContext,
    overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    raw_config, source_config_path = _load_stage_config(context, dataset, "preprocessing")
    if not raw_config:
        logger.warning(
            "Preprocessing config in %s is empty. Continuing with minimal defaults.", source_config_path
        )

    if data_file is not None:
        data_path = _ensure_data_file(context, data_file, dataset, overrides.get("input_root") if overrides else None)
    else:
        data_path = None
    logger.info("Starting preprocessing for dataset '%s'%s", dataset, f" using {data_path}" if data_path else "")

    try:
        stage_result = run_preprocessing_stage(
            dataset,
            raw_config,
            data_path,
            context.project_root,
            overrides=overrides or {},
        )
    except FileNotFoundError as exc:
        raise StageError("preprocessing", dataset, str(exc)) from exc
    except StageError:
        raise
    except Exception as exc:
        logger.exception("Preprocessing failed for dataset '%s'", dataset)
        raise StageError("preprocessing", dataset, str(exc)) from exc
    processed_file = stage_result.get("processed_file")
    if not processed_file:
        raise StageError(
            "preprocessing",
            dataset,
            "Stage did not return 'processed_file'. Validate preprocessing runner implementation.",
        )

    logger.info("Preprocessing complete for '%s'. Output: %s", dataset, processed_file)

    return {
        "processed_file": processed_file,
        "summary": stage_result.get("summary", {}),
    }


def run_analysis(
    dataset: str,
    context: PipelineContext,
    overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    raw_config, unified_config_path = _load_stage_config(context, dataset, "analysis")

    logger.info("Starting analysis for dataset '%s' using config %s", dataset, unified_config_path)
    try:
        stage_result = run_analysis_stage(
            dataset,
            raw_config,
            context.project_root,
            overrides=overrides or {},
        )
    except FileNotFoundError as exc:
        raise StageError("analysis", dataset, str(exc)) from exc
    except StageError:
        raise
    except Exception as exc:
        logger.exception("Analysis failed for dataset '%s'", dataset)
        raise StageError("analysis", dataset, str(exc)) from exc
    analysis_file = stage_result.get("analysis_file")
    if not analysis_file:
        raise StageError(
            "analysis",
            dataset,
            "Stage did not provide 'analysis_file'. Ensure analysis runner returns expected keys.",
        )

    logger.info("Analysis complete for '%s'. Output: %s", dataset, analysis_file)

    return {
        "analysis_file": analysis_file,
        "summary": stage_result.get("summary", {}),
    }


def run_visualization(
    dataset: str,
    context: PipelineContext,
    overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    raw_config, unified_config_path = _load_stage_config(context, dataset, "visualization")

    logger.info("Starting visualization for dataset '%s' using config %s", dataset, unified_config_path)
    try:
        stage_result = run_visualization_stage(
            dataset,
            raw_config,
            context.project_root,
            overrides=overrides or {},
        )
    except FileNotFoundError as exc:
        raise StageError("visualization", dataset, str(exc)) from exc
    except StageError:
        raise
    except Exception as exc:
        logger.exception("Visualization failed for dataset '%s'", dataset)
        raise StageError("visualization", dataset, str(exc)) from exc

    return {
        "artifacts": stage_result.get("artifacts", []),
        "summary": stage_result.get("summary", {}),
    }
