#!/usr/bin/env python3
"""
Suppression Strategies for SIR Simulator
Author: Antigravity

This module defines the registry and suppression strategies for evaluating epidemic
control on network structures.

To add your own suppression algorithm:
1. Write a function with the signature: `def my_algorithm(simulator, event_type, **kwargs)`
2. Decorate it with `@register_strategy("my_algorithm_name")`
3. It will automatically be loaded and evaluated by `sir_simulator.py`!
"""

import random
import numpy as np

# Global registry of suppression strategies.
SUPPRESSION_REGISTRY = {}

def register_strategy(name):
    """
    Decorator to register a suppression strategy function.
    """
    def decorator(func):
        SUPPRESSION_REGISTRY[name] = func
        return func
    return decorator

def run_sparse_power_iteration(nodes_list, adj, max_iter=100, tol=1e-6):
    """
    Computes the principal eigenvalue and eigenvector of the adjacency matrix
    using sparse power iteration.
    """
    n = len(nodes_list)
    node_to_idx = {node: i for i, node in enumerate(nodes_list)}
    
    # Initialize eigenvector with positive values
    u = np.ones(n) / np.sqrt(n)
    
    lambda_1 = 0.0
    for _ in range(max_iter):
        u_next = np.zeros(n)
        for i, node in enumerate(nodes_list):
            for neighbor, weight in adj[node].items():
                if neighbor in node_to_idx:
                    j = node_to_idx[neighbor]
                    w = weight
                    u_next[i] += w * u[j]
        
        norm = np.linalg.norm(u_next)
        if norm < 1e-9:
            break
            
        u_next = u_next / norm
        diff = np.linalg.norm(u_next - u)
        u = u_next
        lambda_1 = norm
        if diff < tol:
            break
            
    return lambda_1, u, node_to_idx

def run_netshield(nodes_list, adj, k):
    """
    Greedy NetShield immunization algorithm (Chen et al.).
    Selects k nodes to maximize the Shield-value Sv(S).
    """
    lambda_1, u, node_to_idx = run_sparse_power_iteration(nodes_list, adj)
    n = len(nodes_list)
    
    # Set S of selected node indices
    S = set()
    
    # member_sum[j] = sum_{i in S} A(i, j) * u[i]
    member_sum = np.zeros(n)
    
    for _ in range(k):
        best_gain = -float('inf')
        best_node_idx = -1
        
        for j in range(n):
            if j in S:
                continue
            
            # Compute marginal gain: gain = 2 * lambda_1 * u(j)^2 - 2 * member_sum[j] * u(j)
            gain = 2 * lambda_1 * (u[j] ** 2) - 2 * member_sum[j] * u[j]
            
            if gain > best_gain:
                best_gain = gain
                best_node_idx = j
                
        if best_node_idx == -1:
            break
            
        S.add(best_node_idx)
        
        # Update member_sum for neighbors of newly added node
        i_star = best_node_idx
        node_name = nodes_list[i_star]
        for neighbor, weight in adj[node_name].items():
            if neighbor in node_to_idx:
                j = node_to_idx[neighbor]
                w = weight
                member_sum[j] += w * u[i_star]
            
    return [nodes_list[idx] for idx in S]

@register_strategy("netshield_edge_suppression")
def netshield_edge_suppression(simulator, event_type, **kwargs):
    """
    NetShield-based Edge Suppression: selects top k nodes using Chen's greedy NetShield algorithm,
    then suppresses all edges incident to those nodes by the standard suppression percentage.
    """
    if event_type == "setup":
        all_nodes = list(simulator.states.keys())
        num_to_suppress = int(len(all_nodes) * simulator.suppression_ratio)
        if num_to_suppress > 0:
            top_nodes = run_netshield(all_nodes, simulator.adj, num_to_suppress)
            reduction_factor = 1.0 - (simulator.suppression_percentage / 100.0)
            seen_edges = set()
            for u_node in top_nodes:
                for v_node in list(simulator.adj[u_node].keys()):
                    edge_key = tuple(sorted((u_node, v_node)))
                    if edge_key not in seen_edges:
                        seen_edges.add(edge_key)
                        w = simulator.adj[u_node][v_node]
                        new_weight = w * reduction_factor
                        
                        # Update in both directions to keep the graph undirected
                        simulator.adj[u_node][v_node] = new_weight
                        if u_node in simulator.adj[v_node]:
                            simulator.adj[v_node][u_node] = new_weight

@register_strategy("centrality_edge_suppression")
def centrality_edge_suppression(simulator, event_type, **kwargs):
    """
    Centrality-based edge suppression: identifies top central nodes using eigenvector centrality
    and randomly reduces the weights of their adjacent links (by multiplying by a random factor in [0.1, 0.5]) at setup.
    """
    if event_type == "setup":
        all_nodes = list(simulator.states.keys())
        # Calculate eigenvector centrality
        _, u, node_to_idx = run_sparse_power_iteration(all_nodes, simulator.adj)
        
        # Sort nodes by centrality u
        sorted_nodes = sorted(all_nodes, key=lambda who: u[node_to_idx[who]], reverse=True)
        num_to_suppress = int(len(sorted_nodes) * simulator.suppression_ratio)
        
        if num_to_suppress > 0:
            top_nodes = sorted_nodes[:num_to_suppress]
            reduction_factor = 1.0 - (simulator.suppression_percentage / 100.0)
            seen_edges = set()
            for u_node in top_nodes:
                for v_node in list(simulator.adj[u_node].keys()):
                    edge_key = tuple(sorted((u_node, v_node)))
                    if edge_key not in seen_edges:
                        seen_edges.add(edge_key)
                        w = simulator.adj[u_node][v_node]
                        new_weight = w * reduction_factor
                        
                        # Update in both directions to keep the graph undirected
                        simulator.adj[u_node][v_node] = new_weight
                        if u_node in simulator.adj[v_node]:
                            simulator.adj[v_node][u_node] = new_weight

@register_strategy("greedy_edge_weight_suppression")
def greedy_edge_weight_suppression(simulator, event_type, **kwargs):
    """
    Greedy edge weight suppression: identifies links with the highest weights
    and suppresses them by reducing their weights by 90% at setup.
    """
    if event_type == "setup":
        # Collect unique undirected edges with their weights
        edges = []
        seen_edges = set()
        for u in simulator.adj:
            for v in simulator.adj[u]:
                edge_key = tuple(sorted((u, v)))
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    w = simulator.adj[u][v]
                    edges.append((edge_key, w))
                    
        # Sort edges by weight in descending order
        edges.sort(key=lambda item: item[1], reverse=True)
        
        # Select top fraction of edges to suppress (using suppression_ratio)
        num_to_suppress = int(len(edges) * simulator.suppression_ratio)
        if num_to_suppress > 0:
            top_edges = edges[:num_to_suppress]
            reduction_factor = 1.0 - (simulator.suppression_percentage / 100.0)
            for (u, v), weight in top_edges:
                suppressed_weight = weight * reduction_factor
                simulator.adj[u][v] = suppressed_weight
                simulator.adj[v][u] = suppressed_weight

@register_strategy("reliable_cluster_edge_suppression")
def reliable_cluster_edge_suppression(simulator, event_type, **kwargs):
    """
    Reliable Cluster-based Edge Suppression (inspired by Pruet Boonma's "Reliable Cluster on Uncertain Multigraph" paper):
    groups nodes into robust/reliable clusters (communities) using weighted Louvain community detection on the
    uncertain/probabilistic link weights, then suppresses the top highest-weight inter-cluster bridging edges by 90% at setup.
    """
    if event_type == "setup":
        import networkx as nx
        
        # Build weighted graph from simulator.adj
        G = nx.Graph()
        for u in simulator.adj:
            for v, w in simulator.adj[u].items():
                G.add_edge(u, v, weight=w)
                
        # Detect communities using weighted Louvain with a fixed seed for reproducible determinism
        try:
            communities = nx.community.louvain_communities(G, weight='weight', seed=42)
        except Exception:
            communities = nx.community.label_propagation_communities(G)
            
        # Map each node to its community index
        node_to_community = {}
        for comm_idx, comm in enumerate(communities):
            for node in comm:
                node_to_community[node] = comm_idx
                
        # Collect all edges that link between different communities
        inter_community_edges = []
        seen_edges = set()
        for u in simulator.adj:
            for v in simulator.adj[u]:
                edge_key = tuple(sorted((u, v)))
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    u_comm = node_to_community.get(u)
                    v_comm = node_to_community.get(v)
                    if u_comm is not None and v_comm is not None and u_comm != v_comm:
                        w = simulator.adj[u][v]
                        inter_community_edges.append((edge_key, w))
                        
        # Sort bridging edges by weight in descending order
        inter_community_edges.sort(key=lambda item: item[1], reverse=True)
        
        # The suppression budget is calculated as a fraction of the TOTAL edges in the graph,
        # ensuring a fair comparison with other edge suppression strategies.
        total_edges = sum(len(neighbors) for neighbors in simulator.adj.values()) // 2
        num_to_suppress = int(total_edges * simulator.suppression_ratio)
        if num_to_suppress > 0:
            top_bridging = inter_community_edges[:num_to_suppress]
            reduction_factor = 1.0 - (simulator.suppression_percentage / 100.0)
            for (u, v), weight in top_bridging:
                suppressed_weight = weight * reduction_factor
                simulator.adj[u][v] = suppressed_weight
                simulator.adj[v][u] = suppressed_weight
