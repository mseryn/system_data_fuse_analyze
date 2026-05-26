import seaborn
import pprint
import os
import matplotlib.pyplot
import pandas

plot_dir = "histograms/"

from helpers.column_mapping import ColumnNames, COLUMN_MAPPINGS

# Demonstrative file to show how to use plots in this framework

def run_all(df, output_dir):
    print("-----")
    print("In plotter: histograms.py")
    # If plot_dir does not exist, create it
    if not os.path.exists(os.path.join(output_dir, plot_dir)):
        os.makedirs(os.path.join(output_dir, plot_dir))
        
    cols = list((df.select_dtypes(include='number')).columns)
    cols.sort()
    pprint.pprint(cols)
    for column in cols:
        if "minutes_to" not in column and "time_to" not in column:
            print(f"Generating histogram for column: {column}")
            histogram_of_column(df, column, output_dir)

def histogram_of_column(df, column_name, output_dir):
    hist_plot = seaborn.histplot(data=df, x=column_name)
    fig = hist_plot.get_figure()
    fig.savefig(os.path.join(output_dir, plot_dir, f"histogram_{column_name}.png"))
    fig.clf()
    matplotlib.pyplot.close()
    