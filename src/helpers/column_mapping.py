from enum import StrEnum, auto

class ColumnNames(StrEnum):
    JOB_ID = auto()
    NODE_ID = auto()
    TASK_ID = auto()
    TASK_ARRAY = auto()
    USER_ID = auto()
    PROJECT_ID = auto()
    START_TIMESTAMP = auto()
    END_TIMESTAMP = auto()
    NUM_NODES = auto()
    NODE_HOURS = auto()
    CPU_PCT_UTILIZATION = auto()
    CPU_ELAPSED_TIME = auto()
    TIMESTAMP = auto()
    CPU_TIME = auto()
    CPU_FREQUENCY = auto()
    CPU_READ_KB = auto()
    CPU_WRITE_KB = auto()
    CPU_STEP = auto()
    CPU_MEM_RSS = auto()
    CPU_MEM_ALLOC = auto()
    CPU_PAGES = auto()
    QUEUE_NAME = auto()
    RUNTIME = auto()
    GPU_0_UTILIZATION = auto()
    GPU_1_UTILIZATION = auto()
    GPU_2_UTILIZATION = auto()
    GPU_3_UTILIZATION = auto()
    GPU_UTILIZATION = auto()
    GPU_0_MEM_UTILIZATION = auto()
    GPU_1_MEM_UTILIZATION = auto()
    GPU_2_MEM_UTILIZATION = auto()
    GPU_3_MEM_UTILIZATION = auto()
    GPU_MEM_UTILIZATION = auto()
    GPU_0_MEM_ALLOCATION = auto()
    GPU_1_MEM_ALLOCATION = auto()
    GPU_2_MEM_ALLOCATION = auto()
    GPU_3_MEM_ALLOCATION = auto()
    GPU_0_POWER = auto()
    GPU_1_POWER = auto()
    GPU_2_POWER = auto()
    GPU_3_POWER = auto()
    GPU_POWER = auto()
    GPU_0_TEMPERATURE = auto()
    GPU_1_TEMPERATURE = auto()
    GPU_2_TEMPERATURE = auto()
    GPU_3_TEMPERATURE = auto()
    GPU_TEMPERATURE = auto()
    DOMAIN = auto()


COLUMN_MAPPINGS = {
    "MIT_SUPERCLOUD": {
        'id_job': ColumnNames.JOB_ID,
        'Node': ColumnNames.NODE_ID,
        'id_array_task': ColumnNames.TASK_ID,  # Keeping it like this for now
        'id_array_job': ColumnNames.TASK_ARRAY,  # Keeping it like this for now
        'time_start': ColumnNames.START_TIMESTAMP,
        'time_end': ColumnNames.END_TIMESTAMP,
        'id_user': ColumnNames.USER_ID,
        'nodes_alloc': ColumnNames.NUM_NODES,
        'CPUUtilization': ColumnNames.CPU_PCT_UTILIZATION,  # Aggregate of used CPUs
        'ElapsedTime': ColumnNames.CPU_ELAPSED_TIME,
        'EpochTime': ColumnNames.TIMESTAMP,
        'CPUFrequency': ColumnNames.CPU_FREQUENCY,
        'CPUTime': ColumnNames.CPU_TIME,  # Could be named better
        'ReadMB': ColumnNames.CPU_READ_KB,
        'WriteMB': ColumnNames.CPU_WRITE_KB,
        'Step': ColumnNames.CPU_STEP,
        'RSS': ColumnNames.CPU_MEM_RSS,
        'VMSize': ColumnNames.CPU_MEM_ALLOC,
        'Pages': ColumnNames.CPU_PAGES,
        "Partition": ColumnNames.QUEUE_NAME,
    },
    "POLARIS": {
        'job_identifier': ColumnNames.JOB_ID,
        'username': ColumnNames.USER_ID,
        'project_name': ColumnNames.PROJECT_ID,
        'host': ColumnNames.NODE_ID,  # confirm this mapping
        # do we want the queuename
        'runtime_seconds': ColumnNames.RUNTIME,
        'nodes_used': ColumnNames.NUM_NODES,
        'used_node_hours': ColumnNames.NODE_HOURS,  # Calculated, so approximate

        'GPU_load_0': ColumnNames.GPU_0_UTILIZATION,
        'GPU_load_1': ColumnNames.GPU_1_UTILIZATION,
        'GPU_load_2': ColumnNames.GPU_2_UTILIZATION,
        'GPU_load_3': ColumnNames.GPU_3_UTILIZATION,
        'GPU_load_avg': ColumnNames.GPU_UTILIZATION,  # need to norm

        'GPU_mem_util_0': ColumnNames.GPU_0_MEM_UTILIZATION,
        'GPU_mem_util_1': ColumnNames.GPU_1_MEM_UTILIZATION,
        'GPU_mem_util_2': ColumnNames.GPU_2_MEM_UTILIZATION,
        'GPU_mem_util_3': ColumnNames.GPU_3_MEM_UTILIZATION,
        'GPU_mem_util_avg': ColumnNames.GPU_MEM_UTILIZATION,  # need to norm

        'GPU_mem_alloc_0': ColumnNames.GPU_0_MEM_ALLOCATION,  # chec units
        'GPU_mem_alloc_1': ColumnNames.GPU_1_MEM_ALLOCATION,
        'GPU_mem_alloc_2': ColumnNames.GPU_2_MEM_ALLOCATION,
        'GPU_mem_alloc_3': ColumnNames.GPU_3_MEM_ALLOCATION,

        'GPU_power_usage_0': ColumnNames.GPU_0_POWER,
        'GPU_power_usage_1': ColumnNames.GPU_1_POWER,
        'GPU_power_usage_2': ColumnNames.GPU_2_POWER,
        'GPU_power_usage_3': ColumnNames.GPU_3_POWER,
        # we don't actually want this - this is average, not sum, which is what we want
        #'GPU_power_usage_avg': ColumnNames.GPU_POWER,

        'GPU_temp_0': ColumnNames.GPU_0_TEMPERATURE,
        'GPU_temp_1': ColumnNames.GPU_1_TEMPERATURE,
        'GPU_temp_2': ColumnNames.GPU_2_TEMPERATURE,
        'GPU_temp_3': ColumnNames.GPU_3_TEMPERATURE,
        'GPU_temp_avg': ColumnNames.GPU_TEMPERATURE,

    }
}
