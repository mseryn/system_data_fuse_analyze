import argparse
import logging
import sys
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:
    print(
        "PyYAML is required to run this script. Install dependencies with `pip install -r requirements.txt`.",
        file=sys.stderr,
    )
    sys.exit(1)

from pipeline.errors import StageError
from pipeline.stages import PipelineContext, is_stage_enabled, run_analysis, run_preprocessing, run_visualization


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VALID_STAGES = {"preprocessing", "analysis", "visualization"}
STAGE_ORDER = ["preprocessing", "analysis", "visualization"]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run pipeline stages for a dataset. "
            "By default all stages with 'enabled: true' in the config file are run. "
            "Use --stages to run specific stages instead."
        ),
    )
    parser.add_argument(
        "config",
        help="Path to the dataset config YAML file (e.g. config/polaris.yml).",
    )
    parser.add_argument(
        "data_file",
        nargs="?",
        default=None,
        help=(
            "Optional raw data file to pass to the preprocessing stage "
            "(e.g. april_2024.tar.gz). Only needed when 'paths.input_dir' "
            "is not set in the config file."
        ),
    )
    parser.add_argument(
        "--stages",
        nargs="+",
        metavar="STAGE",
        help=(
            f"Stages to run ({', '.join(sorted(VALID_STAGES))}). "
            "Overrides 'enabled' in the config file. "
            "Always executed in pipeline order: preprocessing → analysis → visualization."
        ),
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (DEBUG, INFO, WARNING, ERROR). Defaults to INFO.",
    )
    return parser.parse_args(argv)


def _load_dataset_from_config(config_path: Path) -> str:
    with config_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    dataset = data.get("dataset")
    if not dataset:
        raise ValueError(
            f"Config file {config_path} is missing a top-level 'dataset' key."
        )
    return str(dataset).lower()


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
        log_level = getattr(logging, args.log_level.upper(), logging.INFO)
        logging.basicConfig(level=log_level, format="%(levelname)s %(name)s: %(message)s")

        config_path = Path(args.config).expanduser().resolve()
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        dataset = _load_dataset_from_config(config_path)
        context = PipelineContext(project_root=PROJECT_ROOT, config_dir=config_path.parent)

        # Resolve which stages to run, always in pipeline order.
        if args.stages:
            invalid = [s for s in args.stages if s.lower() not in VALID_STAGES]
            if invalid:
                raise ValueError(
                    f"Unknown stage(s): {', '.join(invalid)}. "
                    f"Valid options are: {', '.join(sorted(VALID_STAGES))}."
                )
            stages_to_run = [s for s in STAGE_ORDER if s in {s.lower() for s in args.stages}]
        else:
            # Run all stages where enabled: true in config.
            stages_to_run = [s for s in STAGE_ORDER if is_stage_enabled(context, dataset, s)]
            if not stages_to_run:
                print(
                    "No stages are enabled in the config. "
                    "Set 'enabled: true' under a stage section or pass --stages explicitly.",
                    file=sys.stderr,
                )
                return 1
            logging.info("Running config-enabled stages: %s", ", ".join(stages_to_run))

        for stage in stages_to_run:
            if stage == "preprocessing":
                result = run_preprocessing(dataset, args.data_file, context)
                print(f"Preprocessing complete. Output: {result['processed_file']}")
            elif stage == "analysis":
                result = run_analysis(dataset, context)
                print(f"Analysis complete. Output: {result['analysis_file']}")
            elif stage == "visualization":
                result = run_visualization(dataset, context)
                print("Visualization complete.")
                artifacts = result.get("artifacts", [])
                if artifacts:
                    print("Artifacts:", ", ".join(artifacts))

        return 0
    except StageError as exc:
        logging.exception("%s", exc)
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # pylint: disable=broad-except
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
