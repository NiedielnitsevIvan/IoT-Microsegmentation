import argparse

from constants import DEFAULT_SEED
from gen_topology import TopologyGenerator


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

    parser.add_argument("--topology_out", type=str, default=None,
                        help="Output path for generated topology JSON")

    args = parser.parse_args()
    stringified_noise = f"{args.noise_scale:.2f}".replace('.', '_')

    topology_out = args.topology_out or f"data/topology_{args.seed}_{stringified_noise}.json"

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
