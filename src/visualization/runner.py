from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any, Dict

import pandas
import plotly.express as px

from visualization import histograms, cdfs
from helpers.column_mapping import ColumnNames

logger = logging.getLogger(__name__)


def run_visualization_stage(
    dataset: str,
    config: Dict[str, Any],
    project_root: Path,
    overrides: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Run the visualization stage.

    Reads the analysis output from the path specified in the stage config
    (or the ``input`` override).  The file is expected to already contain a
    fully post-processed dataframe (domain labels applied, outliers removed)
    as written by the analysis stage.
    """
    paths = config.get("paths", {})

    input_override = overrides.get("input")
    if input_override:
        candidate = Path(input_override)
        input_path = candidate if candidate.is_absolute() else project_root / candidate
    else:
        input_path = project_root / paths.get("input", "")

    if not input_path.exists():
        raise FileNotFoundError(
            f"Analysis output not found at {input_path}. "
            "Run the analysis stage first."
        )

    logger.info("Reading analysis output from %s", input_path)
    df = pandas.read_pickle(str(input_path))

    output_dir_override = overrides.get("output_dir")
    output_dir = project_root / (
        output_dir_override if output_dir_override
        else paths.get("output_dir", f"figures/{dataset}")
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    images_dir = str(output_dir)

    # Plotly PDF export requires a warm-up render to avoid a known first-write bug.
    _warmup_plotly(images_dir)

    charts_run = []

    chart_sets = overrides.get("modules") or config.get("chart_sets") or config.get("charts", [])

    if not chart_sets or "histograms" in chart_sets:
        logger.info("Running histograms for '%s'", dataset)
        histograms.run_all(df, images_dir)
        charts_run.append("histograms")

    if not chart_sets or "cdfs" in chart_sets:
        logger.info("Running CDFs for '%s'", dataset)
        cdfs.run_all(df, images_dir)
        charts_run.append("cdfs")

    logger.info("Visualization complete for '%s'. Charts: %s", dataset, charts_run)

    return {
        "artifacts": charts_run,
        "output_dir": str(output_dir),
        "summary": {
            "dataset": dataset,
            "charts_run": charts_run,
            "output_dir": str(output_dir),
            "row_count": len(df),
        },
    }


def _warmup_plotly(images_dir: str) -> None:
    """Write and immediately delete a throwaway figure to prime the Plotly PDF renderer."""
    warmup_path = os.path.join(images_dir, "garbage.pdf")
    try:
        fig = px.scatter(x=[1, 2, 3], y=[1, 2, 3])
        fig.write_image(warmup_path)
        time.sleep(2)
    finally:
        try:
            Path(warmup_path).unlink(missing_ok=True)
        except OSError:
            pass


def _print_domain_breakdown(df: pandas.DataFrame) -> None:
    if ColumnNames.DOMAIN not in df.columns:
        return
    for domain in ("Physics", "Biological Sciences"):
        jobs = df[df[ColumnNames.DOMAIN] == domain]
        if not jobs.empty:
            print(f"\n--- {domain} ---")
            print(jobs["project"].value_counts())
