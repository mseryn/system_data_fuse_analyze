#!/usr/bin/env python3
import influxdb_client, os, time
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.exceptions import InfluxDBError
import pandas
import sys

token = os.environ.get("INFLUXDB_TOKEN")
org = "spear"
url = "http://mysql-drlan:8086"

write_client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)

bucket="polaris"

class BatchingCallback(object):

    def success(self, conf: (str, str, str), data: str):
        print(f"Written batch: {conf}")

    def error(self, conf: (str, str, str), data: str, exception: InfluxDBError):
        print(f"Cannot write batch: {conf}, due: {exception}")

    def retry(self, conf: (str, str, str), data: str, exception: InfluxDBError):
        print(f"Retryable error occurs for batch: {conf}, retry: {exception}")

callback = BatchingCallback()
write_api = write_client.write_api(success_callback=callback.success,
                          error_callback=callback.error,
                          retry_callback=callback.retry)

data = pandas.read_pickle(sys.argv[1])

print(data.columns)
metadata = ['host', 'job_identifier', 'host_number', 'timestamp_raw']
metrics = [column for column in data.columns if column not in metadata and column != 'timestamp']

def submit_to_influx(row):
    point = Point('polaris_data')
    point.time(row['timestamp'])
    for meta in metadata:
        point.tag(meta, row[meta])
    for metric in metrics:
        point.field(metric, row[metric])
    write_api.write(bucket=bucket, org="spear", record=point)
    

data.apply(submit_to_influx, axis=1)

