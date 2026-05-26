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

    

    
def temperature_power_domain_boxplots(df):

    # Box plots of temperature and power by domain
    columns = ["max_power"]
        #w = 8
        #h = 4.5

    # Drop "Internal", "Training", and "Support" domains for clarity
    df = df[~df["domain_full"].isin(["Internal", "Training", "Support"])]

    # Now let's make domain_full a string where, if : exists, we drop anything that comes before it
    # We have to be careful, not all entries have a colon
    def shorten_domain(domain):
        if isinstance(domain, str) and ":" in domain:
            return domain.split(":", 1)[1].strip()
        else:
            return domain
    df["domain_full"] = df["domain_full"].apply(shorten_domain)
    df["domain_full"] = df["domain_full"].fillna("unknown")

    order = df["domain_full"].unique()
    order = list(order)
    order.sort()
    # Get average max power by domain to order the plot
    domain_averages = {}
    for domain in order:
        subset = df[df["domain_full"] == domain]
        domain_averages[domain] = subset["sum_power"].mean()
    # Now sort order by that
    order.sort(key=lambda x: domain_averages[x], reverse=True)

    for column in columns:
        fig, ax = matplotlib.pyplot.subplots(figsize=(5.5, 7))
        
        box_plot = seaborn.boxplot(data=df, y="domain_full", x=column, showfliers=False,
                                   fill=False, order=order, ax=ax)
        ax.set_ylabel( "" , size = 12 )
        fig.subplots_adjust(left=0.6)
        ax.set_xlabel( "Max Power Draw (W)" , size = 12 )
        box_plot.set_xticklabels(box_plot.get_xticklabels(), rotation=90)

        #fig.tight_layout()

        fig.savefig(os.path.join(images_dir, plot_dir, f"boxplot_{column}_by_domain.png"))
        fig.clf()
        matplotlib.pyplot.close()

        
    # Now doing this with node-hours per job in each domain
    columns= ["node_hours"]
    for column in columns:
        fig, ax = matplotlib.pyplot.subplots(figsize=(5.5, 7))
        #order = df["domain_full"].unique()
        #order = list(order)
        #order.sort()
        # Get average node_hours by domain to order the plot
        domain_averages = {}
        for domain in order:
            subset = df[df["domain_full"] == domain]
            domain_averages[domain] = subset[column].mean()
        # Now sort order by that
        #order.sort(key=lambda x: domain_averages[x], reverse=True)
        
        box_plot = seaborn.boxplot(data=df, y="domain_full", x=column, showfliers=False,
                                   fill=False, order=order, ax=ax)
        ax.set_ylabel( "" , size = 12 )
        fig.subplots_adjust(left=0.6)
        ax.set_xlabel( "Node Hours per Job" , size = 12 )
        box_plot.set_xticklabels(box_plot.get_xticklabels(), rotation=90)

        #fig.tight_layout()

        fig.savefig(os.path.join(images_dir, plot_dir, f"boxplot_{column}_by_domain.png"))
        fig.clf()
        matplotlib.pyplot.close()

    # Now doing it for sum_power
    columns= ["sum_power"]
    for column in columns:
        fig, ax = matplotlib.pyplot.subplots(figsize=(5.5, 7))
        #order = df["domain_full"].unique()
        #order = list(order)
        #order.sort()
        # Get average sum_power by domain to order the plot
        domain_averages = {}
        for domain in order:
            subset = df[df["domain_full"] == domain]
            domain_averages[domain] = subset[column].mean()
        # Now sort order by that
        #order.sort(key=lambda x: domain_averages[x], reverse=True)
        
        box_plot = seaborn.boxplot(data=df, y="domain_full", x=column, showfliers=False,
                                   fill=False, order=order, ax=ax)
        ax.set_ylabel( "" , size = 12 )
        fig.subplots_adjust(left=0.6)
        ax.set_xlabel( "Total Energy Consumption (kWh)" , size = 12 )
        box_plot.set_xticklabels(box_plot.get_xticklabels(), rotation=90)

        #fig.tight_layout()

        fig.savefig(os.path.join(images_dir, plot_dir, f"boxplot_{column}_by_domain.png"))
        fig.clf()
        matplotlib.pyplot.close()

        
def cumulative_time_plots(df):
    # Plotting the sum of different columns over time
    columns = [
        "sum_power",
        "node_hours",
        "max_power",
        "mean_power",
        "diff_power",
        "rsm_power",
        "max_load",
        "mean_load",
        "max_mem",
        "mean_mem",
    ]

    # Grouping the data into day-long chunks
    df["date"] = pandas.to_datetime(df["start_timestamp"]).dt.date

    # We can also look at month-long chunks
    df["month"] = pandas.to_datetime(df["start_timestamp"]).dt.to_period("M").dt.to_timestamp()
    
    # Plotting the sum of each column over time
    for column in columns:
        fig, ax = matplotlib.pyplot.subplots(figsize=(6, 4.5))
        # Sort the x axis by month
        df = df.sort_values(by="month")
        bar_plot = seaborn.barplot(data=df, x="month", y=column, ax=ax)# hue="user_category")

        w = 6
        h = 2
        fig.set_size_inches(w,h)
        ax.set_xlabel( "" , size = 12 )
        ax.set_title( column.replace("_", " ").title() , size = 12 )

        # Removing x axis ticks
        #ax.set_xticks([])
        # Angling x axis labels
        bar_plot.set_xticklabels(bar_plot.get_xticklabels(), rotation=45)

        # Setting the x tick labels to be month-year
        labels = [item.get_text() for item in bar_plot.get_xticklabels()]
        new_labels = [pandas.to_datetime(label).strftime("%b %Y") for label in labels]
        bar_plot.set_xticklabels(new_labels, rotation=45)

        fig.tight_layout()

        fig.savefig(os.path.join(images_dir, plot_dir, f"cumulative_bar_{column}.png"))
        fig.clf()
        matplotlib.pyplot.close()
        



def categorize_and_plot_users(df):
    # Categorizing users into "low" and "high" based on average max load
    # If the average max_load for a user is above the 75th percentile, they are "high"
    
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

    # Grouping the data into day-long chunks
    df["date"] = pandas.to_datetime(df["start_timestamp"]).dt.date

    df["month"] = pandas.to_datetime(df["start_timestamp"]).dt.to_period("M").dt.to_timestamp()

    # Sort the x axis by month
    df = df.sort_values(by="month")
    
    # Plotting each column as a box plot by user category
    for column in columns:
        fig, ax = matplotlib.pyplot.subplots(figsize=(6, 4.5))
        box_plot = seaborn.boxplot(data=df, x="month", y=column, showfliers=False,
                                   fill=False, ax=ax, hue="user_category")

        w = 6
        h = 3
        fig.set_size_inches(w,h)
        ax.set_ylabel( "" , size = 12 )
        ax.set_title( column.replace("_", " ").title() , size = 12 )

        # Setting the x tick labels to be month-year
        labels = [item.get_text() for item in box_plot.get_xticklabels()]
        new_labels = [pandas.to_datetime(label).strftime("%b %Y") for label in labels]
        box_plot.set_xticklabels(new_labels, rotation=45)

        # Removing x axis ticks
        #ax.set_xticks([])
        # Angling x axis labels
        box_plot.set_xticklabels(box_plot.get_xticklabels(), rotation=45)
        # Pad the plot so we can see the labels
        fig.tight_layout()

        # Removing legend
        ax.legend_.remove()

        fig.savefig(os.path.join(images_dir, plot_dir, f"boxplot_{column}_by_user_category.png"))
        fig.clf()
        matplotlib.pyplot.close()

    # Now doing the same by user_mem_category
    for column in columns:
        fig, ax = matplotlib.pyplot.subplots(figsize=(6, 4.5))
        box_plot = seaborn.boxplot(data=df, x="month", y=column, showfliers=False,
                                   fill=False, ax=ax, hue="user_mem_category")

        w = 6
        h = 3
        fig.set_size_inches(w,h)
        ax.set_ylabel( "" , size = 12 )
        ax.set_title( column.replace("_", " ").title() , size = 12 )

        # Setting the x tick labels to be month-year
        labels = [item.get_text() for item in box_plot.get_xticklabels()]
        new_labels = [pandas.to_datetime(label).strftime("%b %Y") for label in labels]
        box_plot.set_xticklabels(new_labels, rotation=45)

        # Angling x axis labels
        box_plot.set_xticklabels(box_plot.get_xticklabels(), rotation=45)

        # Removing x axis ticks
        #ax.set_xticks([])

        fig.tight_layout()

        fig.savefig(os.path.join(images_dir, plot_dir, f"boxplot_{column}_by_user_mem_category.png"))
        fig.clf()
        matplotlib.pyplot.close()

    # Finally doing the same without categories at all, just to see the overall distribution
    for column in columns:
        fig, ax = matplotlib.pyplot.subplots(figsize=(6, 4.5))
        box_plot = seaborn.boxplot(data=df, x="month", y=column, showfliers=False,
                                   fill=False, ax=ax)

        w = 6
        h = 3
        fig.set_size_inches(w,h)
        ax.set_ylabel( "" , size = 12 )
        ax.set_title( column.replace("_", " ").title() , size = 12 )

        # Setting the x tick labels to be month-year
        labels = [item.get_text() for item in box_plot.get_xticklabels()]
        new_labels = [pandas.to_datetime(label).strftime("%b %Y") for label in labels]
        box_plot.set_xticklabels(new_labels, rotation=45)

        # Angling x axis labels
        box_plot.set_xticklabels(box_plot.get_xticklabels(), rotation=45)

        # Removing x axis ticks
        #ax.set_xticks([])

        fig.tight_layout()

        fig.savefig(os.path.join(images_dir, plot_dir, f"boxplot_{column}_overall.png"))
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
    g = seaborn.PairGrid(df, hue="user_category",
                            vars=["max_power", "mean_power", "max_temp", "rsm_power", "diff_power", 
                                  "stddev_power", "power_edges", "mean_duration_between_power_edges",
                                  "sum_power"],
                            diag_sharey=False)
    g.map_upper(seaborn.scatterplot, s=15)
    g.map_lower(seaborn.kdeplot)
    g.map_diag(seaborn.kdeplot, lw=2)
    fig = g.fig
    fig.savefig(os.path.join(images_dir, plot_dir, f"pairgrid_example.png"))
    fig.clf()
    matplotlib.pyplot.close()


if __name__ == "__main__":
    #df = pandas.read_pickle("polaris_april_sums_new_new.pkl.zst")
    df = pandas.read_pickle("~/polaris_sums/polaris_24_25.pkl.zst")#2024.pkl.zst")
    df = join_domains_by_project(df, "../../data/project_to_science_polaris.csv")
    df["system"] = "Polaris"

    # Drop all temperatures below 10C as erroneous
    df = df[df["max_temp"] >= 10]

    # Let's just try dropping rsm_power outliers
    threshold = df["rsm_power"].quantile(0.99)
    df = df[df["rsm_power"] <= threshold]

    # Let's normalize the power_edges column by the number of nodes
    df["power_edges"] = df["power_edges"] / df["node_hours"]

    df["class"] = df["queue_name"].apply(combine_queues)

    user_avg_max_load = df.groupby("username")["max_load"].mean()
    threshold = user_avg_max_load.quantile(0.75)
    high_users = user_avg_max_load[user_avg_max_load > threshold].index.tolist()
    df["user_category"] = df["username"].apply(lambda x: "high" if x in high_users else "low")

    # now make a second category that is max_mem based
    user_avg_max_mem = df.groupby("username")["max_mem"].mean()
    threshold_mem = user_avg_max_mem.quantile(0.75)
    high_mem_users = user_avg_max_mem[user_avg_max_mem > threshold_mem].index.tolist()
    df["user_mem_category"] = df["username"].apply(lambda x: "high" if x in high_mem_users else "low")
        
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
    #pairgrid_plots(reduced_df)
    categorize_and_plot_users(reduced_df)
    cumulative_time_plots(reduced_df)
