# IoT Micro-Segmentation

Automated micro-segmentation of IoT networks for Zero Trust architectures: **spectral clustering + role-based heuristic pruning**, with a synthetic topology generator and a suite of weighted security metrics.

Companion code for the paper:

> Niedielnitsev, I., & Antipov, I. (2026). Micro-Segmentation of IoT Networks in the Zero Trust Architecture. *Cybersecurity: Education, Science, Technique*, 2(34), 417–429. https://doi.org/10.28925/2663-4023.2026.34.1336

## Motivation

Large heterogeneous IoT deployments accumulate redundant network connectivity that expands the attack surface and enables lateral movement after a single node is compromised. Manually maintaining access policies for hundreds of devices is infeasible. This project automates policy synthesis: it discovers functional communities in the network graph and prunes structurally dangerous edges, producing compact allow-list policies aligned with Zero Trust principles.

## Pipeline

1. **Topology generation** — `src/gen_topology.py`
   Builds a role-aware IoT graph (sensors, cameras, actuators, hubs, NVRs, controllers, gateways, cloud) with a deterministic functional core (protocol-driven edges: MQTT, RTSP, CoAP, HTTP/HTTPS) and controlled noise: preferential attachment ("rich get richer") + zone affinity, scaled by noise intensity σ.

2. **Policy synthesis** — `src/policy_synthesizer.py`
   Spectral clustering of the adjacency graph (scikit-learn, `discretize` label assignment) with a gateway/cloud whitelist, followed by heuristic pruning rules: peer-to-peer isolation at the edge level, blocking direct cloud access from low levels, removal of transitive shortcut jumps, and rejection of invalid downstream commands.

3. **Metrics** — `src/metrics.py`
   ASR / wASR (weighted attack-surface reduction), LMI / wLMI (weighted lateral-movement index) with reduction values, FB / FBR (false blocks against the generated ground truth), PC (policy complexity), PCR (policy compression ratio, equal to 1 − ASR). Weights are driven by per-role node criticality (`src/iot_models.py`).

4. **Experiments** — `src/run_experiment.py`
   Full grid: 3 network scales (~30 / ~330 / ~950 devices) × noise σ ∈ {0…5} × seeds {100, 200, 300}; afterwards it runs `src/metrics_collector.py` (merges per-run metrics into summary tables) and `src/analytics.py` (per-seed diagnostic plots). `src/scientific_plotting.py` renders the publication figures (mean ± 95% CI across seeds).

## Quick start

Requires Python 3.11+.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python src/run_experiment.py      # full experiment grid (topologies -> policies -> metrics -> plots)
python src/scientific_plotting.py # aggregated publication figures
```

Outputs: `data/` (generated topologies, synthesized policies, and per-run topology renders), `reports/` (per-run and merged metrics CSV, per-seed diagnostic plots), `reports/paper_figures/` (figures used in the paper).

## Key results

For large-scale networks the hybrid method reduces the weighted lateral-movement index by **72–88%** at noise intensities σ ≥ 2, keeps the false block rate at or below **≈3%** for σ ≤ 3 (≈1.5% at σ = 2), and produces compact policies (**PCR 0.71–0.83** at σ ≥ 3). See the paper for details.

## Notes and limitations

- The number of spectral clusters is set equal to the ground-truth number of zones used by the topology generator (a single `--n_clusters` argument feeds both). Automatic selection of the number of segments (e.g., via the eigengap heuristic) is future work.
- The noise intensity σ enters generation twice: it scales the per-device budget of noise-edge attempts and the acceptance probability of each attempt. Since base role-pair probabilities are capped at 0.30, the acceptance component saturates around σ ≈ 3.3, so noise growth at high σ comes mostly from the attempt budget.
- Small networks (~30 devices) are markedly more sensitive to noise due to graph sparsity; see the paper's discussion of FBR variance.

## Repository layout

| Path | Purpose |
|---|---|
| `src/main.py` | Single-run entry point: topology → policy → metrics → plots |
| `src/iot_models.py` | Device model hierarchy: roles, levels, criticality |
| `src/constants.py` | Protocol patterns and role-pair noise priors |
| `src/gen_topology.py` | Role-aware topology generator with controlled noise |
| `src/policy_synthesizer.py` | Spectral clustering + pruning rules |
| `src/metrics.py` | Security and efficiency metrics |
| `src/run_experiment.py` | Experiment grid runner |
| `src/metrics_collector.py` | Merges per-run metrics into summary tables |
| `src/scientific_plotting.py` | Publication figures (mean ± 95% CI) |
| `src/plot_topology.py`, `src/plot_metrics.py`, `src/analytics.py` | Auxiliary visualization |
| `reports/` | Metrics tables and paper figures |

## Citing

If you use this tool in your research, please cite the paper above (see `CITATION.cff`).

## Authors

- **Ivan Niedielnitsev** — PhD student, Kharkiv National University of Radio Electronics ([ORCID 0009-0004-5265-3561](https://orcid.org/0009-0004-5265-3561))
- Scientific supervisor: **Prof. Ivan Antipov**, Dr.Sc., Kharkiv National University of Radio Electronics ([ORCID 0000-0002-9754-4412](https://orcid.org/0000-0002-9754-4412))

## License

[MIT](LICENSE)
