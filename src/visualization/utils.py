import pandas
from scipy.fft import fft, fftfreq
import numpy as np


def fix_job_id(value):
    val = value.split(".")[0]
    print(value)
    print(val)
    if "[" in val:
        val = val.split("[")[0]
    print(val)
    return float(val)


def mean_if_nonzero(data, list_to_sum, skip_zero=False, load=None):
    count = 0
    sum_value = 0
    mean = 0

    # TODO -- this is not right
    # What is the skip zero?
    # Also need to account for load being 0-100 but power not

    if skip_zero:
        for thing in list_to_sum:
            if data[thing] > 0.1:
                sum_value = sum_value + data[thing]
                count = count + 1
    else:
        for thing in list_to_sum:
            sum_value = sum_value + data[thing]
            count = count + 1

    if count == 0:
        return 0
    else:
        mean = sum_value / count
        return mean

        
# FFT -- this is only for power
# Here we will get: 
# Max FFT freqency and corresponding amplitude on each node (since there may be multiple GPUs)
# Then get the max across all nodes for the job
def calculate_fft(df, hosts):
    print("Calculating FFT")

    max_fft_freq = None
    max_fft_amplitude = None
    possible_gpus = int(df["num_alloc_gpus"].max())

    print("Job is on hosts: {}".format(hosts))
    for host in hosts:
        for gpu_index in range(possible_gpus):
            column = "gpu_{}_power".format(gpu_index)
            if column not in df.columns:
                continue

            power_values = df.loc[df["node_id"] == host, column].to_numpy()
            print("Power Values: {}".format(power_values))
            n = len(power_values)
            if n <= 1:
                continue
            freq = np.fft.rfftfreq(n, d=10)  # d is the sample spacing (10s)
            print("FFT frequencies: {}".format(freq))
            for f in freq:
                print("Frequency value: {}".format(f))
                print("Type of frequency values: {}".format(type(f)))
            try:
                fft_values = np.fft.rfft(power_values)
                amplitudes = np.abs(fft_values)
                print("FFT amplitudes for host {}, gpu {}: {}".format(host, gpu_index, amplitudes))
                # Note - we need to ignore the zero frequency component
                if len(freq) < 2:
                    continue
                max_amplitude = np.max(amplitudes[1:])
                max_frequency = freq[np.argmax(amplitudes[1:]) + 1]  # Adjust index due to exclusion
                print("Max amplitude: {} at frequency: {}".format(max_amplitude, max_frequency))

                if (max_fft_amplitude is None) or (max_amplitude > max_fft_amplitude):
                    max_fft_amplitude = max_amplitude
                    max_fft_freq = max_frequency
            except Exception:
                pass
                
    return max_fft_freq, max_fft_amplitude

    
# Edge Calculation -- this is only for power
# Here we will get:
# Number of power edges (sudden changes) on each node
# As well as the duration between edges
# Then get the sum across all nodes for the job for the count
# And get the mean duration between edges across all nodes for the job
# Big question right now -- what threshold to use for an edge?
def calculate_power_edges(df, hosts, threshold=3000):
    print("Calculating power edges for column: gpu_power")
    #print("Using threshold: {} watts".format(threshold))
    #print("Hosts: {}".format(hosts))
    #print(df)

    total_edges = 0
    mean_duration = None
    possible_gpus = int(df["num_alloc_gpus"].max())

    for host in hosts:
        for gpu_index in range(possible_gpus):
            column = "gpu_{}_power".format(gpu_index)
            if column not in df.columns:
                continue

            power_values = df.loc[df["node_id"] == host, column].to_numpy()
            # Calculate the differences between consecutive power readings
            diffs = np.abs(np.diff(power_values))
            # Count the number of edges exceeding the threshold
            edges = np.sum(diffs > threshold)
            total_edges += edges

            durations = np.where(diffs > threshold)[0]
            if len(durations) > 1:
                duration_diffs = np.diff(durations) # Note - this is set to a unit of one, generally one second
                mean_duration = np.mean(duration_diffs)

    return total_edges, mean_duration



# RSM
# This is the resource spike measurement
# We take the integral under the differential, but we run it through a rectifier first
# So we only count increases in resource use, not decreases
# For now, we only do this across all the GPUs
def calculate_RSM(df, hosts, column):
    print("Calculating RSM for column: {}".format(column))
    possible_gpus = 4 # highest count between Polaris and Supercloud
    rsm = 0
    for host in hosts:
        for gpu_index in range(possible_gpus):
            column = "gpu_{}_power".format(gpu_index)
            if column in df.columns:
                
                values = df.loc[df["node_id"] == host, "{}".format(column)].to_numpy()
                diffs = np.diff(values)
                rectified_diffs = np.where(diffs > 0, diffs, 0)
                rsm += np.sum(rectified_diffs)

    return round(float(rsm), 3)


# RI temporal -- resource imbalance
# Temporal looks at variation in resource use over time
# RIt = max of this across all nodes:
#          sum of (U at this time on this node) / sum of (max U on this node across all time)
# Conceptually, this looks at the worst-case for

# RI spatial -- resource imbalance
# Spatial looks at variation in resource use across nodes
# RIs = sum of (max U for the job - max U for this node) / sum of (max U for the job)


# We will do this for compute use, memory use, memory capacity use, power, and temperature
# NOTE -- currently we do not have memory capacity use, but the data exists and just needs preprocessing
"""_
def calculate_RI(df, hosts, column):
    print("Calculating RI for column: {}".format(column))
    print("Hosts: {}".format(hosts))
    print(df)
    results = {
        "ri_temporal_{}".format(column): 0,
        "ri_spatial_{}".format(column): 0,
    }

    max_ri_temporal = 0
    ri_spatial = 0
    max_for_job = 0
    max_per_node = {}
    for host in hosts:
        max_per_node[host] = df.loc[df["host"] == host, "{}_avg".format(column)].max()
        sum_value = df[df["host"] == host]["{}_avg".format(column)].sum()
        sum_of_local_max = max_per_node[host] * len(df[df["host"] == host])
        if max_per_node[host] > max_for_job:
            max_for_job = max_per_node[host]

        ri_temporal = 1 - (sum_value / sum_of_local_max)
        if ri_temporal > max_ri_temporal:
            max_ri_temporal = ri_temporal

    top = 0
    bot = 0
    for host in hosts:
        top = top + (max_for_job - max_per_node[host])
        bot = bot + max_for_job

    if bot == 0:
        ri_spatial = 0
    else:
        ri_spatial = top / bot

    results["ri_temporal_{}".format(column)] = round(float(max_ri_temporal), 3)
    results["ri_spatial_{}".format(column)] = round(float(ri_spatial), 3)

    return results
"""


def get_RI(df, hosts):
    print("Getting RIs for job on hosts: {}".format(hosts))
    gpu_columns = [
        "gpu_utilization",
        "gpu_mem_utilization",
        "gpu_{}_mem_allocation",
    ]  # Stopped here. Need to make columns and then call the ri thing if gpus are used. then need to intake cpu side data in the other side. note the issue of which gpu to measure for ri stuff.
    # First we need to know if it uses the gpu at all, ever
    # If not, we can skip it
    used_gpu = False
    for host in hosts:
        for i in range(0, 4):
            # check if column exists
            if "gpu_{}_utilization".format(i) not in df.columns:
                continue
            if df.loc[df["node_id"] == host, "gpu_{}_utilization".format(i)].max() > 0:
                used_gpu = True
                break

    if not used_gpu:
        print("Job did not use GPU, skipping RI calculation.")
        return None
    print("Calculating RIs for job using GPUs.")
    # results = {"ri_temporal_load": 0, "ri_spatial_load": 0,}
    # We will use:
    # gpu_load_{}
    # gpu_mem_util_{}
    # gpu_temp_{}
    # gpu_power_usage_{}
    # gpu_mem_capacity_{}

    # What should we do here to accommodate jobs that use less than all 4 gpus?
    # We will use the mean of the 4 gpus for now
    def calc_ri(df, hosts, column):
        try:
            max_ri_temporal = 0
            ri_spatial = 0
            max_for_job = 0
            max_per_node = {}
            for node in hosts:
                max_per_node[node] = df.loc[df["node_id"] == node, f"{column}"].max()
                sum_value = df.loc[df["node_id"] == node, f"{column}"].sum()
                sum_of_local_max = max_per_node[node] * len(
                    df.loc[df["node_id"] == node]
                )
                # print(f"Node {node}: sum_value = {sum_value}, sum_of_local_max = {sum_of_local_max}, max_per_node = {max_per_node[node]},min_per_node = {df.loc[df['node_id'] == node, f'{column}'].min()}")
                # print(f"Number of entries for node {node}: {len(df.loc[df['node_id'] == node])}")
                if max_per_node[node] > max_for_job:
                    max_for_job = max_per_node[node]

                ri_temporal = 1 - (sum_value / sum_of_local_max)
                if ri_temporal > max_ri_temporal:
                    max_ri_temporal = ri_temporal

            top = 0
            bot = 0
            for node in hosts:
                top += max_for_job - max_per_node[node]
                bot += max_for_job

            ri_spatial = 0 if bot == 0 else top / bot

            return round(float(max_ri_temporal), 3), round(float(ri_spatial), 3)
        except:
            print(f"Error calculating RI for column {column}")
            return 0, 0

    # df['temp'] = df[['gpu_temp_0', 'gpu_temp_1', 'gpu_temp_2', 'gpu_temp_3']].mean(axis=1)
    # df['load'] = df[['gpu_load_0', 'gpu_load_1', 'gpu_load_2', 'gpu_load_3']].mean(axis=1)
    # df["load"] = (df["gpu_load_0"] + df["gpu_load_1"] + df["gpu_load_2"] + df["gpu_load_3"]) / 4
    # NOTE THIS IS ONLY gpu 0 USE THE ACTUAL MEAN
    res = {}
    # Calculate RIs for each metric for GPU
    if "gpu_utilization" in df.columns:
        res["ri_temporal_load"], res["ri_spatial_load"] = calc_ri(
            df, hosts, "gpu_utilization"
        )
    else:
        res["ri_temporal_load"], res["ri_spatial_load"] = 0, 0

    if "gpu_mem_utilization" in df.columns:
        res["ri_temporal_mem_util"], res["ri_spatial_mem_util"] = calc_ri(
            df, hosts, "gpu_mem_utilization"
        )
    else:
        res["ri_temporal_mem_util"], res["ri_spatial_mem_util"] = 0, 0

    if "gpu_power" in df.columns:
        res["ri_temporal_power"], res["ri_spatial_power"] = calc_ri(
            df, hosts, "gpu_power"
        )
    else:
        res["ri_temporal_power"], res["ri_spatial_power"] = 0, 0

    if "gpu_mem_allocation" in df.columns:
        res["ri_temporal_mem_alloc"], res["ri_spatial_mem_alloc"] = calc_ri(
            df, hosts, "gpu_mem_allocation"
        )
    else:
        res["ri_temporal_mem_alloc"], res["ri_spatial_mem_alloc"] = 0, 0

    if "gpu_temp" in df.columns:
        res["ri_temporal_temp"], res["ri_spatial_temp"] = calc_ri(
            df, hosts, "gpu_temp"
        )
    else:
        res["ri_temporal_temp"], res["ri_spatial_temp"] = 0, 0

    # Now CPU side RIs

    if "cpu_mem_rss" in df.columns:
        res["ri_cpu_mem_rss"], res["ri_spatial_cpu_mem_rss"] = calc_ri(
            df, hosts, "cpu_mem_rss"
        )
    else:
        res["ri_cpu_mem_rss"], res["ri_spatial_cpu_mem_rss"] = 0, 0

    if "cpu_mem_alloc" in df.columns:
        res["ri_cpu_mem_alloc"], res["ri_spatial_cpu_mem_alloc"] = calc_ri(
            df, hosts, "cpu_mem_alloc"
        )
    else:
        res["ri_cpu_mem_alloc"], res["ri_spatial_cpu_mem_alloc"] = 0, 0

    if "cpu_read_kb" in df.columns:
        res["ri_cpu_read_kb"], res["ri_spatial_cpu_read_kb"] = calc_ri(
            df, hosts, "cpu_read_kb"
        )
    else:
        res["ri_cpu_read_kb"], res["ri_spatial_cpu_read_kb"] = 0, 0

    if "cpu_write_kb" in df.columns:
        res["ri_cpu_write_kb"], res["ri_spatial_cpu_write_kb"] = calc_ri(
            df, hosts, "cpu_write_kb"
        )
    else:
        res["ri_cpu_write_kb"], res["ri_spatial_cpu_write_kb"] = 0, 0

    if "mem_pct_rss_to_alloc" in df.columns:
        res["ri_mem_pct_rss_to_alloc"], res["ri_spatial_mem_pct_rss_to_alloc"] = (
            calc_ri(df, hosts, "mem_pct_rss_to_alloc")
        )
    else:
        res["ri_mem_pct_rss_to_alloc"], res["ri_spatial_mem_pct_rss_to_alloc"] = 0, 0

    if "mem_pct_utilization" in df.columns:
        res["ri_mem_pct_utilization"], res["ri_spatial_mem_pct_utilization"] = calc_ri(
            df, hosts, "mem_pct_utilization"
        )
    else:
        res["ri_mem_pct_utilization"], res["ri_spatial_mem_pct_utilization"] = 0, 0

    if "mem_pct_rss_to_available" in df.columns:
        (
            res["ri_mem_pct_rss_to_available"],
            res["ri_spatial_mem_pct_rss_to_available"],
        ) = calc_ri(df, hosts, "mem_pct_rss_to_available")
    else:
        (
            res["ri_mem_pct_rss_to_available"],
            res["ri_spatial_mem_pct_rss_to_available"],
        ) = (0, 0)

    print("Calculated RIs:")
    # if exists 1 value in res not ==0 print it
    for key, value in res.items():
        if value != 0:
            with open("ri_debug.txt", "a") as f:
                # print job number
                f.write("Results for job {}: {}\n".format(df["job_id"].iloc[0], res))
                f.write("\n")
                f.close()
            break
    return res
