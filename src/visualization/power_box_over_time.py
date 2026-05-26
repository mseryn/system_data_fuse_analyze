import seaborn
import pprint
import os
import pandas
import numpy as np
import matplotlib.pyplot

images_dir = "../../images/"
plot_dir = "power_box_over_time/"

from helpers.column_mapping import ColumnNames, COLUMN_MAPPINGS

# Demonstrative file to show how to use plots in this framework

def run_all(df):
    print("-----")
    print("In plotter: power_box_over_time.py")
    # If plot_dir does not exist, create it
    if not os.path.exists(os.path.join(images_dir, plot_dir)):
        os.makedirs(os.path.join(images_dir, plot_dir))
        
    data_columns = list(df.columns)
    data_columns.sort()
    pprint.pprint(data_columns)

    if "system" not in df.columns:
        print("Dataframe must contain a 'system' column to differentiate systems. Appending 'SYSTEM' as default.")
        df['system'] = 'SYSTEM'

    columns = [
        "num_nodes",
        "power_edges",
        "fft_power_amplitudes",
        "fft_power_frequencies",
        "max_alloc",
        "max_load",
        #"max_mem",
        "max_temp",
        "mean_alloc",
        "mean_load",
        #"mean_mem",
        "mean_temp",
        "mean_duration_between_power_edges",
        "sum_power",
        "stddev_power",
        "ri_spatial_power",
        "ri_spatial_temp",
        "ri_temporal_load",
        "ri_temporal_mem_alloc",
        "ri_temporal_mem_util",
        "ri_temporal_power",
        "ri_temporal_temp",
        "ri_spatial_load",
        "ri_spatial_mem_alloc",
        "ri_spatial_mem_util",
        "ri_spatial_power",
        "rsm_power",
        "runtime",
        "node_hours",
        "max_power",
        "mean_power",
        "diff_power",
        "gpu_count",
    ]

    for col in columns:
        if col in df.columns:
            print("\n\n\n")
            print(col)
            both_systems_time_series_boxplot(df, col)
            monthly_sum_line_plot(df, col)

def both_systems_time_series_boxplot(df, column_name):

    # First we need to get rid of the MIT jobs that had no GPUs
    # This is because these jobs consume zero power - the supercloud is disaggregated
    df = df.loc[~((df["system"] == "MIT Supercloud") & (df["gpu_count"] == 0))]

    # divide power columns by 1000 to get kW
    if "sum" in column_name:
        df[column_name] = df[column_name] / 1000.0

    # We are going to try to just get this data out of here manually because I'm wasting time
    data = {"system": [], "year month": [], "{}".format(column_name): []}
    # First get the year
    df['year'] = pandas.to_datetime(df['start_timestamp']).dt.year
    # We are just going to manually set the month because otherwise it's slow and annoying
    df['month'] = pandas.to_datetime(df['start_timestamp']).dt.month
    years = df['year'].unique()

    # Just so it shows up how we want it to in the graph
    years = list(years)
    years.sort()
    months = df['month'].unique()
    months = list(months)
    months.sort()

    # Now we go over each year, then each month, and get the sum of all the power used for each job in that month
    # This specific order ensures the x axis is sorted
    for year in years:
        for system in df["system"].unique():
            for month in months:
                subset = df.loc[(df["year"] == year) & (df["month"] == month) & (df["system"] == system)]
                #df['y_values'] = df['y_values'].replace(0, np.nan)
                subset[column_name] = subset[column_name].replace(0, np.nan)

                for val in subset[column_name].to_list():
                    data["system"].append(system)
                    data["year month"].append("{} {}".format(year, month))
                    data[column_name].append(val)

    # Now turn this into a dataframe seaborn can use
    plotdf =  pandas.DataFrame.from_dict(data)

    # Now plot that using seaborn
    box_plot = seaborn.boxplot(data=plotdf, x='year month', y=column_name, hue='system')
    fig = box_plot.get_figure()
    fig.savefig(os.path.join(images_dir, plot_dir, f"power_box_over_time_{column_name}.png"))
    fig.clf()

    

    # Making test data now
    data = {"system": [], "year month": [], "{}".format(column_name): []}
    remaining_months = [1,2,3,4,5,6,7,8,9,10,11,12]
    for year in years:
        # First MIT
        system = "MIT Supercloud"

        existing_data = df.loc[(df["year"] == year) & (df["system"] == system) & (df["month"] == 4)]
        # Now fill in the missing months with data plus random noise
        for month in remaining_months:
            for val in existing_data[column_name].to_list():
                data["system"].append(system)
                data["year month"].append("{} {}".format(year, month))
                data[column_name].append(val * (np.random.rand()))  

        # Now Polaris
        system = "Polaris"
        existing_data = df.loc[(df["year"] == year) & (df["system"] == system) & (df["month"] == 4)]
        for month in remaining_months:
            for val in existing_data[column_name].to_list():
                data["system"].append(system)
                data["year month"].append("{} {}".format(year, month))
                data[column_name].append(val * ((np.random.rand() ) )) 

    plotdf =  pandas.DataFrame.from_dict(data)
    box_plot = seaborn.boxplot(data=plotdf, x='year month', y=column_name, hue='system',
                               showfliers=False)
    fig = box_plot.get_figure()
    fig.set_size_inches(8,2.5)
    fig.subplots_adjust(bottom=0.4)
    
    if "sum" in column_name:
        fig.axes[0].set_ylabel("Energy (kW)")

    # Tilt the x axis labels
    box_plot.set_xticklabels(box_plot.get_xticklabels(), rotation=45)
    fig.savefig(os.path.join(images_dir, plot_dir, f"TEST_power_box_over_time_{column_name}.png"))
    # y axis title is Energy (KW)
    
    # Set the figure to wide form
    fig.clf()

    
# Now we need to do the same thing but add up certain columns per month and plot
def monthly_sum_line_plot(df, column_name):
    # First we need to get rid of the MIT jobs that had no GPUs
    # This is because these jobs consume zero power - the supercloud is disaggregated
    df = df.loc[~((df["system"] == "MIT Supercloud") & (df["gpu_count"] == 0))]

    # divide power columns by 1000 to get kW
    if "sum" in column_name:
        df[column_name] = df[column_name] / 1000.0

    # We are going to try to just get this data out of here manually because I'm wasting time
    data = {"system": [], "year month": [], "{}".format(column_name): []}
    # First get the year
    df['year'] = pandas.to_datetime(df['start_timestamp']).dt.year
    # We are just going to manually set the month because otherwise it's slow and annoying
    df['month'] = pandas.to_datetime(df['start_timestamp']).dt.month
    years = df['year'].unique()

    # Just so it shows up how we want it to in the graph
    years = list(years)
    years.sort()
    months = df['month'].unique()
    months = list(months)
    months.sort()

    # Now we go over each year, then each month, and get the sum of all the power used for each job in that month
    # This specific order ensures the x axis is sorted
    for year in years:
        for system in df["system"].unique():
            for month in months:
                subset = df.loc[(df["year"] == year) & (df["month"] == month) & (df["system"] == system)]

                total = subset[column_name].sum()

                data["system"].append(system)
                data["year month"].append("{} {}".format(year, month))
                data[column_name].append(total)

    # Now turn this into a dataframe seaborn can use
    plotdf =  pandas.DataFrame.from_dict(data)
    # Now plot that using seaborn
    line_plot = seaborn.lineplot(data=plotdf, x='year month', y=column_name, hue='system', marker='o')
    fig = line_plot.get_figure()
    fig.set_size_inches(8,2.5)
    fig.subplots_adjust(bottom=0.4)
    # Tilt the x axis labels
    line_plot.set_xticklabels(line_plot.get_xticklabels(), rotation=45)
    fig.savefig(os.path.join(images_dir, plot_dir, f"power_monthly_sum_over_time_{column_name}.png"))
    fig.clf()
    matplotlib.pyplot.close()



# Note - this plotter needs to be called manually since it uses both systems for the dec 25 paper submission
if __name__ == "__main__":
    #polaris = pandas.read_pickle("../../data/postprocessed/polaris_april_sums.pkl.zst")
    mit_supercloud = pandas.read_pickle("../../data/postprocessed/supercloud_april_sums.pkl.zst")
    polaris = pandas.read_pickle("~/polaris_sums/polaris_2024.pkl.zst")
    
    # Add a column to each dataframe to identify the system
    polaris['system'] = 'Polaris'
    mit_supercloud['system'] = 'MIT Supercloud'

    # Get rid of all of the numeric columns that have nothing but nan or 0 in them
    df = pandas.concat([polaris, mit_supercloud], ignore_index=True)
    cols_to_drop = []
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    for c in numeric_cols:
        print("looking at {}".format(c))
        unique = df[c].unique()
        print(unique)
        print(type(unique))
        print(len(unique))
        if len(unique) <= 2:
            cols_to_drop.append(c)

    df = df.drop(columns=cols_to_drop)

    run_all(df)
    
