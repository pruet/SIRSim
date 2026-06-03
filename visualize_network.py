#!/usr/bin/env python3
"""
Premium Network Graph Visualization Script
Author: Antigravity
"""

import sys
import os
import matplotlib.pyplot as plt
import networkx as nx
from sir_simulator import parse_netlogo_world

def visualize_graph(csv_file, output_image):
    if not os.path.exists(csv_file):
        print(f"Error: File '{csv_file}' not found.")
        sys.exit(1)
        
    print(f"Parsing network from {csv_file}...")
    globals_dict, nodes, adj = parse_netlogo_world(csv_file)
    
    # Create NetworkX graph
    G = nx.Graph()
    for u in adj:
        for v, w in adj[u].items():
            G.add_edge(u, v, weight=w)
            
    num_nodes = G.number_of_nodes()
    num_edges = G.number_of_edges()
    print(f"Loaded graph with {num_nodes} nodes and {num_edges} edges.")
    
    # Calculate degree centrality for node sizes and colors
    degrees = dict(G.degree())
    max_degree = max(degrees.values()) if degrees else 1
    
    # Colors: Smooth gradient from blue (low degree) to red (high degree / hubs)
    node_colors = [degrees[n] for n in G.nodes()]
    node_sizes = [100 + (degrees[n] / max_degree) * 600 for n in G.nodes()]
    
    # Layout using Spring layout (Fruchterman-Reingold force-directed)
    print("Computing force-directed layout...")
    pos = nx.spring_layout(G, k=0.18, iterations=100, seed=42)
    
    # Draw graph with premium aesthetics
    fig, ax = plt.subplots(figsize=(12, 10), dpi=300)
    ax.axis('off')
    
    # Draw edges with subtle grey lines
    nx.draw_networkx_edges(
        G, pos, ax=ax,
        edge_color="#dcdde1",
        width=1.0,
        alpha=0.6
    )
    
    # Draw nodes with a sleek colormap and borders
    scatter = nx.draw_networkx_nodes(
        G, pos, ax=ax,
        node_color=node_colors,
        node_size=node_sizes,
        cmap=plt.cm.coolwarm,
        edgecolors="#2f3640",
        linewidths=1.2,
        alpha=0.9
    )
    
    # Add labels to the top 10% highest degree hub nodes for clarity
    top_threshold = sorted(degrees.values(), reverse=True)[max(1, int(num_nodes * 0.08))]
    labels = {n: str(n) for n in G.nodes() if degrees[n] >= top_threshold}
    nx.draw_networkx_labels(
        G, pos, labels, ax=ax,
        font_size=8,
        font_weight="bold",
        font_color="#2f3640"
    )
    
    # Add a premium colorbar for degree indicator
    cbar = plt.colorbar(scatter, ax=ax, orientation='horizontal', pad=0.03, shrink=0.6)
    cbar.set_label("Node Connectivity (Degree / Number of Connections)", fontsize=10, fontweight="semibold", color="#2c3e50")
    cbar.ax.tick_params(labelsize=8, colors="#7f8c8d")
    cbar.outline.set_edgecolor("#bdc3c7")
    cbar.outline.set_linewidth(0.8)
    
    # Title & Metadata
    title = f"Force-Directed Network Topology Visualization\n({os.path.basename(csv_file)}: {num_nodes} Nodes, {num_edges} Edges)"
    ax.set_title(title, fontsize=14, fontweight="bold", pad=20, color="#2c3e50")
    
    plt.tight_layout()
    plt.savefig(output_image, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"Successfully generated and saved network visualization plot to: {output_image}")

if __name__ == "__main__":
    csv_path = "polbooks.csv"
    img_out = "polbooks_visualization.png"
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    if len(sys.argv) > 2:
        img_out = sys.argv[2]
        
    visualize_graph(csv_path, img_out)
