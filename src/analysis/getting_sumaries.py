import os, sys
from pathlib import Path
import pandas
import numpy as np
from scipy import stats


TOP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

from .data_postprocess import intake, combine_pickles

opacity = 0.2

def join_domains_by_project(df, projects_file):
    mapper = pandas.read_csv(projects_file)
    shortened_mapper = mapper[["PROJECT_NAME", "SCIENCE_FIELD_SHORT"]]
    shortened_mapper = shortened_mapper.rename(columns={"PROJECT_NAME": "project"})
    shortened_mapper = shortened_mapper.rename(columns={"SCIENCE_FIELD_SHORT": "domain"})
    
    joined = df.merge(shortened_mapper, on="project", how="left")
    return joined
    
def drop_outliers(df):
    z = np.abs(stats.zscore(df['total_energy']))
    threshold = 5
    outliers = df[z > threshold]

    df = df.drop(outliers.index)
    return df

analysis_defaults = {
    "force_intake": False,
    "force_combine": False,
    # data_files and combined_sums are not read from the YAML config.
    # They are constructed programmatically by run_analysis_stage (from paths.input
    # and paths.output_dir) before calling run_analysis, or set via sys.argv
    # when running getting_sumaries.py directly.
    "data_files": [],
    "combined_sums": f"{TOP_DIR}/data/_sums.pkl.zst",
}

def run_analysis(config):
    config = analysis_defaults | config

    sum_files = []

    for data_file in config["data_files"]:
        file_parts = data_file.split(".")
        suffixes = -2 if file_parts[-1] in ['gz', 'zst'] else -1
        file_prefix = ".".join(file_parts[:suffixes])
        print('Summary file prefix ' + file_prefix)
        sum_filename = f"{file_prefix}_sums.pkl.zst"
        sum_files.append(sum_filename)

        print("looking for files")
        print(f"data file: {data_file}")

        if config["force_intake"] or not Path(sum_filename).exists():
            print("Running intake:")
            intake([data_file], sum_filename)
            print("Intake done, sum: " + sum_filename)

    if not Path(config["combined_sums"]).exists() or any(config[k] for k in ("force_intake", "force_combine")):
        print("Running combine:")
        combine_pickles(sum_files, config["combined_sums"])
        print("Combine done")

    return config["combined_sums"]


if __name__ == "__main__":
    data_files = sys.argv[1:] if len(sys.argv) > 1 else [f"{TOP_DIR}/data/_sums.pkl.zst"]
    combined_sums = os.getenv('COMBINED_SUMS_FILE', f"{TOP_DIR}/data/supercloud_sums.pkl.zst")
    config = {
        "force_intake": False,
        "force_combine": False,
        "data_files": data_files,
        "combined_sums": combined_sums,
    }
    print('Combined_sums file: ' + config['combined_sums'])
    analysis_output = run_analysis(config)
    from visualization.runner import run_visualization_stage
    vis_config = {
        "paths": {
            "input": analysis_output,
            "output_dir": f"{TOP_DIR}/images/",
        },
    }
    run_visualization_stage("mit", vis_config, Path(TOP_DIR), {})
