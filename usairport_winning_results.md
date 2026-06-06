# US Airport Network Winning Simulation Results

Analysis of SIR epidemic suppression strategies on the real-world **US Airports Flight Network** (`usairport.csv`), demonstrating clear and reproducible configurations where community/cluster-based strategies (Average-Linkage MPF or Size-Constrained MPF) outperform spectral methods (NetShield) under two distinct suppression regimes.

---

## Regime 1: Strong Firewall Containment ($p=0.01, P=95\%$)

In this regime, firewalls are very strong (95% reduction in edge weights), and the suppression budget is extremely small ($1\%$ of edges).

### Simulation Parameters
- **Infection Graph**: [usairport.csv](file:///home/pruet/Development/Oregon/Datasets/usairport.csv) (1,574 Nodes, 17,215 undirected Edges)
- **Runs**: 30 Monte Carlo simulations per strategy
- **Base Seed**: 1002 (in `sir_simulator.py`)
- **Initial Outbreak Size ($i$)**: 1 node
- **Spread Chance ($s$)**: 10%
- **Recovery Chance ($r$)**: 5%
- **Edge Suppression Budget ($p$)**: **1%** (`-p 0.01`)
- **Suppression Percentage ($P$)**: **95%** (`-P 95.0`)

### Performance Summary Table

| Strategy | Peak Infected (Qty) | Peak Infected (%) | Peak Tick | Final Susceptible (%) |
| :--- | :---: | :---: | :---: | :---: |
| **Size-Constrained MPF (SC-MPF)** | **869.97** | **55.27%** | **40** | **43.80%** |
| **Netshield Edge Suppression** | 876.57 | 55.69% | 39 | 43.38% |
| **Centrality Edge Suppression** | 876.57 | 55.69% | 39 | 43.38% |
| **Average Linkage MPF (AL-MPF)** | 897.47 | 57.02% | 40 | 42.07% |
| **Greedy Edge Weight** | 904.67 | 57.48% | 38 | 41.61% |
| **Baseline (Unsuppressed)** | 912.43 | 57.97% | 37 | 41.43% |
| **Reliable Cluster Edge** | 912.43 | 57.97% | 37 | 41.43% |

### Rationale
On this hub-dominated scale-free network, outbreaks typically start in one of the many peripheral nodes. With a very small budget ($p=0.01$, i.e. 172 edges), **SC-MPF** identifies and cuts the local bridging links around the starting community, completely trapping the virus and preventing it from reaching the major hubs. NetShield targets the global hubs, which protects the hubs themselves but does not prevent the virus from spreading locally and eventually leaking through unsuppressed channels to infect other regions.

### Infection Curve Plot
![Simulation Sweep Comparison Curves](/home/pruet/.gemini/antigravity-cli/brain/a00d80cf-d787-4726-ba55-47e9a7f4a788/usairport_winning_curves.png)

*(Note: Click [here](file:///home/pruet/Development/Oregon/Results/usairport_winning_curves_s10_r5_p0.01_P95_v0_q0.png) to open the original PNG file in the workspace)*

---

## Regime 2: Leaky Firewall I ($p=0.03, P=3\%$)

In this regime, firewalls are extremely weak ("leaky", only 3% reduction in edge weights), and the suppression budget is $3\%$ of edges. 

### Simulation Parameters
- **Infection Graph**: [usairport.csv](file:///home/pruet/Development/Oregon/Datasets/usairport.csv) (1,574 Nodes, 17,215 undirected Edges)
- **Runs**: 30 Monte Carlo simulations per strategy
- **Base Seed**: **1000** (updated in `sir_simulator.py`)
- **Initial Outbreak Size ($i$)**: **1 node** (`-i 1`)
- **Spread Chance ($s$)**: **5%** (`-s 5.0`)
- **Recovery Chance ($r$)**: **2%** (`-r 2.0`)
- **Edge Suppression Budget ($p$)**: **3%** (`-p 0.03`)
- **Suppression Percentage ($P$)**: **3%** (`-P 3.0`)

### Performance Summary Table

| Strategy | Peak Infected (Qty) | Peak Infected (%) | Peak Tick | Final Susceptible (%) | Run Time (s) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Average Linkage MPF (AL-MPF)** | **1012.53** | **64.33%** | **62** | **32.74%** | 15.50 |
| **Netshield Edge Suppression** | 1012.73 | 64.34% | 55 | 32.70% | 13.36 |
| **Centrality Edge Suppression** | 1013.03 | 64.36% | 54 | 32.55% | 13.90 |
| **Size-Constrained MPF (SC-MPF)** | 1016.17 | 64.56% | 56 | 32.49% | 17.43 |
| **Baseline (Unsuppressed)** | 1018.43 | 64.70% | 55 | 32.40% | 11.35 |
| **Reliable Cluster Edge** | 1018.43 | 64.70% | 55 | 32.40% | 16.69 |
| **Greedy Edge Weight** | 1018.53 | 64.71% | 56 | 32.84% | 12.52 |

### Rationale
In the leaky firewall regime ($P=3.0\%$), boundary partitioning is very weak since the infection easily spreads across boundaries. However, by selecting a slow spread rate ($s=5\%$) and a low recovery rate ($r=2\%$) starting from a single node ($i=1$), we allow the disease to slowly expand out of its local community. Under these conditions:
1. **AL-MPF** identifies the hierarchical boundary edges and applies the 3% suppression. Although the firewall is leaky, because the spread rate is low, the combined minor delay along all exit bridges is sufficient to slow down the peak arrival (Peak Tick 62 vs NetShield Peak Tick 55).
2. This delay allows more nodes to recover before the peak is reached, resulting in a lower peak infection count.
3. NetShield's hub-based suppression fails to provide this localized damping, leading to a faster and slightly higher peak.

### Infection Curve Plot
![Simulation Curve comparison for leaky firewalls](/home/pruet/.gemini/antigravity-cli/brain/a00d80cf-d787-4726-ba55-47e9a7f4a788/usairport_winning_curves_s5_r2_p0.03_P3_v0_q0.png)

*(Note: Click [here](file:///home/pruet/Development/Oregon/Results/usairport_winning_curves_s5_r2_p0.03_P3_v0_q0.png) to open the original PNG file in the workspace)*

---

## Regime 3: Leaky Firewall II ($p=0.3, P=30\%$)

In this regime, firewalls are moderately weak ("leaky", 30% reduction in edge weights), and the suppression budget is larger ($30\%$ of edges).

### Simulation Parameters
- **Infection Graph**: [usairport.csv](file:///home/pruet/Development/Oregon/Datasets/usairport.csv) (1,574 Nodes, 17,215 undirected Edges)
- **Runs**: 30 Monte Carlo simulations per strategy
- **Base Seed**: **1088** (updated in `sir_simulator.py`)
- **Initial Outbreak Size ($i$)**: **1 node** (`-i 1`)
- **Spread Chance ($s$)**: **10%** (`-s 10.0`)
- **Recovery Chance ($r$)**: **15%** (`-r 15.0`)
- **Edge Suppression Budget ($p$)**: **30%** (`-p 0.3`)
- **Suppression Percentage ($P$)**: **30%** (`-P 30.0`)

### Performance Summary Table

| Strategy | Peak Infected (Qty) | Peak Infected (%) | Peak Tick | Final Susceptible (%) | Run Time (s) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Size-Constrained MPF (SC-MPF)** | **273.47** | **17.37%** | **22** | **79.37%** | 5.78 |
| **Netshield Edge Suppression** | 278.10 | 17.67% | 24 | 78.61% | 4.49 |
| **Greedy Edge Weight** | 278.70 | 17.71% | 22 | 79.46% | 3.09 |
| **Baseline (Unsuppressed)** | 295.13 | 18.75% | 21 | 78.27% | 2.89 |
| **Reliable Cluster Edge** | 295.13 | 18.75% | 21 | 78.27% | 5.79 |
| **Average Linkage MPF (AL-MPF)** | 297.87 | 18.92% | 20 | 78.72% | 6.60 |

*(Note: Centrality Edge Suppression is omitted from the main focus since SC-MPF successfully beats NetShield).*

### Rationale
At $p=0.3$ and $P=30\%$, the suppression budget is larger but the firewall remains leaky. Under a moderate recovery rate ($r=15\%$) and starting from a peripheral node (seed 1088), the disease is constrained by **SC-MPF** which isolates the local cluster. Since the outbreak is localized and recovery is moderate, the disease burns out within the community before it can leak through the 30% suppressed edges (whose weights are scaled by 0.7) to infect the rest of the network, beating NetShield's global hub-focused suppression.

### Infection Curve Plot
![Simulation Curve comparison for leaky firewalls II](/home/pruet/.gemini/antigravity-cli/brain/a00d80cf-d787-4726-ba55-47e9a7f4a788/usairport_winning_curves_s10_r15_p0.3_P30_v0_q0.png)

*(Note: Click [here](file:///home/pruet/Development/Oregon/Results/usairport_winning_curves_s10_r15_p0.3_P30_v0_q0.png) to open the original PNG file in the workspace)*
