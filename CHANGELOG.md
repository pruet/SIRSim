# Changelog

All notable changes to the Oregon Network Analysis simulation and conversion codebase are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.6.0] - 2026-05-28

### Added
- **Parameterized Suppression Control**: Added `--suppression-ratio` and `--suppression-percentage` CLI arguments and simulator configurations. These allow users to dynamically control the percentage of nodes/edges targeted and the exact percentage of weight reduction (from 0% to 100%) applied across all suppression strategies instead of relying on hardcoded defaults.

---

## [2.5.0] - 2026-05-28

### Added
- **Pruet's Reliable Cluster Edge Suppression Strategy**: Added `reliable_cluster_edge_suppression` strategy in `suppression_strategies.py`. Groups nodes into robust/reliable clusters (communities) using weighted Louvain community detection on probabilistic link weights, then suppresses the top highest-weight inter-cluster bridging edges by 90% at setup to prevent epidemic spread across communities.

---

## [2.4.0] - 2026-05-28

### Changed
- **Strategies Module Cleanup**: Removed all standard reference algorithms from `suppression_strategies.py` (Random Vaccination, High-Degree Vaccination, Acquaintance Vaccination, Infected Quarantine, Social Distancing, and Local Caution) to keep strictly the Baseline simulation along with the three newly requested strategies: NetShield, Centrality Edge Suppression, and Greedy Edge-Weight Suppression.

---

## [2.3.0] - 2026-05-28

### Added
- **Centrality Edge Suppression Strategy**: Added `centrality_edge_suppression` in `suppression_strategies.py`. Identifies top central nodes using eigenvector centrality and randomly scales down adjacent edge weights by a random factor in `[0.1, 0.5]` at setup.
- **Greedy Edge-Weight Suppression Strategy**: Added `greedy_edge_weight_suppression` in `suppression_strategies.py`. Collects unique undirected links, sorts them in descending order of transmission probability, and suppresses the top fraction of highest-weight edges by 90% at setup.

---

## [2.2.0] - 2026-05-28

### Added
- **Chen's NetShield Immunization Strategy**: Integrated Chen's greedy spectral node immunization algorithm (`netshield_immunization`) in `suppression_strategies.py`. Uses sparse power iteration to calculate principal eigenvector centrality in $O(M)$ time and greedily maximizes Shield-value to identify critical network hubs while avoiding clustering.
- **Edge-Weight Suppression Strategies**: Added two new strategies focusing on edge weight manipulation: `social_distancing` (static 50% link weight reduction) and `local_caution` (dynamic 80% link weight reduction for nodes adjacent to active infections).

---

## [2.1.0] - 2026-05-28

### Added
- **Decoupled Strategy Module**: Separated all suppression strategies and the decorator-based registry from `sir_simulator.py` into a dedicated, modular `suppression_strategies.py` file. This allows users to add and edit strategies independently while keeping the core simulator engine unchanged.

---

## [2.0.0] - 2026-05-28

### Added
- **Suppression Strategy Framework**: Overhauled the simulator with a decorator-based strategy registry (`@register_strategy`) supporting pre-simulation (`setup`) and mid-simulation (`step`) lifecycle hooks.
- **Reference Strategies**: Implemented four suppression algorithms: Random Vaccination, High-Degree Vaccination, Acquaintance Vaccination, and Dynamic Infected Quarantine.
- **Identical Outbreak Testing**: Pre-generates exact randomized outbreaks per Monte Carlo run to evaluate and compare all selected strategies under identical initial conditions.
- **Comparative Summaries & Charting**: Outputs a comparative evaluation metrics table in the console and saves a multi-strategy comparative curve plot (`sir_comparison_curves.png`).
- **Suppression Customization CLI**: Added `--vaccination-fraction` and `--quarantine-chance` arguments to configure strategy parameters dynamically.

---

## [1.3.0] - 2026-05-28

### Added
- **Restored Time Alignment Mechanism (Method 1)**: Brought back the original time alignment mechanism as the default averaging mode for multi-run simulations. Shorter runs that terminate early due to virus extinction are dynamically padded with their final steady state, matching the length of the longest active run.
- **Configurable Alignment Modes**: Added the new command-line argument `-a` / `--alignment` to toggle between the restored `align` (Method 1, default) and `truncate` (Method 2) multi-run averaging strategies.

---

## [1.2.0] - 2026-05-28

### Added
- **Monte Carlo Multi-Run Simulation**: Implemented independent parallel execution loops (`-n` / `--runs` argument, default `50` runs) with dynamic random outbreak initialization.
- **Shortest-Run Truncation (Method 2)**: Added an automatic truncation mechanism that safely terminates averaging at the very first step where any simulation run ends early (due to virus death), ensuring clean, non-skewed metrics.
- **Edge Weight Parsing**: Updated CSV reader to parse the `weight` column in the `LINKS` section of NetLogo export files, allowing edge-specific transmission probabilities.
- **Virus Check Logic & Timers**: Added support for `virus-check-frequency` (defined in `GLOBALS`) and individual `virus-check-timer` (defined per turtle). Recovery and resistance checks are now executed strictly when a node's check timer is `0`.

### Changed
- **Execution Order Realignment**: Re-aligned step sequence to match NetLogo's loop (`go` / `do-virus-checks` / `spread-virus` sequence) so that check timers increment, transmission utilizes edge weights, and recovery checks include newly infected nodes.
- **Default Time Limit**: Adjusted the default simulation limit `-t` / `--steps` from `100` to `500` steps to match NetLogo's default time limit.
- **Default Resistance Chance**: Changed the fallback `gain-resistance-chance` from `100.0` to `5.0` to match NetLogo's default model slider and experiment values (5%).

---

## [1.1.0] - 2026-05-28

### Added
- **Dynamic Parameter Arguments**: Enabled configuring `virus_spread_chance`, `recovery_chance`, `gain_resistance_chance`, and `virus_check_frequency` via function arguments in `convert_to_netlogo.py` rather than hardcoding.
- **Randomized Edge Weights**: Changed edge weight generation in the graph converter from a static `1` to `random.uniform(0, virus_spread_chance)` to match NetLogo's native spatially clustered network generator.
- **Distributed Node Timers**: Initialized `virus-check-timer` for all turtles to a random integer in `[0, virus-check-frequency - 1]` to distribute scan timings uniformly at setup.

---

## [1.0.0] - 2026-05-28

### Added
- **Initial Python Simulator**: Created the initial `sir_simulator.py` script featuring basic SIR simulation, CSV parsing, and simple matplotlib plotting.
- **Initial Graph Converter**: Created the initial `convert_to_netlogo.py` script to map autonomous system edge list graphs into NetLogo `export-world` CSV files.
