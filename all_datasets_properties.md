# Workspace Datasets Topological Properties Table

A comprehensive lookup table of all network graphs available in the `Datasets/` and `konect_data/` directories, programmatically analyzed using network topology metrics.

---

## Dataset Properties Table

| Dataset Filename | Nodes ($N$) | Edges ($M$) | Avg Degree | Density | Modularity ($Q$) | Spreading Context / Description |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **[`modular_sbm_300.csv`](file:///home/pruet/Development/Oregon/Datasets/modular_sbm_300.csv)** | 298 | 847 | 5.68 | 0.0191 | 0.590 | Synthetic Stochastic Block Model (Small modularity benchmark) |
| **[`modular_sbm_3000.csv`](file:///home/pruet/Development/Oregon/Datasets/modular_sbm_3000.csv)** | 2,995 | 8,707 | 5.81 | 0.0019 | 0.735 | Synthetic Stochastic Block Model (High modularity benchmark) |
| **[`oregon1_010331.txt`](file:///home/pruet/Development/Oregon/Datasets/oregon1_010331.txt)** | 10,670 | 22,002 | 4.12 | 0.0004 | 0.613 | AS Router Peering Graph (Internet worm spreading) |
| **[`oregon_export.csv`](file:///home/pruet/Development/Oregon/Datasets/oregon_export.csv)** | 3,000 | 8,373 | 5.58 | 0.0019 | 0.493 | Router topology or synthetic variation |
| **[`perfect_tree_sbm.csv`](file:///home/pruet/Development/Oregon/Datasets/perfect_tree_sbm.csv)** | 150 | 563 | 7.51 | 0.0504 | 0.792 | Tree-structured SBM (Hierarchical block benchmark) |
| **[`polblogs.csv`](file:///home/pruet/Development/Oregon/Datasets/polblogs.csv)** | 1,224 | 16,718 | 27.32 | 0.0223 | 0.427 | Political Blogs Hyperlink Network (Information/opinion spreading) |
| **[`polbooks.csv`](file:///home/pruet/Development/Oregon/Datasets/polbooks.csv)** | 105 | 441 | 8.40 | 0.0808 | 0.502 | Political Books Co-purchasing Network (Opinion contagion) |
| **[`primary_school.csv`](file:///home/pruet/Development/Oregon/Datasets/primary_school.csv)** | 242 | 1,938 | 16.02 | 0.0665 | 0.686 | SocioPatterns School Contact Network (Biological spreading) |
| **[`sensor_network.csv`](file:///home/pruet/Development/Oregon/Datasets/sensor_network.csv)** | 150 | 1,399 | 18.65 | 0.1252 | 0.753 | Wireless Sensor Network (Small spatial topology) |
| **[`sensor_network_3000.csv`](file:///home/pruet/Development/Oregon/Datasets/sensor_network_3000.csv)** | 3,000 | 12,000 | 8.00 | 0.0027 | 0.827 | Wireless Sensor Network (Spatially clustered topology) |
| **[`three_tier_sbm.csv`](file:///home/pruet/Development/Oregon/Datasets/three_tier_sbm.csv)** | 150 | 1,284 | 17.12 | 0.1149 | 0.399 | Multi-tier Hierarchical SBM (Hub-dominated hierarchy) |
| **[`vone_3000.csv`](file:///home/pruet/Development/Oregon/Datasets/vone_3000.csv)** | 3,000 | 9,000 | 6.00 | 0.0020 | 0.916 | Scaled Spatial Modular Network (Synthetic spatial community benchmark) |
| **[`vone_300_6_3.csv`](file:///home/pruet/Development/Oregon/Datasets/vone_300_6_3.csv)** | 300 | 901 | 6.01 | 0.0201 | 0.791 | NetLogo Benchmark Spatial Network (Synthetic spatial benchmark) |
| **[`powergrid.csv`](file:///home/pruet/Development/Oregon/konect_data/powergrid.csv)** | 4,941 | 6,594 | 2.67 | 0.0005 | 0.933 | Western US Power Grid Network (Infrastructure cascade failures) |
| **[`usairport.csv`](file:///home/pruet/Development/Oregon/konect_data/usairport.csv)** | 1,574 | 17,215 | 21.87 | 0.0139 | 0.301 | US Air Transportation Network (Global pandemic spreading) |

---

## Key Definitions & Insights
* **Avg Degree ($<k>$)**: The average number of connections per node. Denser contact networks (like `polblogs` or `primary_school`) have a high average degree, making localized epidemic containment extremely difficult without a high budget.
* **Density ($D$)**: The ratio of actual edges to the maximum possible number of edges. Sparse networks (like `powergrid` or `oregon1`) are easily partitioned, while dense networks require hub-focused containment.
* **Modularity ($Q$)**: Measures the strength of division of a network into modules (communities). Graphs with very high modularity ($Q > 0.60$, such as `vone_3000`, `perfect_tree_sbm`, and `powergrid`) are ideal for community-based containment algorithms like **AL-MPF** and **SC-MPF**, which place firewalls on inter-community bridges.
