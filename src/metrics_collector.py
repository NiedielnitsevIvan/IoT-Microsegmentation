import pandas as pd
from pathlib import Path

def load_data(path):
    if not Path(path).exists():
        raise FileNotFoundError(f"File not found: {path}")
    return pd.read_csv(path)

SEEDS = [100, 200, 300]
SCALES = ["small", "medium", "large"]
NOISE_SCALES = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
HEADER = [
    "scale",
    "noise_scale",
    "E_total",
    "E_policy",
    "ASR",
    "wASR",
    "LMI_full",
    "LMI_policy",
    "wLMI_full",
    "wLMI_policy",
    "LMI_reduction",
    "wLMI_reduction",
    "FB",
    "FBR",
    "PC",
    "PCR",
    "N_devices",
]

def merge_metrics_by_noise():
    """
    For each seed and noise level, concatenates the metrics of all scales
    into one table (one row per scale). No averaging is done here — aggregation
    across seeds happens in scientific_plotting.py.
    """
    for noise_scale in NOISE_SCALES:
        stringified_noise_scale = f"{noise_scale:.2f}".replace('.', '_')
        for seed in SEEDS:
            out_filepath = Path(f"reports/{seed}/noise_merged_metrics_{stringified_noise_scale}.csv")
            out_df = pd.DataFrame(columns=HEADER)

            for scale in SCALES:
                out_dir = f"reports/{seed}/{scale}/"
                df = load_data(Path(out_dir + f"metrics_{stringified_noise_scale}.csv"))
                _df = pd.DataFrame([{"scale": scale, "noise_scale": noise_scale}])

                out_df = pd.concat([out_df, df.combine_first(_df)])

            out_df.to_csv(out_filepath, index=False)


def merge_metrics_by_scale():
    """
    For each seed and scale, concatenates the metrics of all noise levels
    into one table (one row per noise level). No averaging is done here —
    aggregation across seeds happens in scientific_plotting.py.
    """
    for scale in SCALES:
        for seed in SEEDS:
            out_filepath = Path(f"reports/{seed}/scale_merged_metrics({scale}).csv")
            out_df = pd.DataFrame(columns=HEADER)

            for noise_scale in NOISE_SCALES:
                stringified_noise_scale = f"{noise_scale:.2f}".replace('.', '_')
                out_dir = f"reports/{seed}/{scale}/"
                df = load_data(Path(out_dir + f"metrics_{stringified_noise_scale}.csv"))
                _df = pd.DataFrame([{"scale": scale, "noise_scale": noise_scale}])

                out_df = pd.concat([out_df, df.combine_first(_df)])

            out_df.to_csv(out_filepath, index=False)

if __name__ == "__main__":
    merge_metrics_by_noise()
    merge_metrics_by_scale()