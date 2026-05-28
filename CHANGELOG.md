# Changelog

All notable changes to the Oregon Network Analysis simulation and conversion codebase are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
