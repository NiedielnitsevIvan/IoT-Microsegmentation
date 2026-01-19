from pathlib import Path
from typing import Dict

import matplotlib.pyplot as plt

def generate_report_graph(
    metrics: Dict,
    seed: int,
    noise_scale: float,
    out_path: str,
):
    """
    Generate a graph with ASR, Weighted ASR, LMI reduction and Heuristic FBR from the metrics dictionary.
    """
    out_path = Path(out_path)

    plt.figure()

    plt.bar(
        ["ASR", "Weighted ASR", "LMI Reduction", "Heuristic FBR"],
        [metrics["ASR"], metrics["wASR"], metrics["LMI_reduction"], metrics["FBR"]]
    )
    plt.ylim(0, 1.0)
    plt.title(f"ASR & LMI reduction (seed={seed}, noise={noise_scale})")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()

    print(f"Metrics graph saved: {out_path}")
