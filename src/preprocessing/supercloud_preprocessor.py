import pandas
import numpy
import gzip
import pprint
import datetime
import numba
import sys
import os
import glob
import datetime
import csv
import gzip
import logging
import tzdata
import time
from pathlib import Path
from zoneinfo import ZoneInfo
from utility.join_minutely import resample

logger = logging.getLogger(__name__)

"""
This will intake the Supercloud 2022 data and output a unified dataframe with all the relevant fields we want to use for analysis.

Written by Melanie Cornelius, January 2023
License TBD
"""

def _read_file_dirs(base_folder):
    """Scan base_folder for CPU and GPU trace CSVs, keyed by job ID."""
    files = {}
    cpu_files = glob.glob('cpu/*/*-timeseries.csv', root_dir=base_folder)
    for file in cpu_files:
        job_id = os.path.basename(file).split("-")[0]
        if job_id not in files:
            files[job_id] = {"cpu": [], "gpu": []}
        files[job_id]["cpu"].append(file)
    gpu_files = glob.glob('gpu/*/*.csv', root_dir=base_folder)
    for file in gpu_files:
        job_id = os.path.basename(file).split("-")[0]
        if job_id not in files:
            files[job_id] = {"cpu": [], "gpu": []}
        files[job_id]["gpu"].append(file)
    return files


def _get_files(job_id, files):
    job_id = str(job_id)
    return files.get(job_id)


def std_clean(dataframe):
    '''
    Handle most of the renames here and basic unit/type conversion
    '''
    rename_map={
        'id_job': 'job_id',
        'Node': 'node_id',
        'id_array_task': 'task_id', #Keeping it like this for now
        'id_array_job': 'task_array', #Keeping it like this for now 
        'time_start': 'start_timestamp',
        'time_end': 'end_timestamp',
        'id_user': 'user_id',
        'nodes_alloc' : 'num_nodes', 
        'CPUUtilization': 'cpu_pct_utilization', #This is the aggergate of cpus being used
        'ElapsedTime' : 'cpu_elapsed_time',
        #'EpochTime' : 'timestamp',
        'CPUFrequency' : 'cpu_frequency',
        'CPUTime' : 'cpu_time', #Could be named better 
        'ReadMB': 'cpu_read_kb',
        'WriteMB': 'cpu_write_kb',
        'Step':'cpu_step',
        'RSS' : 'cpu_mem_rss',
        'VMSize' : 'cpu_mem_available',
        'Pages' : 'cpu_pages',
        'partition': 'queue_name'
    }
    #rename
    dataframe = dataframe.rename(columns=rename_map)
    #LowerCase
    dataframe.columns = dataframe.columns.str.lower()
    #Data not present
    dataframe["project_id"] = numpy.nan
    dataframe["domain"] = numpy.nan
    dataframe["subdomain"] = numpy.nan
    #Convert to datetime Object 
    dataframe["start_timestamp"] = pandas.to_datetime(dataframe["start_timestamp"], unit = 's' , origin ='unix')
    dataframe["end_timestamp"] = pandas.to_datetime(dataframe["end_timestamp"], unit = 's' , origin ='unix')
    #Convert to KB 
    dataframe["cpu_read_kb"] = dataframe["cpu_read_kb"] * 1024
    dataframe["cpu_write_kb"] = dataframe["cpu_write_kb"] * 1024
    #RSS And VMSize are reported in KB. SO, no need to convert.

    #Map CPU UTILLIZATION to 0-1 NOTE IT DOES GO WAYYY OVER 100 - Need to adjust this 
    dataframe["cpu_pct_utilization"] = (dataframe["cpu_pct_utilization"]/dataframe["cpus_req"])

    return dataframe


def clean_dataframe(dataframe):
    #lowercase columns
    dataframe.columns = dataframe.columns.str.lower()
    return dataframe


def derive_metadata(dataframe):
    '''
    Fills out cols for derived metadata fields
    '''
    #Runtime as end - start in seconds
    dataframe["runtime"] = (dataframe["end_timestamp"]-dataframe["start_timestamp"]).dt.total_seconds() #seconds 
    #Node hours = num nodes * runtime in hours
    dataframe["node_hours"] = dataframe["num_nodes"] * dataframe["runtime"]/3600.0
    #gpu hours = num nodes * runtime  * num_gpus in hours [num_gpus can only take values 0,1,2] 
    dataframe["gpu_hours"] = dataframe["num_nodes"] * dataframe["runtime"] * dataframe["num_gpus"]/3600.0
    #Energy - THink about this one implement later 
    dataframe["energy"] = numpy.nan
    #empty list since we're not using it right no
    dataframe["runtime_arr"] = numpy.nan
    #Num of GPUs alloc
    dataframe["num_alloc_gpus"] = (dataframe[dataframe["tres_alloc"].str.contains("1001=") | dataframe["tres_alloc"].str.contains("1002=")]["tres_alloc"]
                                            .str.split(",").str[-1]
                                            .str.split("=").str[-1].astype(float)) #Test this so it does not catch any other tres alloc col
    dataframe["num_alloc_gpus"] = dataframe["num_alloc_gpus"].fillna(0)
    #To tell if gpu is tesla or volta
    choices = ["tesla" , "volta"]
    conditions = [dataframe["tres_alloc"].str.contains("1001="),
                  dataframe["tres_alloc"].str.contains("1002=")]
    dataframe["gpu_type"] = numpy.select(conditions, choices, default=None)
    return dataframe


def gpu_util_mean(group):
    gpu_cols = [col for col in group.columns if col.startswith('gpu_') and col.endswith('_pct_utilization') and "mem" not in col]
    valid_gpu_cols = [col for col in gpu_cols if not group[col].isna().all()]
    print(valid_gpu_cols)
    #Average across the rows first and then down the column
    return group[valid_gpu_cols].mean(axis=1).mean() if valid_gpu_cols else numpy.nan


def gpu_mem_util_mean(group):
    gpu_cols = [col for col in group.columns if col.startswith('gpu_') and col.endswith('_mem_pct_utilization')]
    valid_gpu_cols = [col for col in gpu_cols if not group[col].isna().all()]
    #Average across the rows first and then down the column
    return group[valid_gpu_cols].mean(axis=1).mean() if valid_gpu_cols else numpy.nan


def gpu_mem_alloc_total(group):
    gpu_cols = [col for col in group.columns if col.startswith('gpu_') and col.endswith('_mem_allocation')]
    valid_gpu_cols = [col for col in gpu_cols if not group[col].isna().all()]
    #Pick out the max gpu memory that got allocated for each gpu and sum them
    return group[valid_gpu_cols].max(axis=0).sum() if valid_gpu_cols else numpy.nan
def gpu_power_total(group):
    gpu_cols = [col for col in group.columns if col.startswith('gpu_') and col.endswith('_power')]
    valid_gpu_cols = [col for col in gpu_cols if not group[col].isna().all()]
    #Average power draw for each gpu first and then sum it for total power used
    return group[valid_gpu_cols].mean(axis=0).sum() if valid_gpu_cols else numpy.nan


def gpu_temperature_mean(group):
    gpu_cols = [col for col in group.columns if col.startswith('gpu_') and col.endswith('_temperature')]
    valid_gpu_cols = [col for col in gpu_cols if not group[col].isna().all()]
    #Average power draw for each gpu first and then sum it for total power used
    return group[valid_gpu_cols].mean(axis=1).sum() if valid_gpu_cols else numpy.nan


def derive_metrics(dataframe):
    #Memory Utilization - avg rss/vmsize
    dataframe["mem_pct_utilization"] = dataframe["cpu_mem_rss"]/dataframe["cpu_mem_available"]
    #Network Utilization - Unsure if any fields tell this information, keeping them as Nan for now
    dataframe["net_pct_utilization"] = numpy.nan
    dataframe["net_0_pct_utilization"] = numpy.nan
    dataframe["net_1_pct_utilization"] = numpy.nan

    #cpu_pct_utilization - Average of cpu_0_pct_utilization for that job on that node, i.e, all rows with same job_id and node_id will have same value of cpu_pct_utilization
    #dataframe["cpu_pct_utilization"] = dataframe.groupby(['job_id', 'node_id'])['cpu_0_pct_utilization'].transform('mean')
    #mem_allocation - Using the tres_alloc string and getting out the value for the key "2"
    #dataframe["mem_allocation"] = dataframe["tres_alloc"].str.split(",").str[1].str.split("=").str[-1].astype(float)* 1024 # unverified but most likely gets reported in MB 
    dataframe["mem_allocation"] = numpy.nan
    # gpu_pct_utilization - Average of gpu_{}_pct_utilization across all gpus for that job on that node, i.e, all rows with same job_id and node_id will have same value of gpu_pct_utilization
    

    if True:
        '''
        Group by the job_id and node_id
        For each group, identify columns that start with 'gpu_' and end with '_pct_utilization'
        Filter out columns that are entirely NaN within the group
        Calculate the mean across the valid GPU columns for each row in the group
        Then, calculate the mean of these row means to get a single value for the group
        Reset the index to have a clean DataFrame with job_id, node_id, and the calculated gpu_pct_utilization
        The same logic applies to gpu_mem_pct_utilization
        The other group bys just differ in their final aggergating logic - see respective functions
        '''
        gpu_pct_utilization =(
            dataframe.groupby(['job_id', 'node_id'])
            .apply(gpu_util_mean)
            .reset_index(name='gpu_pct_utilization')
        )
        dataframe = dataframe.merge(gpu_pct_utilization, on=['job_id', 'node_id'], how='left') #CHECK THIS
        #gpu_mem_pct_utilization - Average of gpu_{}_mem_pct_utilization across all
        gpu_mem_pct_utilization =(
            dataframe.groupby(['job_id', 'node_id'])
            .apply(gpu_mem_util_mean)
            .reset_index(name='gpu_mem_utilization')
        )
        dataframe = dataframe.merge(gpu_mem_pct_utilization, on=['job_id', 'node_id'], how='left') #CHECK THIS
        #gpu_mem_allocation - Average of gpu
        #gpu_power - Average of power
        gpu_power = (
            dataframe.groupby(['job_id', 'node_id'])
            .apply(gpu_power_total)
            .reset_index(name='gpu_power')
        )
        dataframe = dataframe.merge(gpu_power, on=['job_id', 'node_id'], how='left') #CHECK THIS
        gpu_mem_allocation = (
            dataframe.groupby(['job_id', 'node_id'])
            .apply(gpu_mem_alloc_total)
            .reset_index(name='gpu_mem_allocation')
        )
        dataframe = dataframe.merge(gpu_mem_allocation, on=['job_id', 'node_id'], how='left') #CHECK THIS
        gpu_temperature = (
            dataframe.groupby(['job_id', 'node_id'])
            .apply(gpu_temperature_mean)
            .reset_index(name='gpu_temperature')
        )
        dataframe = dataframe.merge(gpu_temperature, on=['job_id', 'node_id'], how='left') #CHECK THIS
        dataframe['node_power'] = dataframe['gpu_power'] #+ dataframe['cpu_power'] #cpu power not available for now
    else:
        dataframe["gpu_pct_utilization"] = numpy.nan
        dataframe["gpu_mem_pct_utilization"] = numpy.nan
        dataframe["gpu_mem_allocation"] = numpy.nan
        dataframe["gpu_power"] = numpy.nan
        dataframe["node_power"] = numpy.nan
    return dataframe


def std_dtypes(dataframe):
    dataframe["num_nodes"] = dataframe["num_nodes"].astype(float)
    dataframe["num_gpus"] = dataframe["num_gpus"].astype(float)
    dataframe["runtime"] = dataframe["runtime"].astype(int) #should this be int?
    dataframe["num_alloc_gpus"] = dataframe["num_alloc_gpus"].astype(int)

    return dataframe


def read_job(job, base_folder, files):
    job_id = job['id_job']
    print("Starting job: " + str(job_id) + " submit timestamp: " + str(job['time_submit']))
    job_files = _get_files(job_id, files)
    if job_files is None:
        raise ValueError('Unknown job_id: ' + str(job_id))

    pprint.pprint(job_files)

    cpu_data = pandas.read_csv(os.path.join(base_folder, job_files["cpu"][0]))
    cpu_data["timestamp"] = pandas.to_datetime(cpu_data['EpochTime'], unit='s', origin='unix')
    cpu_data = cpu_data.loc[(cpu_data['Step'] != '-4') & (cpu_data['Step'] != '-1')]
    cpu_data = resample(cpu_data, '5min', host_column="Node", timestamp_column="timestamp")
    for col in job.keys():
        cpu_data[col] = job[col]

    gpu_dfs = []
    global_gpu_count = 0 

    for gpu_file in job_files["gpu"]:
        gpu_node_df = None
        gpu_node = os.path.basename(gpu_file).split('.')[0].split('-', 1)[1]
        gpu_id_job = int(os.path.basename(gpu_file).split('.')[0].split('-')[0])
        gpu_data = pandas.read_csv(os.path.join(base_folder, gpu_file))
        gpu_data = gpu_data.resample('5min', on='timestamp')
        gpu_indexes = gpu_data["gpu_index"].unique()
        local_gpu_count = 0
        for index in gpu_indexes:
            print(f'GPU index {index}')
            gpu_idx_df = gpu_data[gpu_data["gpu_index"] == index]
            #Filter out gpus that arent used from count
            if gpu_idx_df["utilization_gpu_pct"].mean() !=0:
                local_gpu_count += 1
            start_timestamp = gpu_idx_df['timestamp'].iloc[0]
            start_time_struct = time.gmtime(start_timestamp)
            start_datetime = datetime.datetime(*start_time_struct[0:7], tzinfo=ZoneInfo('America/New_York'))
            diff = start_datetime.utcoffset().total_seconds()                                              
            gpu_idx_df['timestamp'] = gpu_idx_df['timestamp'] - diff
            gpu_idx_df['timestamp'] = pandas.to_datetime(gpu_idx_df['timestamp'], unit='s', origin='unix')
            gpu_idx_df = gpu_idx_df.resample('1s', on='timestamp').first()
            gpu_idx_df['memory_used_MiB'] = gpu_idx_df['memory_used_MiB'] * 1024 # Need KiB, not MiB
            gpu_idx_df['memory_free_MiB'] = gpu_idx_df['memory_free_MiB'] * 1024 #Need KiB, not MiB
            #gpu_pcts betweeen 0-1
            gpu_idx_df = gpu_idx_df.rename(columns={'utilization_gpu_pct': f'gpu_{index}_pct_utilization', 
                                                    'utilization_memory_pct': f'gpu_{index}_mem_pct_utilization', 
                                                    'memory_used_MiB': f'gpu_{index}_mem_allocation', 
                                                    'memory_free_MiB': f'gpu_{index}_mem_free', 
                                                    'temperature_gpu': f'GPU_{index}_temperature', 
                                                    'temperature_memory': f'GPU_{index}_mem_temperature', 
                                                    'power_draw_W': f'GPU_{index}_power', 
                                                    'pcie_link_width_current': f'GPU_{index}_link_width', #This and the below fields are not available for all gpu traces
                                                    'clocks_current_sm_MHz': f'GPU_{index}_clocks_current_sm',
                                                    'clocks_current_memory_MHz': f'GPU_{index}_clocks_current_memory',
                                                    'clocks_current_video_MHz': f'GPU_{index}_clocks_current_video',
                                                    'power_limit_W': f'GPU_{index}_power_limit'
                                                     })
            gpu_idx_df = gpu_idx_df.drop('gpu_index', axis=1)
            gpu_idx_df['Node'] = gpu_node
            gpu_idx_df['id_job'] = gpu_id_job
            pprint.pprint(gpu_idx_df)
            if gpu_node_df is None:
                gpu_node_df = gpu_idx_df
            else:
                gpu_node_df = gpu_node_df.merge(gpu_idx_df, how='left', on=['timestamp', 'Node', 'id_job'])
        gpu_dfs.append(gpu_node_df)
        #Since we just want max GPUs used on a single node
        global_gpu_count = max(global_gpu_count, local_gpu_count)
    if len(gpu_dfs) > 0:
        gpu_df = pandas.concat(gpu_dfs)
        pprint.pprint(gpu_df.columns)
        #Fixed gpu trace mismatch by using (node,id_job) dual identifier
        cpu_data = cpu_data.merge(gpu_df, how='left', on=['timestamp', 'Node', 'id_job'])
    cpu_data["num_gpus"] = global_gpu_count

    cpu_data = std_clean(cpu_data)   
    cpu_data = derive_metadata(cpu_data)
    cpu_data = derive_metrics(cpu_data)
    cpu_data = std_dtypes(cpu_data)
    '''
    Add func to convert cols to required types
    '''
    pprint.pprint(cpu_data)
    return cpu_data

def run_preprocessing(config, data_path, project_root):
    """
    Preprocess MIT Supercloud job traces.

    Expected config paths:
      paths.slurm_data  - Slurm accounting CSV (defaults to data_path)
      paths.trace_dir   - base folder containing cpu/ and gpu/ trace subdirectories
      paths.output_dir  - destination directory
      paths.output_filename - output filename
    """
    paths = config.get("paths", {})

    slurm_data_file = Path(paths.get("slurm_data", str(data_path)))
    if not slurm_data_file.is_absolute():
        slurm_data_file = project_root / slurm_data_file

    trace_dir = paths.get("trace_dir")
    if trace_dir is None:
        raise ValueError("config paths.trace_dir is required for supercloud preprocessing")
    trace_dir = str(project_root / trace_dir)

    output_dir = project_root / paths.get("output_dir", "data/processed/supercloud")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_filename = paths.get("output_filename", "supercloud_preprocessed.pkl.zst")
    output_path = output_dir / output_filename

    files = _read_file_dirs(trace_dir)
    logger.info("Supercloud preprocessing: %d jobs found in trace directory", len(files))

    job_meta = pandas.read_csv(str(slurm_data_file))

    parameters = config.get("parameters", {})
    time_range = parameters.get("time_range")
    if isinstance(time_range, dict) and "start" in time_range and "end" in time_range:
        job_meta = job_meta[
            (job_meta["time_submit"] > time_range["start"]) &
            (job_meta["time_submit"] < time_range["end"])
        ]
        logger.info("Time range filter applied: %s jobs remain", len(job_meta))

    job_ids = [int(k) for k in files.keys()]
    job_meta = job_meta[job_meta["id_job"].isin(job_ids)]

    job_results = []
    for _, job in job_meta.iterrows():
        try:
            job_results.append(read_job(job, trace_dir, files))
        except Exception as exc:
            logger.warning("Failed to process job %s: %s", job.get("id_job"), exc)

    if not job_results:
        raise RuntimeError("No supercloud jobs were successfully processed.")

    final_results = pandas.concat(job_results, ignore_index=True)
    final_results.to_pickle(str(output_path), compression="zstd")
    logger.info("Supercloud preprocessing complete. Output written to %s", output_path)

    try:
        processed_rel = str(output_path.relative_to(project_root))
    except ValueError:
        processed_rel = str(output_path)

    return {
        "processed_file": processed_rel,
        "derived_features": sorted(final_results.columns.tolist()),
        "summary": {
            "jobs_processed": len(job_results),
            "total_rows": len(final_results),
            "has_gpu_metrics": True,
            "output_file": processed_rel,
        },
        "notes": "",
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Preprocess MIT Supercloud job traces.")
    parser.add_argument("slurm_data", help="Slurm accounting CSV.")
    parser.add_argument("trace_dir", help="Base folder containing cpu/ and gpu/ trace subdirectories.")
    parser.add_argument("--output-dir", default="data/processed/supercloud", help="Output directory.")
    parser.add_argument("--output-filename", default="supercloud_preprocessed.pkl.zst", help="Output filename.")
    parser.add_argument("--start-filter", type=int, default=None, help="Unix timestamp lower bound for time_submit.")
    parser.add_argument("--end-filter", type=int, default=None, help="Unix timestamp upper bound for time_submit.")
    args = parser.parse_args()

    time_range = {}
    if args.start_filter is not None:
        time_range["start"] = args.start_filter
    if args.end_filter is not None:
        time_range["end"] = args.end_filter

    config = {
        "paths": {
            "slurm_data": args.slurm_data,
            "trace_dir": args.trace_dir,
            "output_dir": args.output_dir,
            "output_filename": args.output_filename,
        },
        "parameters": {
            "time_range": time_range or None,
        },
    }
    project_root = Path(args.output_dir).resolve().parents[1]
    result = run_preprocessing(config, Path(args.slurm_data), project_root)
    pprint.pprint(result)
