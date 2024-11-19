"""
Module for statistics and plots about found pulses.
"""
import scipy
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

hist_colors = ("tab:orange", "red", "tab:blue", "blue")
# hist_colors = "tab:blue", "tab:orange", "blue", "red"

def fit_histo(data: pd.Series, axes, nbins, x_array, label, color=hist_colors[0]):
    """Fit a bell curve to a histogram"""
    data.hist(ax=axes, bins=nbins, density=True, label=label, alpha=0.6, color=color)

    mean, sigma = scipy.stats.norm.fit(data)
    pct = 100*sigma/mean
    fit_line = scipy.stats.norm.pdf(x_array, mean, sigma)

    print(mean, sigma, pct)

    return mean, sigma, pct, fit_line


def plot_distribution(df, binwidth=None, nbins=15, colors=hist_colors, **kwargs):
    colors = iter(hist_colors)

    title = kwargs.get("title") or "BoxcarSum distribution with Filter v2"
    xlabel= kwargs.get("xlabel") or "Summed ADC-Counts of pulse"
    columns = kwargs.get("columns") or ["Sum"]
    labels = kwargs.get("labels") or ["Peak-finding sum"]

    Max = max((max(df[column]) for column in columns))
    Min = min((min(df[column]) for column in columns))
    x_array = np.linspace(Min, Max, 1000)
    print("Full data range:", Min, Max, Max-Min)

    if binwidth is not None:
        nbins = (Max-Min) // binwidth
    else:
        binwidth = (Max-Min) // nbins

    fig, axes = plt.subplots()

    for i,column in enumerate(columns):
        data = df[column]

        min_data, max_data = min(data), max(data)
        print(f"data range {column}:", min_data, max_data, max_data-min_data)

        mean, sigma, pct, line = fit_histo(data, axes, nbins, x_array, labels[i], next(colors))

        axes.plot(
            x_array, line,
            label=f"{mean:.4} $\pm$ {sigma:.3} ({pct:.2}%)",
            color=next(colors),
            )

    #
    # todo: use OO commands
    # todo: set position relative to figure, not using data values
    # todo: return figure or something plotablew
    #
    fig.suptitle(title)
    axes.set_xlabel(xlabel)
    # fig.text(3000, 0.002, f"{df.shape[0]} Snippets\nBinwidth: {binwidth}ADC")
    fig.legend()

    return fig, binwidth
