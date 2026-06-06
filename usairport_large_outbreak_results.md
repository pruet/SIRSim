# US Airport Network Large Outbreak Simulation Results (10% Initial Infected)

Analysis of SIR epidemic suppression strategies on the real-world **US Airports Flight Network** (`usairport.csv`) when the disease starts with a large, distributed initial infected population ($i = 157$ nodes, ~10% of the network size).

---

## Simulation Parameters
- **Infection Graph**: [usairport.csv](file:///home/pruet/Development/Oregon/Datasets/usairport.csv) (1,574 Nodes, 17,215 undirected Edges)
- **Runs**: 30 Monte Carlo simulations per strategy
- **Base Seed**: **1088**
- **Initial Outbreak Size ($i$)**: **157 nodes** (`-i 157`)
- **Spread Chance ($s$)**: **10%** (`-s 10.0`)
- **Recovery Chance ($r$)**: **15%** (`-r 15.0`)
- **Edge Suppression Budget ($p$)**: **30%** (`-p 0.3`)
- **Suppression Percentage ($P$)**: **30%** (`-P 30.0`)

## Performance Summary Table

| Strategy | Peak Infected (Qty) | Peak Infected (%) | Peak Tick | Final Susceptible (%) | Run Time (s) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Netshield Edge Suppression** | **615.37** | **39.10%** | **13** | **54.84%** | 6.72 |
| **Centrality Edge Suppression** | 648.17 | 41.18% | 12 | 52.75% | 6.66 |
| **Greedy Edge Weight** | 659.97 | 41.93% | 15 | 52.18% | 5.34 |
| **Average Linkage MPF (AL-MPF)** | 670.40 | 42.59% | 11 | 51.17% | 10.82 |
| **Size-Constrained MPF (SC-MPF)** | 673.10 | 42.76% | 13 | 51.85% | 6.23 |
| **Reliable Cluster Edge** | 700.73 | 44.52% | 12 | 49.99% | 5.96 |
| **Baseline (Unsuppressed)** | 703.37 | 44.69% | 12 | 50.18% | 4.92 |

---

## Topological & Epidynamic Analysis

### Why NetShield Wins in the Large Outbreak Regime
1. **Multi-pocket Seed Infiltration**: When the initial outbreak size is very small ($i = 1$), the infection starts in a single node, which is usually located within a specific local community. Community containment strategies (**SC-MPF**, **AL-MPF**) succeed because they can place firewalls on the boundaries of that community, trapping the virus before it reaches global hubs. However, with 157 starting nodes scattered across the network, the virus is initialized simultaneously across multiple different communities.
2. **Failure of Boundary Partitioning**: Since the outbreak has already bypassed the community boundaries at tick 0, partitioning the network into isolated clusters is no longer effective. The firewalls cut connections between regions that are both already active outbreak sites, failing to prevent localized spread.
3. **Criticality of Global Hubs**: In a widespread, multi-seed outbreak, the primary risk is that separate local outbreaks merge and spread exponentially through major transport hubs (e.g., Atlanta, Chicago, Denver). By prioritizing the suppression of edges connected to these high-eigenvector hubs, **NetShield** successfully dampens the global transmission channels, slowing down the overall peak height.

### Infection Curve Plot
![Simulation Curve comparison for large outbreak](/home/pruet/.gemini/antigravity-cli/brain/a00d80cf-d787-4726-ba55-47e9a7f4a788/usairport_i157_curves_s10_r15_p0.3_P30_v0_q0.png)

*(Note: Click [here](file:///home/pruet/Development/Oregon/Results/usairport_i157_curves_s10_r15_p0.3_P30_v0_q0.png) to open the original PNG file in the workspace)*
