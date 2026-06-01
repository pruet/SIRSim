# Oregon Network Analysis & Epidemic Simulation Project

## Directory Overview
This directory contains datasets, simulation engines, and results focused on network topology, community structure, and epidemic modeling. Specifically, it includes Autonomous System (AS) peering graphs and a premium probabilistic SIR simulation platform equipped with advanced network-level suppression strategies.

## Key Files
- **sir_simulator.py (v2.7.1)**: The core SIR (Susceptible-Infected-Recovered) simulation engine. Runs probabilistic, multi-run Monte Carlo simulations directly on parsed NetLogo world exports, logs detailed progression metrics, outputs comparative summary statistics, and plots premium epidemic curves (`sir_comparison_curves.png`).
- **suppression_strategies.py**: A modular strategy module housing the epidemic suppression registry (`@register_strategy`). Contains:
  1. `baseline`: Standard unsuppressed spread benchmark.
  2. `netshield_immunization`: Spectral node immunization using Chen's greedy NetShield algorithm to maximize Shield-value strictly over susceptible nodes.
  3. `centrality_edge_suppression`: Eigenvector centrality-based edge suppression.
  4. `greedy_edge_weight_suppression`: Suppresses the highest-probability transmission links globally.
  5. `reliable_cluster_edge_suppression`: A top-performing containment strategy inspired by Pruet Boonma's *“Reliable Cluster on Uncertain Multigraph”* paper. Uses the Most-Probability-First (MPF) greedy clustering algorithm to group nodes into robust clusters, then isolates them by suppressing inter-cluster bridging links using a fair total edge budget.
- **CHANGELOG.md**: Comprehensive Semantic Versioning logs documenting all features, bug fixes, and architectural cleanups from v1.0.0 through v2.7.1.
- **vone_300_6_3.csv**: Exported world data from a NetLogo "Virus on a Network Extended" simulation (300 nodes, 901 edges) used as the standard benchmark network.
- **convert_to_netlogo.py**: A converter script to map autonomous system edge-list graphs (like `oregon1_010331.txt`) into NetLogo `export-world` CSV files.
- **oregon1_010331.txt**: Undirected AS peering graph representing BGP peering data from March 31, 2001 (10,670 nodes and 22,002 edges).
- **oregon_export.csv**: The converted full Oregon BGP graph ready for NetLogo import.

## Parameterization & Configuration
All active suppression strategies are fully parameterized to allow dynamic control from the command line:
- `--suppression-ratio` (0.0 to 1.0): Percentage of nodes or edges targeted for containment (defaults to mapping onto `--vaccination-fraction`).
- `--suppression-percentage` (0.0 to 100.0): Percentage of weight/spread reduction applied to targeted elements (defaults to 90%, i.e., scaling edge weights by 0.1).

## Strictly Weighted Graph Architecture
The engine is optimized strictly for **weighted graphs**, where each edge weight represents its exact probability of transmission (spread-chance). All legacy unweighted graph fallbacks and checks have been completely removed to keep the codebase highly focused, performant, and clean.

## Usage
Run comparative simulations and save metrics:
```bash
python sir_simulator.py vone_300_6_3.csv -n 50 -c comparison_summary.csv
```
Run with custom parameters:
```bash
python sir_simulator.py vone_300_6_3.csv -n 50 --suppression-ratio 0.20 --suppression-percentage 75.0 -c comparison_summary.csv
```
