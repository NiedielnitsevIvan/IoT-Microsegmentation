import argparse

from constants import DEFAULT_SEED
from gen_topology import TopologyGenerator
from metrics import MetricsAnalyzer
from plot_topology import TopologyVisualizer
from policy_synthesizer import PolicySynthesizer

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Pipeline: topology -> required flows -> baseline policy -> metrics"
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED,
                        help="Random seed for reproducibility")
    parser.add_argument("--n_sensors", type=int, default=20,
                        help="Number of sensors")
    parser.add_argument("--n_cameras", type=int, default=8,
                        help="Number of cameras")
    parser.add_argument("--n_actuators", type=int, default=8,
                        help="Number of actuators")
    parser.add_argument("--n_hubs", type=int, default=3,
                        help="Number of hubs")
    parser.add_argument("--n_controllers", type=int, default=3,
                        help="Number of controllers")
    parser.add_argument("--n_nvr", type=int, default=2,
                        help="Number of nvr")
    parser.add_argument("--n_gateways", type=int, default=1,
                        help="Number of gateways")
    parser.add_argument("--n_cloud", type=int, default=1,
                        help="Number of clouds")

    parser.add_argument("--noise_scale", type=float, default=1.0,
                        help="Scale for role-pair noise (0 = only functional core)")
    parser.add_argument("--n_clusters", default=4, type=int,
                        help="Number of clusters (rooms/zones) for spectral policy synthesis")
    parser.add_argument("--whitelist_roles", default=None, nargs="*",
                        help="Roles to whitelist in policy synthesis that should be opened to inter-cluster communication")

    parser.add_argument("--topology_out", type=str, default=None,
                        help="Output path for generated topology JSON")
    parser.add_argument("--policy_out", type=str, default=None,
                        help="Output path for synthesized policy JSON")
    parser.add_argument("--metrics_out", type=str, default=None,
                        help="Output path for computed metrics CSV")

    args = parser.parse_args()
    stringified_noise = f"{args.noise_scale:.2f}".replace('.', '_')

    topology_out = args.topology_out or f"data/{args.seed}/topology_{stringified_noise}.json"
    topology_plot_out = topology_out.replace('.json', '.png')
    policy_out = args.policy_out or f"data/{args.seed}/policy_synthesis_{stringified_noise}.csv"
    metrics_out = args.metrics_out or f"reports/{args.seed}/metrics_{stringified_noise}.csv"

    topology_generator = TopologyGenerator(
        topology_out,
        seed=args.seed,
        n_sensors=args.n_sensors,
        n_cameras=args.n_cameras,
        n_actuators=args.n_actuators,
        n_hubs=args.n_hubs,
        n_controllers=args.n_controllers,
        n_nvr=args.n_nvr,
        n_gateways=args.n_gateways,
        n_cloud=args.n_cloud,
        n_zones=args.n_clusters,
        noise_scale=args.noise_scale,
    )
    topology = topology_generator.generate_topology()
    policy_synthesizer = PolicySynthesizer(
        policy_out,
        topo_json=topology,
        seed=args.seed,
        noise_scale=args.noise_scale,
        n_clusters=args.n_clusters,
        whitelist_roles=args.whitelist_roles,
    )
    edges = policy_synthesizer.synthesize()

    viz = TopologyVisualizer(topology_out, policy_out, args.seed)
    viz.create_plot(
        out_path=topology_plot_out,
        width=2400,
        height=1600,
        with_labels=True,
    )

    metrics_analyzer = MetricsAnalyzer(
        topo_path=topology_out,
        policy_path=policy_out,
        out_filepath=metrics_out,
    )
    metrics = metrics_analyzer.compute_all_metrics()
    print("Computed Metrics:")
    for k, v in metrics.items():
        print(f" - {k}: {v}")
