import seaborn
import pprint
import os
import matplotlib.pyplot
import pandas

plot_dir = "cdfs/"

from helpers.column_mapping import ColumnNames, COLUMN_MAPPINGS

# Demonstrative file to show how to use plots in this framework

def run_all(df, output_dir):
    print("-----")
    print("In plotter: cdfs.py")
    # If plot_dir does not exist, create it
    if not os.path.exists(os.path.join(output_dir, plot_dir)):
        os.makedirs(os.path.join(output_dir, plot_dir))
        
    cols = list((df.select_dtypes(include='number')).columns)
    cols.sort()
    pprint.pprint(cols)
    for column in cols:
        if "minutes_to" not in column and "time_to" not in column:
            print(f"Generating cdfs for column: {column}")
            cdf_of_column(df, column, output_dir)

def cdf_of_column(df, column_name, output_dir):
    cdf_plot = seaborn.displot(df, x=column_name, kind="ecdf", hue="queue_name")
    fig = cdf_plot.figure #get_figure()
    fig.savefig(os.path.join(output_dir, plot_dir, f"cdf_{column_name}.png"))
    fig.clf()
    matplotlib.pyplot.close()