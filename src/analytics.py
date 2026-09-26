"""
Scientific Analysis Module.

Generates visualizations and statistical summaries from the experiment dataset.
Focuses on evaluating the trade-off between Security (ASR) and Functionality (FBR).
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Configure scientific plotting style
sns.set_theme(style="whitegrid")
plt.rcParams.update({'font.size': 12, 'figure.figsize': (10, 6)})

SCALES = ["Small", "Medium", "Large"]
SEEDS = [100, 200, 300]

def load_data(path):
    if not Path(path).exists():
        raise FileNotFoundError(f"File not found: {path}. Run src/run_experiment.py first.")
    return pd.read_csv(path)


def plot_noise_fbr():
    """
    How does Noise Level impact False Block Rate (FBR)?
    We expect FBR to stay low until a breaking point.
    """
    for seed in SEEDS:
        plt.figure()
        for scale in SCALES:
            df = load_data(Path(f"reports/{seed}/scale_merged_metrics({scale.lower()}).csv"))
            sns.lineplot(data=df, x="noise_scale", y="FBR", marker="o", label=scale)

        plt.title(f"Impact of Noise on False Block Rate (FBR)\n(Seed={seed})")
        plt.ylabel("False Block Rate (FBR)")
        plt.xlabel("Noise Scale")
        plt.legend(title="Scale of the Network")
        plt.savefig(f"reports/{seed}/noise_fbr.png", dpi=300)
        plt.close()
        print("Generated: noise_fbr.png")

def plot_noise_w_asr():
    """
    How does Noise Level impact Weighted ASR?
    We expect ASR to stay high until a breaking point.
    """
    for seed in SEEDS:
        plt.figure()
        for scale in SCALES:
            df = load_data(Path(f"reports/{seed}/scale_merged_metrics({scale.lower()}).csv"))
            sns.lineplot(data=df, x="noise_scale", y="wASR", marker="o", label=scale)

        plt.title(f"Impact of Noise on Weighted ASR\n(Seed={seed})")
        plt.ylabel("Weighted ASR (Security)")
        plt.xlabel("Noise Scale (Injection Intensity)")
        plt.legend(title="Scale of the Network")
        plt.savefig(f"reports/{seed}/noise_w_asr.png", dpi=300)
        plt.close()
        print("Generated: noise_w_asr.png")


def plot_noise_lmi_reduction():
    """
    Does the algorithm effectively reduce LMI compared to noise?
    """
    for seed in SEEDS:
        plt.figure()
        for scale in SCALES:
            df = load_data(Path(f"reports/{seed}/scale_merged_metrics({scale.lower()}).csv"))
            sns.lineplot(data=df, x="noise_scale", y="wLMI_reduction", marker="o", label=scale)

        plt.title(f"Impact of Noise on Weighted LMI Reduction\n(Seed={seed})")
        plt.ylabel("Weighted LMI Reduction")
        plt.xlabel("Noise Scale")
        plt.legend(title="Scale of the Network")
        plt.savefig(f"reports/{seed}/noise_lmi_reduction.png", dpi=300)
        plt.close()
        print("Generated: noise_lmi_reduction.png")

def plot_fbr_vs_asr():
    """
    Trade-off between security (wASR) and functionality (FBR) per network scale.
    """
    for seed in SEEDS:
        fig, axes = plt.subplots(1, len(SCALES), figsize=(16, 5.5), sharey=True)
        fig.suptitle(f"Trade-off between Weighted ASR and FBR\n(Seed={seed})", fontsize=16)

        for i, scale in enumerate(SCALES):
            df = load_data(Path(f"reports/{seed}/scale_merged_metrics({scale.lower()}).csv"))
            ax = axes[i]

            sns.scatterplot(
                data=df, x="wASR", y="FBR",
                hue="noise_scale", palette="coolwarm",
                s=120, ax=ax,
            )

            ax.legend(title="Noise scale")
            ax.set_ylabel("False Block Rate (FBR)")
            n_devices = int(df["N_devices"].iloc[0])
            ax.set_title(f"{scale} Network ({n_devices} devices)")
            ax.set_xlabel("Weighted ASR (Security)")

        plt.tight_layout()
        plt.savefig(f"reports/{seed}/fbr_vs_asr.png", dpi=300)
        plt.close()
        print("Generated: fbr_vs_asr.png")


def plot_scale_false_block_rate():
    """
    How does the scale and noise level impact the False Block Rate (FBR)?
    We expect larger networks to have higher FBR, especially at higher noise levels.
    """
    for seed in SEEDS:
        fig, axes = plt.subplots(1, len(SCALES), figsize=(16, 5.5), sharey=True)
        fig.suptitle(f"Impact of Network Size and Noise Level on False Block Rate (FBR)\n(Seed={seed})", fontsize=16)

        for i, scale in enumerate(SCALES):
            df = load_data(Path(f"reports/{seed}/scale_merged_metrics({scale.lower()}).csv"))
            ax = axes[i]

            _create_barplot(df, ax, x_metric="E_total", y_metric="FBR", hue="noise_scale")

            ax.legend(title="Noise scale")
            ax.set_ylabel("False Block Rate (FBR)")
            ax.set_xlabel("Number of Edges in the Network")
            n_devices = int(df["N_devices"].iloc[0])
            ax.set_title(f"{scale} Network ({n_devices} devices)")

        plt.tight_layout()
        plt.savefig(f"reports/{seed}/scale_fbr.png", dpi=300)
        plt.close()
        print("Generated: scale_fbr.png")

def plot_scale_weighted_asr():
    """
    How does the scale and noise level impact the Weighted ASR?
    We expect larger networks to have lower ASR, especially at higher noise levels.
    """
    for seed in SEEDS:
        fig, axes = plt.subplots(1, len(SCALES), figsize=(16, 5.5), sharey=True)
        fig.suptitle(f"Impact of Network Size and Noise Level on Weighted ASR\n(Seed={seed})", fontsize=16)

        for i, scale in enumerate(SCALES):
            df = load_data(Path(f"reports/{seed}/scale_merged_metrics({scale.lower()}).csv"))

            ax = axes[i]

            _create_barplot(df, ax, x_metric="E_total", y_metric="wASR", hue="noise_scale")

            ax.legend(title="Noise scale")
            ax.set_ylabel("Weighted ASR (Security)")
            ax.set_xlabel("Number of Edges in the Network")
            n_devices = int(df["N_devices"].iloc[0])
            ax.set_title(f"{scale} Network ({n_devices} devices)")

        plt.tight_layout()
        plt.savefig(f"reports/{seed}/scale_weighted_asr.png", dpi=300)
        plt.close()
        print("Generated: scale_weighted_asr.png")

def plot_scale_weighted_lmi_reduction():
    """
    How does the scale and noise level impact the Weighted LMI Reduction?
    We expect larger networks to have higher LMI, especially at higher noise levels.
    """
    for seed in SEEDS:
        fig, axes = plt.subplots(1, len(SCALES), figsize=(16, 5.5), sharey=True)
        fig.suptitle(f"Impact of Network Size and Noise Level on Weighted LMI Reduction\n(Seed={seed})", fontsize=16)

        for i, scale in enumerate(SCALES):
            df = load_data(Path(f"reports/{seed}/scale_merged_metrics({scale.lower()}).csv"))

            ax = axes[i]

            _create_barplot(df, ax, x_metric="E_total", y_metric="wLMI_reduction", hue="noise_scale")

            ax.legend(title="Noise scale")
            ax.set_ylabel("Weighted LMI Reduction")
            ax.set_xlabel("Number of Edges in the Network")
            n_devices = int(df["N_devices"].iloc[0])
            ax.set_title(f"{scale} Network ({n_devices} devices)")

        plt.tight_layout()
        plt.savefig(f"reports/{seed}/scale_weighted_lmi_reduction.png", dpi=300)
        plt.close()
        print("Generated: scale_weighted_lmi_reduction.png")


def _create_barplot(
    df: pd.DataFrame,
    ax: plt.Axes,
    x_metric: str,
    y_metric: str,
    hue: str = None,
) -> None:
    """
    Helper function to create a bar plot with annotations.
    """
    kwargs = {
        "data": df,
        "x": x_metric,
        "y": y_metric,
        "ax": ax,
        "palette": "coolwarm",
    }
    if hue:
        kwargs["hue"] = hue

    sns.barplot(**kwargs)

    for container in ax.containers:
        ax.bar_label(container, label_type='center', fontweight='bold', padding=2)

    ax.set_yticks([0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])


if __name__ == "__main__":
    plot_noise_fbr()
    plot_noise_w_asr()
    plot_noise_lmi_reduction()
    plot_scale_false_block_rate()
    plot_scale_weighted_asr()
    plot_scale_weighted_lmi_reduction()
    plot_fbr_vs_asr()