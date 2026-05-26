import pandas
import numpy
import gzip
import shutil
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
from pathlib import Path
from helpers.column_mapping import ColumnNames, COLUMN_MAPPINGS
from utility.join_minutely import resample

logger = logging.getLogger(__name__)

GPU_COLDTYPES = {
    'host': 'category',
    'GPU_load_0': numpy.int8,
    'GPU_load_1': numpy.int8,
    'GPU_load_2': numpy.int8,
    'GPU_load_3': numpy.int8,
    'GPU_load_avg': numpy.int8,
    'GPU_mem_util_0': numpy.int8,
    'GPU_mem_util_1': numpy.int8,
    'GPU_mem_util_2': numpy.int8,
    'GPU_mem_util_3': numpy.int8,
    'GPU_mem_util_avg': numpy.int8,
    'GPU_power_usage_0': numpy.int16,
    'GPU_power_usage_1': numpy.int16,
    'GPU_power_usage_2': numpy.int16,
    'GPU_power_usage_3': numpy.int16,
    'GPU_power_usage_avg': numpy.int16,
    'GPU_temp_0': numpy.int8,
    'GPU_temp_1': numpy.int8,
    'GPU_temp_2': numpy.int8,
    'GPU_temp_3': numpy.int8,
    'GPU_temp_avg': numpy.float16,
}

GPU_DROP_COLUMNS = [
    'GPU_load', 'GPU_mem_alloc', 'GPU_mem_util', 'GPU_power_usage', 'GPU_temp',
    'GPU_aggr_dbit_ecc', 'GPU_aggr_dbit_ecc_0', 'GPU_aggr_dbit_ecc_1',
    'GPU_aggr_dbit_ecc_2', 'GPU_aggr_dbit_ecc_3', 'GPU_aggr_dbit_ecc_avg',
    'cm_monitoring_state', 'kernel_version', 'uptime', 'cpuload', 'memory_used',
]

"""
This will prototype the system we will use to intake multifaceted data
about ANL Polaris and related systems.

Written by Melanie Cornelius, January 2023
License TBD
"""
def jobname_to_number(jobname):
    return int(jobname.split('.')[0].split('[')[0])

def timestamp_to_numpy(timestamp):
    return timestamp.to_numpy().astype("int64")

class JobMeta:
    def __init__(self, filename = None, comp_filename = None, filetype = "csv", column_dtypes = None, drop_columns = None, dataframe = None, comp_dataframe = None, start_timestamp='start_time', end_timestamp='end_time', hostname_column='host'):
        self.filename = filename
        self.comp_filename = comp_filename
        self.filetype = filetype
        self.column_dtypes = column_dtypes or {}
        self.drop_columns = drop_columns or []
        self.dataframe = dataframe
        self.comp_dataframe = comp_dataframe
        self.start_timestamp = start_timestamp
        self.end_timestamp = end_timestamp
        self.hostname_column = hostname_column

        if (self.dataframe is None and self.filename is None):
            raise ValueError("Must specify one of filename or dataframe")

        if (self.hostname_column not in self.column_dtypes):
            self.column_dtypes[self.hostname_column]='category'

        if self.dataframe is None or self.comp_dataframe is None:
            self.intake_job_data()

    def intake_job_data(self):
        if (self.filetype == 'csv'):
            if self.dataframe is None:
                headers = pandas.read_csv(self.filename, nrows=0).columns.tolist()
                cols = [header for header in headers if header not in self.drop_columns]
                self.dataframe = pandas.read_csv(self.filename, usecols=cols, dtype=self.column_dtypes, engine='pyarrow', dtype_backend="pyarrow")
                self.dataframe[self.start_timestamp] = pandas.to_datetime(self.dataframe[self.start_timestamp])
                self.dataframe[self.end_timestamp] = pandas.to_datetime(self.dataframe[self.end_timestamp])
            if self.comp_dataframe is None:
                headers = pandas.read_csv(self.comp_filename, nrows=0).columns.tolist()
                cols = [header for header in headers if header not in self.drop_columns]
                comp_dataframe = pandas.read_csv(self.comp_filename, usecols=cols, dtype=self.column_dtypes, engine='pyarrow', dtype_backend="pyarrow")
                self.dataframe = self.dataframe.merge(comp_dataframe, left_on="job_identifier", right_on="pbs_job_identifier")
            pprint.pprint(self.dataframe.columns)
        else:
            raise ValueError("Unrecognized filetype " + self.filetype)

    def make_lookup_cache(self, start_timestamp, end_timestamp):
        vhost_cache_df = self.dataframe.loc[(self.dataframe[self.start_timestamp] < end_timestamp) & (self.dataframe[self.end_timestamp] > start_timestamp)][[self.hostname_column, self.start_timestamp, self.end_timestamp, 'job_identifier', 'queue_name', 'project_name', 'exit_code', 'username']]

        # Add in some calculated metrics
        # Runtime as end - start in seconds
        vhost_cache_df["runtime"] = (vhost_cache_df[self.end_timestamp]-vhost_cache_df[self.start_timestamp]).dt.total_seconds()
        vhost_cache_df["num_nodes"] = vhost_cache_df.groupby(['job_identifier'])[self.hostname_column].transform('count')
        # Node hours = num nodes * runtime in hours
        vhost_cache_df["node_hours"] = (vhost_cache_df["num_nodes"] * vhost_cache_df["runtime"]/3600.0)
        # gpu hours = num nodes * runtime  * num_gpus in hours [num_gpus is hard set at 4 for Polaris
        vhost_cache_df["gpu_hours"] = (vhost_cache_df["num_nodes"] * vhost_cache_df["runtime"] * 4/3600.0)
        # Num of GPUs alloc
        vhost_cache_df["num_alloc_gpus"] = 4

        vhost_name_list = self.dataframe[self.hostname_column].unique()
        vhost_name_lookup_reverse = dict(zip(vhost_name_list, range(len(vhost_name_list))))
        vhost_project_list = self.dataframe['project_name'].unique()
        vhost_project_lookup_reverse = dict(zip(vhost_project_list, range(len(vhost_project_list))))
        vhost_queue_list = self.dataframe['queue_name'].unique()
        vhost_queue_lookup_reverse = dict(zip(vhost_queue_list, range(len(vhost_queue_list))))
        vhost_user_list = self.dataframe['username'].unique()
        vhost_user_lookup_reverse = dict(zip(vhost_user_list, range(len(vhost_user_list))))
        vhost_cache_df['vnode_number']= vhost_cache_df[self.hostname_column].map(vhost_name_lookup_reverse).to_numpy(dtype=numpy.int64)
        vhost_cache_df['project_number']= vhost_cache_df['project_name'].map(vhost_project_lookup_reverse).to_numpy(dtype=numpy.int64)
        vhost_cache_df['queue_number']= vhost_cache_df['queue_name'].map(vhost_queue_lookup_reverse).to_numpy(dtype=numpy.int64)
        vhost_cache_df['user_number']= vhost_cache_df['username'].map(vhost_user_lookup_reverse).to_numpy(dtype=numpy.int64)
        vhost_cache_df['start_time_value'] = vhost_cache_df[self.start_timestamp].map(timestamp_to_numpy).to_numpy()
        vhost_cache_df['end_time_value'] = vhost_cache_df[self.end_timestamp].map(timestamp_to_numpy).to_numpy()
        vhost_cache_df['job_number'] =  vhost_cache_df['job_identifier'].map(jobname_to_number).to_numpy()
        vhost_cache_df['exit_code'] = vhost_cache_df['exit_code'].to_numpy(dtype=numpy.int64)
        vhost_lookup = {
            'name': vhost_name_lookup_reverse,
            'project': vhost_project_lookup_reverse,
            'queue': vhost_queue_lookup_reverse,
            'user': vhost_user_lookup_reverse,
        }

        vhost_cache = []
        for vnode in range(len(vhost_name_list)):
            vhost_cache.append(vhost_cache_df.loc[vhost_cache_df["vnode_number"] == vnode][['start_time_value', 'end_time_value', 'job_number', 'runtime', 'num_nodes', 'node_hours', 'gpu_hours', 'num_alloc_gpus', 'project_number', 'queue_number', 'exit_code', 'user_number']].to_numpy())
        maxlen = max([len(x) for x in vhost_cache])
        print("Max length: " + str(maxlen))
        for vnode in range(len(vhost_name_list)):
            to_pad = maxlen - len(vhost_cache[vnode])
            vhost_cache[vnode] = numpy.pad(vhost_cache[vnode], ((0,to_pad), (0, 0)), 'constant')
        vhost_cache = numpy.asarray(vhost_cache)
        return vhost_cache, vhost_lookup



class JobLabelHelper:

    def __init__(self, filename = None, filetype = "csv", column_dtypes = None, drop_columns = None, dataframe = None, job_metadata = None, timestamp_column='timestamp', hostname_column='host'):
        self.filename = filename
        self.filetype = filetype
        self.filename_prefix = self.filename.split("." + self.filetype)[0]
        self.column_dtypes = column_dtypes or {}
        self.drop_columns = drop_columns or []
        self.dataframe = dataframe
        self.job_metadata = job_metadata
        self.timestamp_column = timestamp_column
        self.hostname_column = hostname_column


        if (self.dataframe is None and self.filename is None):
            raise ValueError("Must specify one of filename or dataframe")

        if (self.hostname_column not in self.column_dtypes):
            self.column_dtypes[self.hostname_column]='category'


    def intake_gpu_data(self):
        if (self.filetype == 'csv'):
            # Read column names from the csv to filter out the drop columns
            headers = pandas.read_csv(self.filename, nrows=0).columns.tolist()
            cols = [header for header in headers if header not in self.drop_columns]
            self.dataframe = pandas.read_csv(self.filename, usecols=cols, dtype=self.column_dtypes, engine='pyarrow', dtype_backend="pyarrow")
            self.dataframe[self.timestamp_column] = pandas.to_datetime(self.dataframe[self.timestamp_column])
            self.dataframe = resample(self.dataframe, '1min', host_column=self.hostname_column, timestamp_column=self.timestamp_column)
            self.dataframe = self.dataframe.reset_index(level=[self.timestamp_column])
        else:
            raise ValueError("Unrecognized filetype " + self.filetype)

    def process_gpu_data(self):
        """
        """

        #if (os.path.isfile('{}.parquet.zst'.format(self.filename_prefix))):
        if (os.path.isfile('{}.pkl.zst'.format(self.filename_prefix))):
            print('Skipping already processed file {}'.format(self.filename))
            return

        if (self.dataframe is None):
            self.intake_gpu_data()

        pprint.pprint(self.dataframe.columns)

        vhost_cache, vhost_lookup = self.job_metadata.make_lookup_cache(self.dataframe["timestamp"].head(1).iloc[0], self.dataframe["timestamp"].tail(1).iloc[0])

        def find_jobid(index):
            def actual_find(x):
                TIMESTAMP=1
                HOST=0

                for job in vhost_cache[x[HOST]]:
                    if job[0] < x[TIMESTAMP] and job[1] > x[TIMESTAMP]:
                        return job[index]
                return 0
            return actual_find

        self.dataframe['host_number'] = self.dataframe['host'].map(vhost_lookup['name']).to_numpy(dtype=int)
        self.dataframe['timestamp_raw'] = self.dataframe['timestamp'].to_numpy().astype('int64')
        self.dataframe["start_timestamp"] = self.dataframe[['host_number', 'timestamp_raw']].apply(find_jobid(0), args=(), axis=1, raw=True, engine='numba',engine_kwargs={ 'nopython': False, 'nogil': True, 'parallel': True })
        self.dataframe["end_timestamp"] = self.dataframe[['host_number', 'timestamp_raw']].apply(find_jobid(1), args=(), axis=1, raw=True, engine='numba',engine_kwargs={ 'nopython': False, 'nogil': True, 'parallel': True })
        self.dataframe["job_identifier"] = self.dataframe[['host_number', 'timestamp_raw']].apply(find_jobid(2), args=(), axis=1, raw=True, engine='numba',engine_kwargs={ 'nopython': False, 'nogil': True, 'parallel': True })
        self.dataframe["runtime"] = self.dataframe[['host_number', 'timestamp_raw']].apply(find_jobid(3), args=(), axis=1, raw=True, engine='numba',engine_kwargs={ 'nopython': False, 'nogil': True, 'parallel': True })
        self.dataframe["num_nodes"] = self.dataframe[['host_number', 'timestamp_raw']].apply(find_jobid(4), args=(), axis=1, raw=True, engine='numba',engine_kwargs={ 'nopython': False, 'nogil': True, 'parallel': True })
        self.dataframe["node_hours"] = self.dataframe[['host_number', 'timestamp_raw']].apply(find_jobid(5), args=(), axis=1, raw=True, engine='numba',engine_kwargs={ 'nopython': False, 'nogil': True, 'parallel': True })
        self.dataframe["gpu_hours"] = self.dataframe[['host_number', 'timestamp_raw']].apply(find_jobid(6), args=(), axis=1, raw=True, engine='numba',engine_kwargs={ 'nopython': False, 'nogil': True, 'parallel': True })
        self.dataframe["num_alloc_gpus"] = 4
        self.dataframe["project_number"] = self.dataframe[['host_number', 'timestamp_raw']].apply(find_jobid(8), args=(), axis=1, raw=True, engine='numba',engine_kwargs={ 'nopython': False, 'nogil': True, 'parallel': True })
        self.dataframe["queue_number"] = self.dataframe[['host_number', 'timestamp_raw']].apply(find_jobid(9), args=(), axis=1, raw=True, engine='numba',engine_kwargs={ 'nopython': False, 'nogil': True, 'parallel': True })
        self.dataframe["exit_code"] = self.dataframe[['host_number', 'timestamp_raw']].apply(find_jobid(10), args=(), axis=1, raw=True, engine='numba',engine_kwargs={ 'nopython': False, 'nogil': True, 'parallel': True })
        self.dataframe["user_number"] = self.dataframe[['host_number', 'timestamp_raw']].apply(find_jobid(11), args=(), axis=1, raw=True, engine='numba',engine_kwargs={ 'nopython': False, 'nogil': True, 'parallel': True })
        self.dataframe["project_id"] = self.dataframe["project_number"].map({v: k for k, v in vhost_lookup['project'].items()})
        self.dataframe["queue_name"] = self.dataframe["queue_number"].map({v: k for k, v in vhost_lookup['queue'].items()})
        self.dataframe["user_id"] = self.dataframe["user_number"].map({v: k for k, v in vhost_lookup['user'].items()})
        self.dataframe["gpu_power"] = self.dataframe[['GPU_power_usage_0', 'GPU_power_usage_1', 'GPU_power_usage_2', 'GPU_power_usage_3']].sum(axis=1)
        self.dataframe["gpu_mem_allocation"] = self.dataframe[['GPU_mem_alloc_0', 'GPU_mem_alloc_1', 'GPU_mem_alloc_2', 'GPU_mem_alloc_3']].sum(axis=1)
        self.dataframe["gpu_mem_pct_allocation"] = self.dataframe["gpu_mem_allocation"] / (40 * 1024 * 1024 * 4.0)
        self.dataframe = self.dataframe[self.dataframe["job_identifier"] != 0]

        return self.dataframe

    def write_result(self):
        if self.dataframe is None:
            return # No result to write
        mapper = { key: str(value) for key, value in COLUMN_MAPPINGS['POLARIS'].items() }
        self.dataframe.rename(columns=mapper, inplace=True)
        self.dataframe.to_pickle("{}.pkl.zst".format(self.filename_prefix), compression='zstd')


def keep_column(column):
    return column not in ['GPU_load', 'GPU_mem_alloc', 'GPU_mem_util','GPU_power_usage', 'GPU_temp', 'GPU_aggr_dbit_ecc', 'GPU_aggr_dbit_ecc_0', 'GPU_aggr_dbit_ecc_1', 'GPU_aggr_dbit_ecc_2', 'GPU_aggr_dbit_ecc_3', 'GPU_aggr_dbit_ecc_avg', 'cm_monitoring_state', 'kernel_version', 'uptime', 'cpuload', 'memory_used']
    
def intake_gpu_data(filename):
    # Returns DF
    # Keep separate for now -- likely functionality will bifurcate

    coldtypes = {
        'host': 'category',
        'GPU_load_0': numpy.int8,
        'GPU_load_1': numpy.int8,
        'GPU_load_2': numpy.int8,
        'GPU_load_3': numpy.int8,
        'GPU_load_avg': numpy.int8,
        'GPU_mem_util_0': numpy.int8,
        'GPU_mem_util_1': numpy.int8,
        'GPU_mem_util_2': numpy.int8,
        'GPU_mem_util_3': numpy.int8,
        'GPU_mem_util_avg': numpy.int8,
        'GPU_power_usage_0': numpy.int16,
        'GPU_power_usage_1': numpy.int16,
        'GPU_power_usage_2': numpy.int16,
        'GPU_power_usage_3': numpy.int16,
        'GPU_power_usage_avg': numpy.int16,
        'GPU_temp_0': numpy.int8,
        'GPU_temp_1': numpy.int8,
        'GPU_temp_2': numpy.int8,
        'GPU_temp_3': numpy.int8,
        'GPU_temp_avg': numpy.float16
    }

    headers = pandas.read_csv(filename, nrows=0).columns.tolist()

    cols = [header for header in headers if keep_column(header)]
    df = pandas.read_csv(filename, usecols=cols, dtype=coldtypes, engine='pyarrow', dtype_backend="pyarrow")
    return df

def intake_vnode_map_data(filename):
    # Returns DF
    # Keep separate for now -- likely functionality will bifurcate
    df = pandas.read_csv(filename, engine='pyarrow', dtype_backend="pyarrow")
    return df

def run_preprocessing(config, data_path, project_root):
    """
    Preprocess a folder of Polaris GPU telemetry CSV.gz files.

    Expected config paths:
      paths.input_dir   - folder containing *.csv.gz GPU telemetry files
      paths.vnode_file  - PBS vnode/accounting CSV (main)
      paths.job_comp_file - PBS accounting companion CSV
      paths.output_dir            - destination directory for the combined pickle
      paths.output_filename       - output filename
    """
    paths = config.get("paths", {})

    input_dir = Path(paths.get("input_dir", str(data_path)))
    if not input_dir.is_absolute():
        input_dir = project_root / input_dir

    vnode_file = project_root / paths["vnode_file"]
    job_comp_file = project_root / paths["job_comp_file"]

    output_dir = project_root / paths.get("output_dir", "data/processed/polaris")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_filename = paths.get("output_filename", "polaris_preprocessed.pkl.zst")
    output_path = output_dir / output_filename

    csv_files = sorted(glob.glob(os.path.join(str(input_dir), "*.csv.gz")))
    if not csv_files:
        raise FileNotFoundError(f"No *.csv.gz files found in {input_dir}")
    logger.info("Polaris preprocessing: %d input files found in %s", len(csv_files), input_dir)

    jobmeta = JobMeta(
        str(vnode_file),
        str(job_comp_file),
        hostname_column="vnode_name",
    )

    results = []
    for file_name in csv_files:
        try:
            logger.info("Processing %s", file_name)
            jlh = JobLabelHelper(
                filename=file_name,
                filetype="csv",
                column_dtypes=GPU_COLDTYPES,
                drop_columns=GPU_DROP_COLUMNS,
                job_metadata=jobmeta,
            )
            jlh.process_gpu_data()
            jlh.write_result()
            results.append(jlh.filename_prefix + ".pkl.zst")
        except Exception as exc:
            logger.warning("Failed to process %s: %s", file_name, exc)


    final_df = pandas.concat((pandas.read_pickle(str(output_dir / f)) for f in results), ignore_index=True)
    mapper = {key: str(value) for key, value in COLUMN_MAPPINGS["POLARIS"].items()}
    final_df.rename(columns=mapper, inplace=True)
    final_df.to_pickle(str(output_path), compression="zstd")
    logger.info("Polaris preprocessing complete. Output written to %s", output_path)

    try:
        processed_rel = str(output_path.relative_to(project_root))
    except ValueError:
        processed_rel = str(output_path)

    return {
        "processed_file": processed_rel,
        "derived_features": sorted(final_df.columns.tolist()),
        "summary": {
            "input_files_processed": len(results),
            "total_rows": len(final_df),
            "has_gpu_metrics": True,
            "output_file": processed_rel,
        },
        "notes": "",
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Preprocess Polaris GPU telemetry CSV.gz files.")
    parser.add_argument("input_dir", help="Folder containing *.csv.gz telemetry files.")
    parser.add_argument("vnode_file", help="PBS vnode/accounting CSV (main).")
    parser.add_argument("job_comp_file", help="PBS accounting companion CSV.")
    parser.add_argument("--output-dir", default="data/processed/polaris", help="Output directory.")
    parser.add_argument("--output-filename", default="polaris_preprocessed.pkl.zst", help="Output filename.")
    args = parser.parse_args()

    config = {
        "paths": {
            "input_dir": args.input_dir,
            "vnode_file": args.vnode_file,
            "job_comp_file": args.job_comp_file,
            "output_dir": args.output_dir,
            "output_filename": args.output_filename,
        }
    }
    project_root = Path(args.output_dir).resolve().parents[1]
    result = run_preprocessing(config, Path(args.input_dir), project_root)
    pprint.pprint(result)
