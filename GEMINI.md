# Oregon Network Analysis Project

## Directory Overview
This directory contains datasets and simulation results focused on network topology and epidemic modeling. It specifically focuses on Autonomous System (AS) peering information and virus spread simulations on networks.

## Key Files
- **oregon1_010331.txt**: A graph dataset representing undirected AS peering information.
  - **Source**: Inferred from Oregon route-views BGP data (March 31, 2001).
  - **Stats**: 10,670 nodes and 22,002 edges.
  - **Format**: Edge list (`FromNodeId`, `ToNodeId`).
- **vone_300_6_3.csv**: Exported world data from a [NetLogo](https://ccl.northwestern.edu/netlogo/) simulation.
  - **Simulation**: "Virus on a Network Extended" (version 6.3.0).
  - **Contents**: Full snapshot of the simulation state, including global variables, agents (turtles), grid patches, and links.
- **convert_to_netlogo.py**: A Python script to convert edge-list graphs (like `oregon1_010331.txt`) into NetLogo `export-world` CSV format.
- **oregon_export.csv**: The result of running `convert_to_netlogo.py` on the Oregon dataset. This file can be imported into NetLogo using `import-world`.

## Usage
The contents of this directory are designed for:
1. **Network Research**: Analyzing the structure and properties of the AS peering graph.
2. **Epidemic Modeling**: Studying how viruses or information spread across large-scale networks using simulation data.
3. **Data Visualization**: Using the node/edge data and simulation snapshots to visualize network behavior.
