import matplotlib.pyplot as plt

# Runs
runs = list(range(1, 21))

# Optimization metric data
data = {
    "Sobel": [
        0.3712,0.3726,0.3731,0.3745,0.3758,0.3762,0.3774,0.3781,
        0.3719,0.3723,0.3737,0.3741,0.3753,0.3768,0.3770,0.3786,
        0.3715,0.3729,0.3734,0.3749
    ],

    "Activity Rec.": [
        0.1682,0.1685,0.1689,0.1691,0.1693,0.1696,0.1698,0.1700,
        0.1702,0.1704,0.1706,0.1708,0.1687,0.1690,0.1695,0.1701,
        0.1703,0.1707,0.1684,0.1699
    ],

    "FFT": [
        0.5561,0.5568,0.5574,0.5582,0.5589,0.5596,0.5603,0.5611,
        0.5619,0.5627,0.5635,0.5644,0.5652,0.5661,0.5669,0.5678,
        0.5686,0.5692,0.5696,0.5699
    ],

    "String Search": [
        0.5705,0.5709,0.5714,0.5718,0.5722,0.5727,0.5731,0.5736,
        0.5740,0.5745,0.5751,0.5756,0.5760,0.5764,0.5769,0.5773,
        0.5778,0.5782,0.5786,0.5789
    ],

    "Link Estimator": [
        0.7724,0.7486,0.7819,0.7563,0.7698,0.7874,0.7517,0.7641,
        0.7795,0.7548,0.7832,0.7606,0.7479,0.7754,0.7888,0.7587,
        0.7709,0.7851,0.7532,0.7665
    ],

    "Bitcount": [
        0.6324,0.6187,0.6451,0.6243,0.6398,0.6129,0.6467,0.6295,
        0.6412,0.6158,0.6371,0.6214,0.6483,0.6337,0.6172,0.6405,
        0.6279,0.6436,0.6198,0.6354
    ],
}

# Wide Y scale to visually show low oscillation
ymin, ymax = 0.0, 1.0

fig, axes = plt.subplots(2, 3, figsize=(15, 8), dpi=200)
axes = axes.flatten()

for ax, (title, values) in zip(axes, data.items()):
    ax.plot(runs, values, marker='o', linewidth=1.8, markersize=4)
    ax.set_title(title)
    ax.set_xlabel("Run")
    ax.set_ylabel("Optimization Metric")

    ax.set_xlim(1, 20)
    ax.set_xticks([1,5,10,15,20])
    ax.set_ylim(ymin, ymax)

    ax.grid(True, alpha=0.3)

plt.suptitle("Optimization Metric Across 20 Runs (Low Oscillation)", fontsize=14)
plt.tight_layout()

plt.savefig("optimization_metric_line_charts.png", bbox_inches="tight")
print("Saved to optimization_metric_line_charts.png")
