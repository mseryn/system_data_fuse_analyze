import logging
import os
import sys
from pathlib import Path
import pandas
import numpy as np
import pprint

from visualization import utils
from helpers.column_mapping import ColumnNames

logger = logging.getLogger(__name__)

# Ensure the analysis module directory is importable when called from the pipeline
_SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

TIMESTEP = 10  # every 10 seconds

#pandas.set_option("compute.use_numba", True)

TOP_LEVEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))


def intake(files, destination, threshold=2, do_ris=True, verbose_log=True):
    def printv(message):
        if verbose_log:
            pprint.pprint(message)

    measurements = {
        "mean": (
            lambda df, column: df[column].mean() if column in df.columns else np.nan
        ),
        "max": (
            lambda df, column: df[column].max() if column in df.columns else np.nan
        ),
        "stddev": (
            lambda df, column: df[column].std() if column in df.columns else np.nan
        ),
        "variance": (
            lambda df, column: df[column].var() if column in df.columns else np.nan
        ),
        "iof": (
            lambda df, column: (
                np.nan
                if column not in df.columns
                else (
                    df[column].var() / df[column].mean()
                    if df[column].mean() != 0
                    else 0
                )
            )
        ),
        "skew": (
            lambda df, column: df[column].skew() if column in df.columns else np.nan
        ),
        "kurtosis": (
            lambda df, column: df[column].kurt() if column in df.columns else np.nan
        ),
        "sum": (
            lambda df, column: (
                np.nan if column not in df.columns else (df[column].sum() * TIMESTEP)
            )
        ),
    }

    for filename in files:
        printv("Intaking {}".format(filename))
        p = pandas.read_pickle(filename)

        cols = list(p["job_id"].unique())
        df_dict = {name: p.loc[p["job_id"] == name] for name in cols}
        printv("Found {} unique jobs".format(len(df_dict)))

        summaries = []

        printv("Before keying into job data")
        for key, df in df_dict.items():
            jobid = key
            print(df.columns)
            node_hours = df[str(ColumnNames.NODE_HOURS)].max()

            pprint.pprint(df.columns)

            if node_hours <= 0:
                printv("Job {} has no node hours".format(jobid))
            if node_hours > 0:

                # Somehow, we need to change this so different steps happen
                # based on whether or not that data is warrented.
                # Ex, everything below is for GPU processing.

                printv("Job {} has {} node hours".format(jobid, node_hours))

                print("NOTE: REMOVE THISA FTER PREPROCESSOR FIXED")
                df.rename(
                    columns={
                        "partition": "queue_name",
                        "gpu_pct_utilization": "gpu_utilization",
                        "gpu_0_pct_utilization": "gpu_0_utilization",
                        "gpu_1_pct_utilization": "gpu_1_utilization",
                        "gpu_mem_pct_utilization": "gpu_mem_utilization",
                        "gpu_0_mem_pct_utilization": "gpu_0_mem_utilization",
                        "gpu_1_mem_pct_utilization": "gpu_1_mem_utilization",
                        #"gpu_pct_mem_allocation": "gpu_mem_pct_allocation",
                    },
                    inplace=True,
                )

                summ = {}
                summ["runtime_seconds"] = df["runtime"].max()
                if summ["runtime_seconds"] <= 10:
                    continue
                summ["jobid"] = jobid
                summ["hosts"] = list(df["node_id"].unique())
                summ["start_timestamp"] = df["timestamp"].min()
                summ["end_timestamp"] = df["timestamp"].max()
                summ["queue_name"] = df["queue_name"].iloc[0]
                summ["exit_code"] = df["exit_code"].iloc[0]
                summ["num_nodes"] = df["num_nodes"].iloc[0]
                summ["node_hours"] = node_hours
                summ["username"] = df["user_id"].iloc[0]
                summ["project"] = df["project_id"].iloc[0]
                summ["available_gpus"] = df["num_alloc_gpus"].max()

                summ["time_to_gpu_use"] = np.nan
                summ["minutes_to_gpu_use"] = np.nan

                num_gpus = 0
                possible_gpus = int(df["num_alloc_gpus"].max())

                def add_or_make(key, val):
                    if key in summ:
                        summ[key] = summ[key] + val
                    else:
                        summ[key] = val

                printv("Starting by-gpu stats")

                local_max_power_var = None

                for x in range(0, possible_gpus):
                    # Getting the FFT values for power

                    # Stats for alloc
                    summ["mean_alloc_{}".format(x)] = measurements["mean"](
                        df, "gpu_{}_mem_allocation".format(x)
                    )
                    summ["max_alloc_{}".format(x)] = measurements["max"](
                        df, "gpu_{}_mem_allocation".format(x)
                    )
                    summ["mean_alloc_pct_{}".format(x)] = measurements["mean"](
                        df, "gpu_{}_mem_pct_allocation".format(x)
                    )
                    summ["max_alloc_pct_{}".format(x)] = measurements["max"](
                        df, "gpu_{}_mem_pct_allocation".format(x)
                    )
                    add_or_make("mean_alloc", summ["mean_alloc_{}".format(x)])
                    add_or_make("max_alloc", summ["max_alloc_{}".format(x)])
                    add_or_make("mean_alloc_pct", summ["mean_alloc_pct_{}".format(x)])
                    add_or_make("max_alloc_pct", summ["max_alloc_pct_{}".format(x)])

                    # Stats for load (compute)
                    summ["mean_load_{}".format(x)] = measurements["mean"](
                        df, "gpu_{}_utilization".format(x)
                    )
                    summ["max_load_{}".format(x)] = measurements["max"](
                        df, "gpu_{}_utilization".format(x)
                    )
                    print("summ['mean_load_{}'] = {}".format(x, summ["mean_load_{}".format(x)]))
                    if summ["mean_load_{}".format(x)] > threshold:
                        num_gpus = num_gpus + 1
                    add_or_make("mean_load", summ["mean_load_{}".format(x)])
                    add_or_make("max_load", summ["max_load_{}".format(x)])

                    # Stats for memory
                    summ["mean_mem_{}".format(x)] = measurements["mean"](
                        df, "gpu_{}_mem_utilization".format(x)
                    )
                    summ["max_mem_{}".format(x)] = measurements["max"](
                        df, "gpu_{}_mem_utilization".format(x)
                    )
                    add_or_make("mean_mem", summ["mean_mem_{}".format(x)])
                    add_or_make("max_mem", summ["max_mem_{}".format(x)])

                    # Stats for power
                    summ["mean_power_{}".format(x)] = measurements["mean"](
                        df, "gpu_{}_power".format(x)
                    )
                    summ["max_power_{}".format(x)] = measurements["max"](
                        df, "gpu_{}_power".format(x)
                    )
                    add_or_make("mean_power", summ["mean_power_{}".format(x)])
                    add_or_make("max_power", summ["max_power_{}".format(x)])

                    summ["sum_power_{}".format(x)] = measurements["sum"](
                        df, "gpu_{}_power".format(x)
                    )
                    add_or_make("sum_power", summ["sum_power_{}".format(x)])

                    summ["var_power_{}".format(x)] = measurements["variance"](
                        df, "gpu_{}_power".format(x)
                    )
                    add_or_make("var_power", summ["var_power_{}".format(x)])
                    # Check if this GPUs var power is the new local max
                    if (
                        local_max_power_var is None
                        or summ["var_power_{}".format(x)] > local_max_power_var
                    ):
                        local_max_power_var = summ["var_power_{}".format(x)]

                    # Stats for temperature
                    summ["mean_temp_{}".format(x)] = measurements["mean"](
                        df, "gpu_{}_temperature".format(x)
                    )
                    summ["max_temp_{}".format(x)] = measurements["max"](
                        df, "gpu_{}_temperature".format(x)
                    )
                    add_or_make("mean_temp", summ["mean_temp_{}".format(x)])
                    add_or_make("max_temp", summ["max_temp_{}".format(x)])

                    if "gpu_{}_utilization".format(x) in df.columns:
                        print("gpu_{}_utilization".format(x))
                        time_to_nonzero_load = df[
                            df["gpu_{}_utilization".format(x)] > 0.02
                        ]["timestamp"].min()
                        summ["time_to_nonzero_gpu_use_{}".format(x)] = np.nan
                        if time_to_nonzero_load is not None and not pandas.isnull(
                            time_to_nonzero_load
                        ):
                            time_to_nonzero_load = pandas.to_datetime(
                                time_to_nonzero_load
                            )
                            print(
                                "time to nonzero load: {} {}".format(
                                    time_to_nonzero_load, type(time_to_nonzero_load)
                                )
                            )
                            print(
                                "start timestamp: {} {}".format(
                                    summ["start_timestamp"],
                                    type(summ["start_timestamp"]),
                                )
                            )
                            summ["time_to_nonzero_gpu_use_{}".format(x)] = (
                                time_to_nonzero_load
                                - pandas.to_datetime(summ["start_timestamp"])
                            )
                            summ["minutes_to_nonzero_gpu_use_{}".format(x)] = (
                                summ["time_to_nonzero_gpu_use_{}".format(x)] / 60
                            )

                            print(summ["time_to_gpu_use"])
                            print(type(summ["time_to_gpu_use"]))
                            if (not isinstance(
                                summ["time_to_nonzero_gpu_use_{}".format(x)], float
                            )) or (
                                summ["time_to_nonzero_gpu_use_{}".format(x)]
                                < summ["time_to_gpu_use"]
                            ):
                                summ["time_to_gpu_use"] = summ[
                                    "time_to_nonzero_gpu_use_{}".format(x)
                                ]
                                summ["minutes_to_gpu_use"] = (
                                    summ["time_to_gpu_use"] / 60
                                )

                printv("Done with by-gpu stats, doing by-node gpu stats")
                # Getting mean of means
                summ["mean_load"] = df["gpu_utilization"].mean()
                summ["mean_mem"] = df["gpu_mem_utilization"].mean()
                summ["mean_power"] = df["gpu_power"].mean()
                summ["mean_temp"] = df["gpu_temperature"].mean()
                summ["mean_alloc"] = df["gpu_mem_allocation"].mean()

                summ["max_load"] = df["gpu_utilization"].max()
                summ["max_mem"] = df["gpu_mem_utilization"].max()
                summ["max_power"] = df["gpu_power"].max()
                summ["max_temp"] = df["gpu_temperature"].max()
                summ["max_alloc"] = df["gpu_mem_allocation"].max()

                # CPU side stats
                if "mem_pct_rss_to_alloc" in df.columns:
                    summ["mean_cpu_alloc_pct"] = df["mem_pct_rss_to_alloc"].mean()
                    summ["max_cpu_alloc_pct"] = df["mem_pct_rss_to_alloc"].max()
                if "mem_pct_utilization" in df.columns:
                    summ["mean_cpu_load_pct"] = df["mem_pct_utilization"].mean()
                    summ["max_cpu_load_pct"] = df["mem_pct_utilization"].max()
                if "mem_pct_rss_to_available" in df.columns:
                    summ["mean_cpu_mem_pct"] = df["mem_pct_rss_to_available"].mean()
                    summ["max_cpu_mem_pct"] = df["mem_pct_rss_to_available"].max()

                printv("Done with by-node stats, doing totals")
                summ["gpu_count"] = num_gpus

                # This is the most-complex part
                if do_ris:
                    printv("Done with totals, doing RIs")
                    resource_imbalances = utils.get_RI(df, summ["hosts"])
                    printv(resource_imbalances)

                    if resource_imbalances:
                        for rikey, value in resource_imbalances.items():
                            summ[rikey] = value
                    printv("Done with RIs")

                # Now getting power edges
                printv("Doing power edges")
                power_edges, mean_duration = utils.calculate_power_edges(
                    df, summ["hosts"], threshold=225
                )
                summ["power_edges"] = power_edges
                summ["mean_duration_between_power_edges"] = mean_duration
                printv("Done with power edges")
                
                # Now doing FFTs for power on each GPU
                printv("Doing FFTs for power")
                fft_freqs, fft_amps = utils.calculate_fft(df, summ["hosts"])
                summ["fft_power_frequencies"] = fft_freqs
                summ["fft_power_amplitudes"] = fft_amps
                printv("Done with FFTs for power")
                summaries.append(summ)

                # Now getting the RSM for power
                printv("Doing RSM for power")
                rsm_power = utils.calculate_RSM(df, summ["hosts"], "gpu_power")
                summ["rsm_power"] = rsm_power
                printv("Done with RSM for power")

        sum_dfs = pandas.DataFrame.from_records(summaries)
        sum_dfs.to_pickle(destination)


def read_pickle(filename):
    print("reading " + filename)
    return pandas.read_pickle(filename)

def combine_pickles(files, destination):
    print("now combining")
    sums_df = pandas.concat((read_pickle(filename) for filename in files))
    sums_df.to_pickle(destination)


DATASET_ANALYSIS_DEFAULTS = {
    "mit": {
        "recommended_charts": ["filled_area_charts", "composite_chart"],
    },
    "polaris": {
        "recommended_charts": [
            "filled_area_charts",
            "composite_chart",
            "proportion_bar_charts",
        ],
    },
}


def run_analysis_stage(
    dataset: str,
    config: dict,
    project_root: Path,
    overrides: dict,
) -> dict:
    from analysis.getting_sumaries import run_analysis as _run_analysis

    dataset_key = dataset.lower()
    defaults = DATASET_ANALYSIS_DEFAULTS.get(dataset_key, {})

    paths = config.get("paths", {})
    options = config.get("options", {})

    input_override = overrides.get("input")
    if input_override:
        candidate = Path(input_override)
        input_path = candidate if candidate.is_absolute() else project_root / candidate
    else:
        input_path = project_root / paths.get("input", "")
    if not input_path.exists():
        raise FileNotFoundError(f"Preprocessed data not found at {input_path}.")

    output_dir_override = overrides.get("output_dir")
    output_dir = project_root / (
        output_dir_override if output_dir_override
        else paths.get("output_dir", f"data/analysis/{dataset_key}")
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    output_filename = overrides.get(
        "output_filename",
        paths.get("output_filename", f"{input_path.stem}_{dataset_key}_analysis.pkl.zst"),
    )
    analysis_path = output_dir / output_filename

    join_domains = options.get("join_domains", False)
    domains_file = options.get("domains_file")
    if domains_file and not Path(domains_file).is_absolute():
        domains_file = str(project_root / domains_file)

    analysis_config = {
        "force_intake": overrides.get("force_intake", options.get("force_intake", False)),
        "force_combine": overrides.get("force_combine", options.get("force_combine", False)),
        "data_files": [str(input_path)],
        "combined_sums": str(analysis_path),
    }

    logger.info("Running analysis for '%s': %s → %s", dataset_key, input_path, analysis_path)
    _run_analysis(analysis_config)

    logger.info("Reading and finalising analysis output for '%s'", dataset_key)
    df = pandas.read_pickle(str(analysis_path))

    if join_domains and domains_file is not None:
        from analysis.getting_sumaries import join_domains_by_project
        df = join_domains_by_project(df, domains_file)

    df = df[df[ColumnNames.NODE_HOURS] < 1e6]

    df.to_pickle(str(analysis_path))

    try:
        analysis_rel_path = str(analysis_path.relative_to(project_root))
    except ValueError:
        analysis_rel_path = str(analysis_path)

    return {
        "analysis_file": analysis_rel_path,
        "summary": {
            "dataset": dataset_key,
            "input_file": str(input_path),
            "analysis_file": analysis_rel_path,
            "row_count": len(df),
        },
        "metadata": {
            "derived_features": config.get("metadata", {}).get("derived_features", []),
            "notes": config.get("metadata", {}).get("notes"),
        },
        "recommended_charts": defaults.get("recommended_charts", []),
    }
