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
                j = node_to_idx[neighbor]
                w = weight if weight is not None else 1.0
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
            j = node_to_idx[neighbor]
            w = weight if weight is not None else 1.0
            member_sum[j] += w * u[i_star]
            
    return [nodes_list[idx] for idx in S]

@register_strategy("netshield_immunization")
def netshield_immunization(simulator, event_type, **kwargs):
    """
    Static NetShield immunization: selects and immunizes k nodes using Chen's greedy NetShield algorithm.
    """
    if event_type == "setup":
        susceptible_nodes = [who for who, state in simulator.states.items() if state == 0]
        num_to_vaccinate = int(len(susceptible_nodes) * simulator.vaccination_fraction)
        if num_to_vaccinate > 0:
            all_nodes = list(simulator.states.keys())
            to_vaccinate = run_netshield(all_nodes, simulator.adj, num_to_vaccinate)
            for who in to_vaccinate:
                if simulator.states[who] == 0:
                    simulator.states[who] = 2  # Immunize

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
        num_to_suppress = int(len(sorted_nodes) * simulator.vaccination_fraction)
        
        if num_to_suppress > 0:
            top_nodes = sorted_nodes[:num_to_suppress]
            for u_node in top_nodes:
                for v_node in list(simulator.adj[u_node].keys()):
                    w = simulator.adj[u_node][v_node]
                    base_chance = w if w is not None else simulator.spread_chance
                    # Reduce by a random factor in [0.1, 0.5]
                    reduction_factor = random.uniform(0.1, 0.5)
                    new_weight = base_chance * reduction_factor
                    
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
                    base_weight = w if w is not None else simulator.spread_chance
                    edges.append((edge_key, base_weight))
                    
        # Sort edges by weight in descending order
        edges.sort(key=lambda item: item[1], reverse=True)
        
        # Select top fraction of edges to suppress (using vaccination_fraction, e.g. 10% of edges)
        num_to_suppress = int(len(edges) * simulator.vaccination_fraction)
        if num_to_suppress > 0:
            top_edges = edges[:num_to_suppress]
            for (u, v), weight in top_edges:
                suppressed_weight = weight * 0.1
                simulator.adj[u][v] = suppressed_weight
                simulator.adj[v][u] = suppressed_weight
