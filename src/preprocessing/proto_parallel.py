import pandas
import numpy
import gzip
import shutil
import pprint
import datetime
import numba
import sys

"""
This will prototype the system we will use to intake multifaceted data
about ANL systems.

TODO:
    - Intake all 3 sources of data
        - Unify (each in separate function)
    - Add functionality to say "was this up/downtime"
    - Build simple dash to intake this data


Written by Melanie Cornelius, January 2023
License TBD
"""
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

    all_cols = pandas.read_csv(filename, compression='gzip', nrows=0).columns.tolist()
    wanted_cols = [col for col in all_cols if col not in ['GPU_aggr_dbit_ecc', 'GPU_aggr_dbit_ecc_0', 'GPU_aggr_dbit_ecc_1', 'GPU_aggr_dbit_ecc_2', 'GPU_aggr_dbit_ecc_3', 'GPU_aggr_dbit_ecc_avg', 'GPU_load', 'GPU_load_avg', 'GPU_mem_alloc', 'GPU_mem_alloc_0', 'GPU_mem_alloc_1', 'GPU_mem_alloc_2', 'GPU_mem_alloc_3', 'GPU_mem_alloc_avg', 'GPU_mem_util','GPU_mem_util_avg', 'GPU_power_usage', 'GPU_power_usage_avg', 'GPU_temp', 'GPU_temp_avg', 'cm_monitoring_state', 'kernel_version', 'uptime']]
    df = pandas.read_csv(filename, engine="pyarrow", dtype=coldtypes, dtype_backend="pyarrow", usecols=wanted_cols)
    return df

def process_data(file_name, vhost_cache, vhost_name_lookup_reverse):
    """
    """
    uncompressed_name = file_name.split(".gz")[0]

    file_name_prefix = uncompressed_name.split(".csv")[0]

    pandas.set_option('display.max_colwidth', None)

    start = datetime.datetime.now()
    gpu_data = intake_gpu_data(file_name)
    runtime = datetime.datetime.now() - start
    print('Intake time: ' + str(runtime))

    #
    #
    # Un-comment below to make the dataset smaller
    # gpu_data = gpu_data.head(5000)
    #
    #

    gpu_data["timestamp"] = pandas.to_datetime(gpu_data["timestamp"])
    
    pprint.pprint(gpu_data)
    pprint.pprint(gpu_data.columns)


    def find_jobid(x):
        TIMESTAMP=1
        HOST=0

        for y in vhost_cache:
            if y[0] == x[HOST] and y[1] < x[TIMESTAMP] and y[2] > x[TIMESTAMP]:
                return y[3]
        return 0

    print('Prepping host number')
    gpu_data['host_number'] = gpu_data['host'].map(vhost_name_lookup_reverse)
    print('Prepping timestamp')
    gpu_data['timestamp_raw'] = gpu_data['timestamp'].to_numpy().astype('int64')
    print('Running apply')
    node_data = gpu_data[['host_number', 'timestamp_raw']].apply(find_jobid, args=(), axis=1, raw=True, engine='numba',engine_kwargs={ 'nopython': True, 'nogil': True, 'parallel': True })
    gpu_data["job_identifier"] = node_data

    print(gpu_data)

    gpu_data.to_pickle("{}.pkl".format(file_name_prefix))

def preprocess_polaris_data(vnode_file, *gpu_files):
    vnode_data = pandas.read_pickle(vnode_file)
    vnode_data["start_time"] = pandas.to_datetime(vnode_data["start_time"])
    vnode_data["end_time"] = pandas.to_datetime(vnode_data["end_time"])

    def timestamp_to_numpy(timestamp):
        return timestamp.to_numpy().astype("int64")
    def jobname_to_number(jobname):
        return int(jobname.split('.')[0].split('[')[0])
        
    vhost_cache_df = vnode_data[['vnode_name', 'start_time', 'end_time', 'job_identifier']]
    vhost_name_list = vnode_data['vnode_name'].unique()
    vhost_name_lookup_reverse = dict(zip(vhost_name_list, range(len(vhost_name_list))))
    vhost_cache_df['vnode_number']= vnode_data['vnode_name'].map(vhost_name_lookup_reverse).to_numpy()
    vhost_cache_df['start_time_value'] = vnode_data['start_time'].map(timestamp_to_numpy).to_numpy()
    vhost_cache_df['end_time_value'] = vnode_data['end_time'].map(timestamp_to_numpy).to_numpy()
    vhost_cache_df['job_number'] =  vnode_data['job_identifier'].map(jobname_to_number).to_numpy()
    vhost_cache = vhost_cache_df[['vnode_number', 'start_time_value', 'end_time_value', 'job_number']].to_numpy()

    for file_name in files:
        process_data(file_name, vhost_cache, vhost_name_lookup_reverse)

if __name__ == "__main__":

    """
    files = ["polaris_gpu_metrics_2023-12-01.csv.gz", "polaris_gpu_metrics_2023-12-08.csv.gz",
    "polaris_gpu_metrics_2023-12-16.csv.gz", "polaris_gpu_metrics_2023-12-24.csv.gz", 
    "polaris_gpu_metrics_2023-12-09.csv.gz", "polaris_gpu_metrics_2023-12-17.csv.gz", "polaris_gpu_metrics_2023-12-25.csv.gz",
    "polaris_gpu_metrics_2023-12-02.csv.gz", "polaris_gpu_metrics_2023-12-10.csv.gz", "polaris_gpu_metrics_2023-12-18.csv.gz", 
    "polaris_gpu_metrics_2023-12-26.csv.gz", "polaris_gpu_metrics_2023-12-03.csv.gz", "polaris_gpu_metrics_2023-12-11.csv.gz", 
    "polaris_gpu_metrics_2023-12-19.csv.gz", "polaris_gpu_metrics_2023-12-27.csv.gz", "polaris_gpu_metrics_2023-12-04.csv.gz",
    "polaris_gpu_metrics_2023-12-12.csv.gz", "polaris_gpu_metrics_2023-12-20.csv.gz", "polaris_gpu_metrics_2023-12-28.csv.gz",
    "polaris_gpu_metrics_2023-12-05.csv.gz", "polaris_gpu_metrics_2023-12-13.csv.gz", "polaris_gpu_metrics_2023-12-21.csv.gz",
    "polaris_gpu_metrics_2023-12-29.csv.gz", "polaris_gpu_metrics_2023-12-06.csv.gz", "polaris_gpu_metrics_2023-12-14.csv.gz",
    "polaris_gpu_metrics_2023-12-22.csv.gz", "polaris_gpu_metrics_2023-12-30.csv.gz", "polaris_gpu_metrics_2023-12-07.csv.gz",
    "polaris_gpu_metrics_2023-12-15.csv.gz", "polaris_gpu_metrics_2023-12-23.csv.gz", "polaris_gpu_metrics_2023-12-31.csv.gz"]
    """

    """files = ["polaris_gpu_metrics_2023-12-02.csv.gz"]"""
    files = sys.argv[2:]
    vnode_filename = sys.argv[1]
    
    preprocess_polaris_data(vnode_filename, *files)

