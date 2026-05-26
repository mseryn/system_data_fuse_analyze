import pandas
import seaborn
import plotly
import matplotlib.pyplot
import numpy as np
import os

# Handful of plotters built for the Polaris data
# Specifically tailored for the Dec '25 deadline, ISC

base_names = ["small", "medium", "large"]

images_dir = "../../images/"
plot_dir = "custom_polaris/"

# Demonstrative file to show how to use plots in this framework


def combine_queues(queue):
    for n in base_names:
        if n in queue:
            return n
    return queue

def density_fft(df):
    cols = ["fft_power_amplitudes", "fft_power_frequencies"]
    w = 4
    h = 4.5
    
    for column in cols:
        density_plot = seaborn.displot(df, x=column, kind="kde", hue="queue_name", legend=False,
                                       fill=True, alpha=0.2)
        fig = density_plot.figure  # get_figure()
        ax = fig.get_axes()[0]
        fig.set_size_inches(w,h)
        ax.set_ylabel( "" , size = 12 )

        # absolute value the FFT amplitudes, so log scale makes sense
        df["fft_power_amplitudes"] = df["fft_power_amplitudes"].apply(lambda x: abs(x))

        if "amplitude" in column:
        #if "frequency" in column or "amplitude" in column:
            #ax.set_xscale("log")
            ax.set(xlim=(0, 20000))

        fig.savefig(os.path.join(images_dir, plot_dir, f"density_{column}.png"))
        fig.clf()
        matplotlib.pyplot.close()
        
        

def cdfs(df):
    # Producing a subset of CDFs
    columns = [
        "num_nodes",
        "power_edges",
        "fft_power_amplitudes",
        "fft_power_frequencies",
        "max_alloc",
        "max_load",
        "max_mem",
        "max_temp",
        "mean_alloc",
        "mean_load",
        "mean_mem",
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
    w = 4
    h = 4.5

    for column in columns:
        cdf_plot = seaborn.displot(df, x=column, kind="ecdf", hue="queue_name", legend=False)
        fig = cdf_plot.figure  # get_figure()
        ax = fig.get_axes()[0]
        fig.set_size_inches(w,h)
        ax.set_ylabel( "" , size = 12 )

        # If this has to do with power edges, we need to use a log scale
        #if "edge" in column or "rsm" in column:
        #    ax.set_xscale("log")

        fig.savefig(os.path.join(images_dir, plot_dir, f"cdf_{column}.png"))
        fig.clf()
        matplotlib.pyplot.close()

    # Now doing just one repeat plot so I can grab the legend
    column = "num_nodes"
    cdf_plot = seaborn.displot(df, x=column, kind="ecdf", hue="queue_name")
    fig = cdf_plot.figure  # get_figure()
    ax = fig.get_axes()[0]
    fig.set_size_inches(w,h)
    ax.set_ylabel( "" , size = 12 )
    fig.savefig(os.path.join(images_dir, plot_dir, f"cdf_{column}_with_legend.png"))
    fig.clf()
    matplotlib.pyplot.close()

    

    

    
def join_domains_by_project(df, projects_file):
    # Change this to reflect new data format
    mapper = pandas.read_csv(projects_file)
    shortened_mapper = mapper[["PROJECT_NAME", "SCIENCE_FIELD_SHORT", "SCIENCE_FIELD"]]
    shortened_mapper = shortened_mapper.rename(columns={"PROJECT_NAME": "project"})
    shortened_mapper = shortened_mapper.rename(columns={"SCIENCE_FIELD_SHORT": "domain"})
    shortened_mapper = shortened_mapper.rename(columns={"SCIENCE_FIELD": "domain_full"})

    
    joined = df.merge(shortened_mapper, on="project", how="left")
    return joined


def pairgrid_plots(df):
    # Example pairgrid plot
    g = seaborn.PairGrid(df, hue="queue_name",
                            vars=["max_power", "mean_power", "max_temp", "rsm_power", "diff_power", 
                                  "stddev_power", "power_edges", "mean_duration_between_power_edges"],
                            diag_sharey=False)
    g.map_upper(seaborn.scatterplot, s=15)
    g.map_lower(seaborn.kdeplot)
    g.map_diag(seaborn.kdeplot, lw=2)
    fig = g.fig
    fig.savefig(os.path.join(images_dir, plot_dir, "pairgrid_example.png"))
    fig.clf()
    matplotlib.pyplot.close()


if __name__ == "__main__":
    df = pandas.read_pickle("supercloud_april_sums.pkl.zst")
    # df = join_domains_by_project(df, "../../data/project_to_science_polaris.csv")
    df["system"] = "Polaris"

    # Let's normalize the power_edges column by the number of nodes
    df["power_edges"] = df["power_edges"] / df["node_hours"]

    df["class"] = df["queue_name"].apply(combine_queues)
    reduced_df = df[df["queue_name"].isin(base_names)]

    reduced_df["stddev_power"] = df["var_power"].apply(lambda x: np.sqrt(x))
    reduced_df["runtime"] = reduced_df["runtime_seconds"] / 60.0  # Converting to minutes
    reduced_df["diff_power"] = reduced_df["max_power"] - reduced_df["mean_power"]
    for col in reduced_df.select_dtypes(include='number').columns:
        if "alloc" in col:
            reduced_df[col] = reduced_df[col] / (1024*1024)  # Converting to GB

    cdfs(reduced_df)
    density_fft(reduced_df)
    temperature_power_domain_boxplots(reduced_df)
    pairgrid_plots(reduced_df)
