import sys
import pandas

def resample(df, frequency, host_column="host_number", timestamp_column="timestamp"):
    return df.groupby(by=host_column)[df.columns.to_list()].resample(frequency, on=timestamp_column).first()

def join_and_resample(destination, sources, frequency, host_column="host_number", timestamp_column="timestamp"):
    data = []
    for source in sources:
        partial = pandas.read_pickle(source)
        data.append(resample(partial, frequency, host_column, timestamp_column))
    out = pandas.concat(data)
    out = out.reset_index(level=[timestamp_column])
    out.to_pickle(destination)


if __name__ == "__main__":

    if (len(sys.argv) < 3):
        print('Usage: ' + sys.argv[0] + ' <output> <input> <input> <...>')

    join_and_resample(sys.argv[1], sys.argv[2:], '10min')

