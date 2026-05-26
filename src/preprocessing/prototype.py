import pandas
import numpy
import dash
import gzip
import shutil
import pprint
import datetime

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
def time_comp(time1, time2):
    # Takes two strings for time
    # Returns T/F if they're true or not
    format_str = "%Y-%m-%dT%H:%M:%S"
    dt1 = datetime.datetime.strptime(time1, format_str)
    dt2 = datetime.datetime.strptime(time2, format_str)
    return dt1==dt2

def time_in_range(time, starttime, endtime):
    # Takes a string time
    # Checks if it is between a start and end time range
    # Returns T/F
    format_str = "%Y-%m-%dT%H:%M:%S"
    comparison = datetime.datetime.strptime(time, format_str)
    start = datetime.datetime.strptime(starttime, format_str)
    end = datetime.datetime.strptime(endtime, format_str)
    if ((start <= comparison) & (end >= comparison)):
        return True
    else:
        return False

def separate_vnodes(vnode_data):
    # Returns a dict of host: vnode_data df
    # This is to ease conceptual inexing
    # Test later if this is efficient

    vnodes_to_data = {}
    hosts = list(vnode_data.vnode_name.unique())
    for host in hosts:
        vnodes_to_data[host] = vnode_data[vnode_data.vnode_name == host]

    return vnodes_to_data

def separate_gpu_data(gpu_data):
    # Returns a dict of host: gpu_data df
    # This is to ease conceptual inexing
    # Test later if this is efficient

    host_to_gpu_data = {}
    hosts = list(gpu_data.host.unique())
    for host in hosts:
        host_to_gpu_data[host] = gpu_data[gpu_data.host == host]

    return host_to_gpu_data

def get_jobID(vnode_by_host, host, time):
    #vnode_name
    current_vnode = vnode_by_host[host]
    
def intake_gpu_data(filename):
    # Returns DF
    # Keep separate for now -- likely functionality will bifurcate
    df = pandas.read_csv(filename)
    return df

def intake_job_comp_data(filename):
    # Returns DF
    # Keep separate for now -- likely functionality will bifurcate
    df = pandas.read_csv(filename)
    return df

def intake_vnode_map_data(filename):
    # Returns DF
    # Keep separate for now -- likely functionality will bifurcate
    df = pandas.read_csv(filename)
    return df

def uncompress_gzip(filename):
    # Helper, saves a .csv of a .csv.gz file
    # Note -- user must re-open this file
    # Takes filename (including extensions), returns nothing
    if filename.endswith("csv.gz"):
        with open(filename.split(".gz")[0], 'wb') as f_out:
            with gzip.open(filename, 'rb') as f_in:
                shutil.copyfileobj(f_in, f_out)
    else:
        print("This only works on csv.gz files")

def intake_prototype_toy_data():
    comp_data = intake_job_comp_data("toy-data/polaris_dim_job_comp_2023-12.csv")
    pprint.pprint(comp_data)
    pprint.pprint(comp_data.columns)

    pandas.to_pickle(comp_data, "comp_data.pkl")

    vnode_data = intake_vnode_map_data("toy-data/polaris_job_vnode_map_2023-12.csv")
    pprint.pprint(vnode_data)
    pprint.pprint(vnode_data.columns)

    pandas.to_pickle(vnode_data, "vnode_data.pkl")

    gpu_data = intake_gpu_data("toy-data/polaris_gpu_metrics_2023-12-01.csv")
    pprint.pprint(gpu_data)
    pprint.pprint(gpu_data.columns)

    gpu_data = shrink_gpu_data(gpu_data)
    #pandas.to_pickle(gpu_data, "gpu_data.pkl")

def shrink_gpu_data(data):
    #data = pandas.read_pickle("toy-data/all_gpu_data.pkl")
    data = data.drop(['GPU_aggr_dbit_ecc', 'GPU_aggr_dbit_ecc_0', 'GPU_aggr_dbit_ecc_1', 'GPU_aggr_dbit_ecc_2', 'GPU_aggr_dbit_ecc_3', 'GPU_aggr_dbit_ecc_avg', 'GPU_load', 'GPU_load_avg', 'GPU_mem_alloc', 'GPU_mem_alloc_0', 'GPU_mem_alloc_1', 'GPU_mem_alloc_2', 'GPU_mem_alloc_3', 'GPU_mem_alloc_avg', 'GPU_mem_util','GPU_mem_util_avg', 'GPU_power_usage', 'GPU_power_usage_avg', 'GPU_temp', 'GPU_temp_avg', 'cm_monitoring_state', 'kernel_version', 'uptime'], axis=1)

    return data

def unify_toy_data():
    """
        Idea:
            Store data for each node separately
    """
    file_name = "/home/mseryn/hpc-data-processing/full_data/gpu/polaris_gpu_metrics_2023-12-02.csv.gz"
    file_name_prefix = "polaris_gpu_metrics_2023-12-02"
    uncompress_gzip(file_name)
    data_by_hosts = {}

    pandas.set_option('display.max_colwidth', None) 
    comp_data = pandas.read_pickle("toy-data/comp_data.pkl")
    vnode_data = pandas.read_pickle("toy-data/vnode_data.pkl")

    gpu_data = intake_gpu_data("toy-data/polaris_gpu_metrics_2023-12-01.csv")
    gpu_data = shrink_gpu_data(gpu_data)

    #gpu_data = pandas.read_pickle("toy-data/smaller_gpu.pkl")
    #gpu_data = pandas.read_pickle("toy-data/gpu_data.pkl")

    #gpu_data = gpu_data.head(1000000)
    #smaller_gpu_data.to_pickle("toy-data/smaller_gpu.pkl")

    # Separating manually
    # Check performance of this later
    #vnodes_to_data = separate_vnodes(vnode_data)
    
    # try separating by host for gpu side
    #host_to_gpu_data = separate_gpu_data(gpu_data)

    """
    # for each, we will re-index using the times
    for host, df in host_to_gpu_data.items():
        print("HOST IS {}".format(host))
        df[["Date","Time"]] = df["timestamp"].str.split('T', expand=True)
        df['Datetime'] = pandas.to_datetime(df['Date'] + ' ' + df['Time'])
        df = df.set_index('Datetime')

        df.to_pickle("{}-01.pkl".format(host))
    """
    
    # Next, we will get the sub DF of each host for both GPU data and VNODE data
    # Then, we will put the vnode->job_identifier field into the GPU data DF
    # This will allow us to sort by job!
    #toy_g["job_identifier"] = toy_g.apply(lambda x: toy_v[(toy_v["host"] == x["host"]) & (toy_v["starttime"] < x["datetime"]) & (toy_v["endtime"] > x["datetime"])]["job_    identifier"].values[0], axis=1)

    print(gpu_data)
    gpu_data.to_pickle("{}.pkl".format(file_name_prefix))

    gpu_data["timestamp"] = pandas.to_datetime(gpu_data["timestamp"])
    vnode_data["start_time"] = pandas.to_datetime(vnode_data["start_time"])
    vnode_data["end_time"] = pandas.to_datetime(vnode_data["end_time"])


    
    #hosts_g = set(list(gpu_data["host"].unique()))
    #hosts_v = set(list(vnode_data["vnode_name"].unique()))
    #print(hosts_g.intersection(hosts_v))

    """

    def find_jobid(x):
        jobinfo = vnode_data[(vnode_data["vnode_name"] == x["host"]) & (vnode_data["start_time"] < x["timestamp"]) & (vnode_data["end_time"] > x["timestamp"])]["job_identifier"]
        if (len(jobinfo) > 0):
            return jobinfo.values[0]
        return numpy.nan

    #gpu_data["job_identifier"] = gpu_data.apply(lambda x: vnode_data[(vnode_data["vnode_name"] == x["host"]) & (vnode_data["start_time"] < x["timestamp"]) & (vnode_data["end_time"] > x["timestamp"])]["job_identifier"].values[0], axis=1)
    #gpu_data["job_identifier"] = gpu_data.apply(find_jobid, args=(), axis=1, raw=True, engine='numba', engine_kwargs={ 'parallel': False, 'nopython': True })
    gpu_data["job_identifier"] = gpu_data.apply(find_jobid, args=(), axis=1)

    pandas.to_pickle(gpu_data, "{}.pkl".format(file_name))




    #df = pd.merge(df,df2[['Key_Column','Target_Column']],on='Key_Column', how='left')
    



    # Un-sanitizing the data
    #gpu_data.set_index(
    #pprint.pprint(gpu_data.host)

    # This is the identifier combo to join these
    #pprint.pprint(comp_data.pbs_job_identifier)
    #pprint.pprint(vnode_data.job_identifier)

    # This is the identifier combo to join these -- ALSO include time
    #pprint.pprint(vnode_data.vnode_name)
    #pprint.pprint(gpu_data.host)
    
    #pprint.pprint(comp_data.columns)
    #pprint.pprint(vnode_data.columns)
    #pprint.pprint(gpu_data.columns)

    #with_cpu = gpu_data[gpu_data.cpuload.notna()]
    #without_cpu = gpu_data[gpu_data.cpuload.isna()]

    #with_hosts = list(with_cpu.host.unique())
    #without_hosts = list(without_cpu.host.unique())

    #with_set = set(with_hosts)
    #without_set = set(without_hosts)

    #if (with_set & without_set):
    #    print(with_set & without_set)
    #else:
    #    print("no overlap of hosts")

    """

if __name__ == "__main__":
    #unify_toy_data()
    unify_toy_data()

