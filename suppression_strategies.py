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
    Reliable Cluster-based Edge Suppression (implementing the exact Most-Probability-First algorithm
    from Pruet Boonma's "Reliable Cluster on Uncertain Multigraph" paper):
    1. Initializes each node as a singleton cluster.
    2. Sorts all network edges descending by their transmission probability (weight).
    3. Greedily merges clusters connected by the highest probability edges first until exactly k clusters remain.
    4. Identifies all inter-cluster bridging edges and suppresses the top highest-weight links.
    """
    if event_type == "setup":
        # Collect all unique edges and their weights
        edges = []
        seen_edges = set()
        for u in simulator.adj:
            for v in simulator.adj[u]:
                edge_key = tuple(sorted((u, v)))
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    w = simulator.adj[u][v]
                    edges.append((u, v, w))
                    
        # Sort edges by weight in descending order (highest probability first)
        edges.sort(key=lambda x: x[2], reverse=True)
        
        # Disjoint-Set helper functions
        all_nodes = list(simulator.adj.keys())
        
        # Calculate node strengths (degrees) in the original graph
        node_strength = {u: sum(simulator.adj[u].values()) for u in simulator.adj}
        total_strength = sum(node_strength.values())
        
        # Optimize k dynamically starting from the number of initial infected nodes (min k) up to max(15, min_k)
        # by maximizing the modularity Q
        initial_infected_count = sum(1 for state in simulator.states.values() if state == 1)
        min_k = max(2, initial_infected_count)
        max_k = max(15, min_k)
        
        best_k = min_k
        max_modularity = -float('inf')
        best_node_to_community = None
        
        for temp_k in range(min_k, max_k + 1):
            parent = {node: node for node in all_nodes}
            
            def find(node):
                path = []
                while parent[node] != node:
                    path.append(node)
                    node = parent[node]
                for n in path:
                    parent[n] = node
                return node
                
            def union(node1, node2):
                root1 = find(node1)
                root2 = find(node2)
                if root1 != root2:
                    parent[root1] = root2
                    return True
                return False
                
            num_clusters = len(all_nodes)
            for u, v, w in edges:
                if num_clusters <= temp_k:
                    break
                if union(u, v):
                    num_clusters -= 1
                    
            node_to_community = {node: find(node) for node in all_nodes}
            
            # Map community root to its list of nodes
            comm_nodes = {}
            for node, comm in node_to_community.items():
                if comm not in comm_nodes:
                    comm_nodes[comm] = []
                comm_nodes[comm].append(node)
                
            # Calculate Modularity Q for this partition
            modularity_val = 0.0
            if total_strength > 1e-9:
                for comm, members in comm_nodes.items():
                    vol = sum(node_strength.get(node, 0.0) for node in members)
                    internal_weight = 0.0
                    for u in members:
                        for v, weight in simulator.adj[u].items():
                            if node_to_community.get(v) == comm:
                                internal_weight += weight
                    modularity_val += (internal_weight / total_strength) - (vol / total_strength) ** 2
                    
            if modularity_val > max_modularity:
                max_modularity = modularity_val
                best_k = temp_k
                best_node_to_community = node_to_community
                
        # Collect all inter-cluster bridging edges for the optimal k configuration
        inter_community_edges = []
        for u, v, w in edges:
            u_comm = best_node_to_community[u]
            v_comm = best_node_to_community[v]
            if u_comm != v_comm:
                inter_community_edges.append(((u, v), w))
                
        # Sort bridging edges descending by weight
        inter_community_edges.sort(key=lambda x: x[1], reverse=True)
        
        # Suppression budget is calculated as a fraction of TOTAL edges in the graph
        total_edges = len(edges)
        num_to_suppress = int(total_edges * simulator.suppression_ratio)
        if num_to_suppress > 0:
            top_bridging = inter_community_edges[:num_to_suppress]
            reduction_factor = 1.0 - (simulator.suppression_percentage / 100.0)
            for (u, v), weight in top_bridging:
                suppressed_weight = weight * reduction_factor
                simulator.adj[u][v] = suppressed_weight
                simulator.adj[v][u] = suppressed_weight

@register_strategy("size_constrained_mpf_suppression")
def size_constrained_mpf_suppression(simulator, event_type, **kwargs):
    """
    Size-Constrained MPF Suppression:
    1. Reconstructs communities using MPF, but enforces a maximum cluster size constraint
       (max_size = alpha * N / k, where alpha = 1.5 by default) during Union-Find merges.
    2. Modularity is evaluated dynamically to select the best k.
    3. Identifies inter-cluster bridging edges and suppresses them.
    """
    if event_type == "setup":
        edges = []
        seen_edges = set()
        for u in simulator.adj:
            for v in simulator.adj[u]:
                edge_key = tuple(sorted((u, v)))
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    w = simulator.adj[u][v]
                    edges.append((u, v, w))
        edges.sort(key=lambda x: x[2], reverse=True)
        
        all_nodes = list(simulator.adj.keys())
        n_nodes = len(all_nodes)
        node_strength = {u: sum(simulator.adj[u].values()) for u in simulator.adj}
        total_strength = sum(node_strength.values())
        
        initial_infected_count = sum(1 for state in simulator.states.values() if state == 1)
        min_k = max(2, initial_infected_count)
        max_k = max(15, min_k)
        
        best_k = min_k
        max_modularity = -float('inf')
        best_node_to_community = None
        
        alpha = 1.5 # Cluster size tolerance factor
        
        for temp_k in range(min_k, max_k + 1):
            parent = {node: node for node in all_nodes}
            size = {node: 1 for node in all_nodes}
            
            def find(node):
                path = []
                while parent[node] != node:
                    path.append(node)
                    node = parent[node]
                for n in path:
                    parent[n] = node
                return node
                
            def union(node1, node2, max_size):
                root1 = find(node1)
                root2 = find(node2)
                if root1 != root2:
                    if size[root1] + size[root2] <= max_size:
                        parent[root1] = root2
                        size[root2] += size[root1]
                        return True
                return False
                
            max_cluster_size = max(5, int(alpha * n_nodes / temp_k))
            num_clusters = n_nodes
            
            for u, v, w in edges:
                if num_clusters <= temp_k:
                    break
                if union(u, v, max_cluster_size):
                    num_clusters -= 1
                    
            node_to_community = {node: find(node) for node in all_nodes}
            comm_nodes = {}
            for node, comm in node_to_community.items():
                if comm not in comm_nodes:
                    comm_nodes[comm] = []
                comm_nodes[comm].append(node)
                
            modularity_val = 0.0
            if total_strength > 1e-9:
                for comm, members in comm_nodes.items():
                    vol = sum(node_strength.get(node, 0.0) for node in members)
                    internal_weight = 0.0
                    for u in members:
                        for v, weight in simulator.adj[u].items():
                            if node_to_community.get(v) == comm:
                                internal_weight += weight
                    modularity_val += (internal_weight / total_strength) - (vol / total_strength) ** 2
                    
            if modularity_val > max_modularity:
                max_modularity = modularity_val
                best_k = temp_k
                best_node_to_community = node_to_community
                
        # Collect inter-community edges and suppress
        inter_community_edges = []
        for u, v, w in edges:
            u_comm = best_node_to_community[u]
            v_comm = best_node_to_community[v]
            if u_comm != v_comm:
                inter_community_edges.append(((u, v), w))
                
        inter_community_edges.sort(key=lambda x: x[1], reverse=True)
        total_edges = len(edges)
        num_to_suppress = int(total_edges * simulator.suppression_ratio)
        if num_to_suppress > 0:
            top_bridging = inter_community_edges[:num_to_suppress]
            reduction_factor = 1.0 - (simulator.suppression_percentage / 100.0)
            for (u, v), weight in top_bridging:
                suppressed_weight = weight * reduction_factor
                simulator.adj[u][v] = suppressed_weight
                simulator.adj[v][u] = suppressed_weight

@register_strategy("average_linkage_mpf_suppression")
def average_linkage_mpf_suppression(simulator, event_type, **kwargs):
    """
    Average-Linkage MPF Suppression:
    1. Reconstructs communities using Average-Linkage Hierarchical Clustering.
    2. Modularity is evaluated dynamically to select the best k.
    3. Identifies inter-cluster bridging edges and suppresses them.
    """
    if event_type == "setup":
        import heapq
        all_nodes = list(simulator.adj.keys())
        n_nodes = len(all_nodes)
        
        node_strength = {u: sum(simulator.adj[u].values()) for u in simulator.adj}
        total_strength = sum(node_strength.values())
        
        # Initialize clusters
        cluster_members = {node: [node] for node in all_nodes}
        cluster_size = {node: 1 for node in all_nodes}
        active_clusters = set(all_nodes)
        node_to_cluster = {node: node for node in all_nodes}
        
        # Initialize inter-cluster edge weights
        inter_weight = {node: {} for node in all_nodes}
        for u in simulator.adj:
            for v, w in simulator.adj[u].items():
                inter_weight[u][v] = w
                
        # Initialize heap
        heap = []
        for u in simulator.adj:
            for v, w in simulator.adj[u].items():
                if u < v:
                    sim = w / (cluster_size[u] * cluster_size[v])
                    heapq.heappush(heap, (-sim, u, v, cluster_size[u], cluster_size[v]))
                    
        num_clusters = n_nodes
        partitions = {}
        
        initial_infected_count = sum(1 for state in simulator.states.values() if state == 1)
        min_k = max(2, initial_infected_count)
        max_k = max(15, min_k)
        
        # Pre-populate partitions with fallback
        default_partition = {node: node for node in all_nodes}
        for temp_k in range(min_k, max_k + 1):
            partitions[temp_k] = default_partition
            
        if min_k <= num_clusters <= max_k:
            partitions[num_clusters] = {node: node_to_cluster[node] for node in all_nodes}
            
        while num_clusters > 2:
            if not heap:
                active_list = list(active_clusters)
                if len(active_list) < 2:
                    break
                c1 = active_list[0]
                c2 = active_list[1]
                neg_sim = 0.0
            else:
                neg_sim, c1, c2, s1, s2 = heapq.heappop(heap)
                
            if c1 not in active_clusters or c2 not in active_clusters:
                continue
            if cluster_size[c1] != s1 or cluster_size[c2] != s2:
                continue
                
            active_clusters.remove(c2)
            
            c2_members = cluster_members[c2]
            cluster_members[c1].extend(c2_members)
            for node in c2_members:
                node_to_cluster[node] = c1
            del cluster_members[c2]
            
            cluster_size[c1] += cluster_size[c2]
            del cluster_size[c2]
            
            neighbors = set(inter_weight[c1].keys()).union(inter_weight[c2].keys())
            neighbors.discard(c1)
            neighbors.discard(c2)
            
            for c3 in list(inter_weight[c2].keys()):
                if c3 in active_clusters:
                    if c2 in inter_weight[c3]:
                        del inter_weight[c3][c2]
                        
            for c3 in neighbors:
                if c3 not in active_clusters:
                    continue
                w_c1_c3 = inter_weight[c1].get(c3, 0.0)
                w_c2_c3 = inter_weight[c2].get(c3, 0.0)
                new_weight = w_c1_c3 + w_c2_c3
                
                inter_weight[c1][c3] = new_weight
                inter_weight[c3][c1] = new_weight
                
                sim = new_weight / (cluster_size[c1] * cluster_size[c3])
                heapq.heappush(heap, (-sim, min(c1, c3), max(c1, c3), cluster_size[c1], cluster_size[c3]))
                
            if c2 in inter_weight:
                del inter_weight[c2]
            if c2 in inter_weight[c1]:
                del inter_weight[c1][c2]
                
            num_clusters -= 1
            if min_k <= num_clusters <= max_k:
                partitions[num_clusters] = {node: node_to_cluster[node] for node in all_nodes}
                
        best_k = min_k
        max_modularity = -float('inf')
        best_node_to_community = partitions[min_k]
        
        for temp_k in range(min_k, max_k + 1):
            p = partitions[temp_k]
            comm_nodes = {}
            for node, comm in p.items():
                if comm not in comm_nodes:
                    comm_nodes[comm] = []
                comm_nodes[comm].append(node)
                
            modularity_val = 0.0
            if total_strength > 1e-9:
                for comm, members in comm_nodes.items():
                    vol = sum(node_strength.get(node, 0.0) for node in members)
                    internal_weight = 0.0
                    for u in members:
                        for v, weight in simulator.adj[u].items():
                            if p.get(v) == comm:
                                internal_weight += weight
                    modularity_val += (internal_weight / total_strength) - (vol / total_strength) ** 2
                    
            if modularity_val > max_modularity:
                max_modularity = modularity_val
                best_k = temp_k
                best_node_to_community = p
                
        # Collect inter-community edges and suppress
        inter_community_edges = []
        seen_edges = set()
        for u in simulator.adj:
            for v, w in simulator.adj[u].items():
                edge_key = tuple(sorted((u, v)))
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    u_comm = best_node_to_community[u]
                    v_comm = best_node_to_community[v]
                    if u_comm != v_comm:
                        inter_community_edges.append(((u, v), w))
                        
        inter_community_edges.sort(key=lambda x: x[1], reverse=True)
        total_edges = sum(len(neighbors) for neighbors in simulator.adj.values()) // 2
        num_to_suppress = int(total_edges * simulator.suppression_ratio)
        if num_to_suppress > 0:
            top_bridging = inter_community_edges[:num_to_suppress]
            reduction_factor = 1.0 - (simulator.suppression_percentage / 100.0)
            for (u, v), weight in top_bridging:
                suppressed_weight = weight * reduction_factor
                simulator.adj[u][v] = suppressed_weight
                simulator.adj[v][u] = suppressed_weight

