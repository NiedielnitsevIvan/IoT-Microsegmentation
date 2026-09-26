"""
Scientific Plotting Module for Research Paper.

Generates publication-ready figures for the article (Ukrainian labels).
Aggregates data across seeds: solid line = mean, shaded band = 95% CI
(computed automatically by seaborn.lineplot over the per-seed values).

Outputs (PNG 300 dpi + PDF) are written to reports/paper_figures/:
    fig1_wasr_vs_noise      - Рис. 1: wASR vs шум
    fig2_fbr_vs_noise       - Рис. 2: FBR vs шум (з порогом 5%)
    fig3_wlmi_before_after  - Рис. 3: wLMI до/після сегментації (3 масштаби)
    fig4_pcr_vs_noise       - Рис. 4: PCR vs шум
    aggregated_metrics_mean_std.csv - агрегована таблиця (mean ± std за сідами)
"""

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from pathlib import Path

# Configuration
SEEDS = [100, 200, 300]
SCALES = ["small", "medium", "large"]
SCALE_LABELS = {
    "small": "Мала (~30)",
    "medium": "Середня (~330)",
    "large": "Велика (~950)",
}
SCALE_TITLES = {
    "small": "Мала мережа (~30 пристроїв)",
    "medium": "Середня мережа (~330 пристроїв)",
    "large": "Велика мережа (~950 пристроїв)",
}
SCALE_ORDER = [SCALE_LABELS[s] for s in SCALES]
BASE_DIR = "reports"
OUTPUT_DIR = "reports/paper_figures"

# Embedded titles are OFF by default: figure captions live in the article text.
WITH_TITLES = False

X_LABEL = "Інтенсивність шуму σ"
LEGEND_TITLE = "Масштаб мережі"

# Academic style (serif with Cyrillic support)
sns.set_theme(style="whitegrid", context="paper", font_scale=1.4)
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['DejaVu Serif'],
    'lines.linewidth': 2.5,
    'axes.labelsize': 14,
    'axes.titlesize': 15,
    'xtick.labelsize': 12,
    'ytick.labelsize': 12,
    'legend.fontsize': 11,
    'figure.figsize': (8, 5),
})


def load_all_data() -> pd.DataFrame:
    """
    Loads and concatenates merged metrics from all seeds and scales.
    Derives PCR / wLMI_reduction if the columns are absent (older CSVs).
    """
    all_data = []

    for seed in SEEDS:
        for scale in SCALES:
            path = Path(f"{BASE_DIR}/{seed}/scale_merged_metrics({scale}).csv")
            if not path.exists():
                print(f"Warning: Missing file {path}")
                continue

            df = pd.read_csv(path)
            if "PCR" not in df.columns:
                df["PCR"] = df["E_policy"] / df["E_total"]
            if "wLMI_reduction" not in df.columns:
                df["wLMI_reduction"] = (
                    (1 - df["wLMI_policy"] / df["wLMI_full"])
                    .replace([np.inf, -np.inf], np.nan)
                    .fillna(0.0)
                )
            df["scale_key"] = scale
            df["Scale"] = SCALE_LABELS[scale]
            df["Seed"] = seed
            all_data.append(df)

    expected = len(SEEDS) * len(SCALES)
    if len(all_data) != expected:
        raise FileNotFoundError(
            f"Expected {expected} merged CSV files ({len(SEEDS)} seeds x {len(SCALES)} scales), "
            f"found {len(all_data)}. Run src/run_experiment.py first."
        )

    return pd.concat(all_data, ignore_index=True)


def _save(fig_name: str):
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/{fig_name}.png", dpi=300)
    plt.savefig(f"{OUTPUT_DIR}/{fig_name}.pdf")
    plt.close()
    print(f"Generated: {fig_name}")


def plot_wasr(df: pd.DataFrame):
    """
    Рис. 1. Зважене зменшення поверхні атаки (wASR) залежно від шуму.
    """
    plt.figure()
    sns.lineplot(
        data=df,
        x="noise_scale",
        y="wASR",
        hue="Scale",
        style="Scale",
        hue_order=SCALE_ORDER,
        style_order=SCALE_ORDER,
        markers=True,
        dashes=False,
        palette="viridis",
    )
    if WITH_TITLES:
        plt.title("Зважене зменшення поверхні атаки залежно від шуму")
    plt.xlabel(X_LABEL)
    plt.ylabel("Зменшення поверхні атаки (wASR)")
    plt.xlim(0, 5)
    plt.legend(title=LEGEND_TITLE)
    _save("fig1_wasr_vs_noise")


def plot_fbr(df: pd.DataFrame):
    """
    Рис. 2. Стійкість до топологічного шуму: частка хибних блокувань (FBR).
    """
    plt.figure()
    sns.lineplot(
        data=df,
        x="noise_scale",
        y="FBR",
        hue="Scale",
        style="Scale",
        hue_order=SCALE_ORDER,
        style_order=SCALE_ORDER,
        markers=True,
        dashes=False,
        palette="viridis",
    )
    plt.axhline(y=0.05, color='r', linestyle='--', alpha=0.6,
                label="Поріг прийнятності (5%)")
    if WITH_TITLES:
        plt.title("Стійкість алгоритму до топологічного шуму")
    plt.xlabel(X_LABEL)
    plt.ylabel("Частка хибних блокувань (FBR)")
    plt.xlim(0, 5)
    plt.legend(title=LEGEND_TITLE)
    _save("fig2_fbr_vs_noise")


def plot_wlmi_before_after(df: pd.DataFrame):
    """
    Рис. 3. Вплив мікросегментації на зважений індекс латерального руху (wLMI):
    базова топологія проти сегментованої, для трьох масштабів.
    """
    df_melted = df.melt(
        id_vars=["noise_scale", "Seed", "scale_key"],
        value_vars=["wLMI_full", "wLMI_policy"],
        var_name="State",
        value_name="wLMI",
    )
    df_melted["State"] = df_melted["State"].map({
        "wLMI_full": "До сегментації",
        "wLMI_policy": "Після сегментації",
    })

    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=False)

    for i, scale in enumerate(SCALES):
        ax = axes[i]
        subset = df_melted[df_melted["scale_key"] == scale]
        sns.lineplot(
            data=subset,
            x="noise_scale",
            y="wLMI",
            hue="State",
            style="State",
            hue_order=["До сегментації", "Після сегментації"],
            style_order=["До сегментації", "Після сегментації"],
            markers=True,
            palette=["gray", "tab:blue"],
            ax=ax,
            legend=(i == 2),
        )
        ax.set_title(SCALE_TITLES[scale])
        ax.set_xlabel(X_LABEL)
        ax.set_ylabel("Зважений індекс латерального руху (wLMI)" if i == 0 else "")
        ax.set_xlim(0, 5)
        ax.grid(True, alpha=0.3)

    if axes[2].legend_ is not None:
        axes[2].legend_.set_title("Стан")

    if WITH_TITLES:
        fig.suptitle("Вплив мікросегментації на ризик латерального руху", fontsize=16)
    _save("fig3_wlmi_before_after")


def plot_pcr(df: pd.DataFrame):
    """
    Рис. 4. Коефіцієнт стиснення політики (PCR) залежно від шуму.
    """
    plt.figure()
    sns.lineplot(
        data=df,
        x="noise_scale",
        y="PCR",
        hue="Scale",
        style="Scale",
        hue_order=SCALE_ORDER,
        style_order=SCALE_ORDER,
        markers=True,
        dashes=False,
        palette="viridis",
    )
    if WITH_TITLES:
        plt.title("Ефективність стиснення правил політики")
    plt.xlabel(X_LABEL)
    plt.ylabel("Коефіцієнт стиснення політики (PCR)")
    plt.xlim(0, 5)
    plt.legend(title=LEGEND_TITLE)
    _save("fig4_pcr_vs_noise")


def export_aggregated_table(df: pd.DataFrame):
    """
    Aggregated table (mean ± std across seeds) for citing exact numbers
    in the article text.
    """
    metrics = ["E_total", "E_policy", "ASR", "wASR", "LMI_full", "LMI_policy",
               "wLMI_full", "wLMI_policy", "LMI_reduction", "wLMI_reduction",
               "FB", "FBR", "PCR"]
    agg = (
        df.groupby(["scale_key", "noise_scale"])[metrics]
        .agg(["mean", "std"])
        .round(4)
    )
    agg.columns = [f"{m}_{stat}" for m, stat in agg.columns]
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    out_path = f"{OUTPUT_DIR}/aggregated_metrics_mean_std.csv"
    agg.reset_index().to_csv(out_path, index=False)
    print(f"Generated: {out_path}")


if __name__ == "__main__":
    data = load_all_data()
    plot_wasr(data)
    plot_fbr(data)
    plot_wlmi_before_after(data)
    plot_pcr(data)
    export_aggregated_table(data)
    print("All figures generated in reports /paper_figures/")
