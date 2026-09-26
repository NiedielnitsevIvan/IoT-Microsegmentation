import subprocess
import sys

# ------------------------------ Experiment Configuration ------------------------------
SCALES = {
    # Small: ~30 devices (smart home / small office / lab)
    "small": {
        "n_sensors": 12,
        "n_cameras": 6,
        "n_actuators": 6,
        "n_hubs": 2,
        "n_controllers": 2,
        "n_nvr": 1,
        "n_gateways": 1,
        "n_cloud": 1,
        "n_clusters": 2,
    },
    # Medium: ~330 devices (smart building / factory etc.)
    "medium": {
        "n_sensors": 255,
        "n_cameras": 20,
        "n_actuators": 40,
        "n_hubs": 5,
        "n_controllers": 3,
        "n_nvr": 2,
        "n_gateways": 1,
        "n_cloud": 1,
        "n_clusters": 4
    },
    # Large: ~950 devices (smart city subset)
    "large": {
        "n_sensors": 600,
        "n_cameras": 200,
        "n_actuators": 60,
        "n_hubs": 20,
        "n_controllers": 25,
        "n_nvr": 40,
        "n_gateways": 5,
        "n_cloud": 1,
        "n_clusters": 12,
    },
}

NOISE_SCALES = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]  # 0 = functional flows only
SEEDS = [100, 200, 300]


def run_experiment(
    scale_name: str,
    seed: int,
    noise_scale: float,
):
    """
    Run a single experiment with given parameters.
    """
    scale_params = SCALES[scale_name]
    noise_str = f"{noise_scale:.2f}".replace('.', '_')
    topology_out = f"data/{seed}/{scale_name}/topology_{noise_str}.json"
    policy_out = f"data/{seed}/{scale_name}/policy_synthesis_{noise_str}.csv"
    metrics_out = f"reports/{seed}/{scale_name}/metrics_{noise_str}.csv"


    cmd = [
        sys.executable,
        "src/main.py",
        "--seed", str(seed),
        "--n_sensors", str(scale_params["n_sensors"]),
        "--n_cameras", str(scale_params["n_cameras"]),
        "--n_actuators", str(scale_params["n_actuators"]),
        "--n_hubs", str(scale_params["n_hubs"]),
        "--n_controllers", str(scale_params["n_controllers"]),
        "--n_nvr", str(scale_params["n_nvr"]),
        "--n_gateways", str(scale_params["n_gateways"]),
        "--n_cloud", str(scale_params["n_cloud"]),
        "--noise_scale", str(noise_scale),
        "--n_clusters", str(scale_params["n_clusters"]),
        "--topology_out", topology_out,
        "--policy_out", policy_out,
        "--metrics_out", metrics_out,
    ]

    print(f"[INFO] Running experiment: scale={scale_name}, seed={seed}, noise_scale={noise_scale}")

    run_subprocess(cmd)


def run_subprocess(cmd) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        sys.stderr.write(
            f"[ERROR] Command failed: "
            f"{' '.join(cmd)}\n"
            f"STDERR:\n"
            f"{result.stderr}\n"
        )
        raise RuntimeError("Subprocess failed")
    if result.stderr.strip():
        sys.stderr.write(result.stderr + "\n")


if __name__ == "__main__":
    for scale_name in SCALES:
        for seed in SEEDS:
            for noise_scale in NOISE_SCALES:
                run_experiment(
                    scale_name=scale_name,
                    seed=seed,
                    noise_scale=noise_scale,
                )

    collect_metrics_cmd = [
        sys.executable,
        "src/metrics_collector.py",
    ]

    run_subprocess(collect_metrics_cmd)

    create_plots_cmd = [
        sys.executable,
        "src/analytics.py",
    ]

    run_subprocess(create_plots_cmd)
