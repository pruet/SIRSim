#!/usr/bin/env python3
"""
Rigorous Verification Script for SIR Suppression Strategies
Author: Antigravity
"""

import sys
import networkx as nx
from sir_simulator import parse_netlogo_world, SIRNetworkSimulator
from suppression_strategies import SUPPRESSION_REGISTRY, run_sparse_power_iteration, run_netshield

def run_verification(file_path):
    print("=" * 70)
    print(f"LOADING BENCHMARK WORLD: {file_path}")
    print("=" * 70)
    
    globals_dict, nodes, adj = parse_netlogo_world(file_path)
    all_nodes = list(nodes.keys())
    total_edges = sum(len(neighbors) for neighbors in adj.values()) // 2
    
    initial_infected = [who for who, attrs in nodes.items() if attrs['infected']]
    if not initial_infected:
        initial_infected = [79, 224, 243] # Fallback standard outbreak
        
    print(f"Graph stats: {len(all_nodes)} nodes, {total_edges} edges, initial infected: {initial_infected}")
    print("-" * 70)
    
    ratios_to_test = [0.10, 0.20]
    percentages_to_test = [90.0, 75.0]
    
    for strategy_name, strategy_func in SUPPRESSION_REGISTRY.items():
        print(f"VERIFYING STRATEGY: '{strategy_name}'")
        
        for ratio in ratios_to_test:
            for pct in percentages_to_test:
                # Instantiate simulator
                sim = SIRNetworkSimulator(
                    nodes, adj, 
                    spread_chance=10.0, 
                    recovery_chance=5.0, 
                    resistance_chance=5.0, 
                    virus_check_frequency=1,
                    suppression_ratio=ratio,
                    suppression_percentage=pct
                )
                sim.strategy_func = strategy_func
                
                # Run reset to trigger the "setup" hook
                sim.reset(initial_infected_nodes=initial_infected)
                
                # General invariants checks
                # 1. Check original graph is unmodified
                for u in adj:
                    for v, w in adj[u].items():
                        assert sim.original_adj[u][v] == w, "Original adjacency list was modified!"
                
                # 2. Check all modified edges in sim.adj are perfectly symmetric
                for u in sim.adj:
                    for v, w in sim.adj[u].items():
                        assert sim.adj[v][u] == w, f"Asymmetry detected for edge ({u}, {v}): {w} vs {sim.adj[v][u]}"
                
                # Strategy-specific checks
                if strategy_name == "netshield_edge_suppression":
                    # NetShield strategy suppresses edges of top nodes
                    expected_nodes_count = int(len(all_nodes) * ratio)
                    reduction_factor = 1.0 - (pct / 100.0)
                    
                    # Reconstruct top central nodes via netshield
                    top_nodes = set(run_netshield(all_nodes, sim.original_adj, expected_nodes_count))
                    
                    # Check that only edges incident on top_nodes are modified
                    modified_edges = []
                    seen = set()
                    for u_node in sim.adj:
                        for v_node, w in sim.adj[u_node].items():
                            edge = tuple(sorted((u_node, v_node)))
                            if edge not in seen:
                                seen.add(edge)
                                orig = sim.original_adj[u_node][v_node]
                                if abs(orig - w) > 1e-5:
                                    expected_weight = orig * reduction_factor
                                    assert abs(w - expected_weight) < 1e-5, f"Scaling factor mismatch: {w} vs {expected_weight}"
                                    assert u_node in top_nodes or v_node in top_nodes, f"Edge {edge} modified but neither endpoint is a NetShield node!"
                                    modified_edges.append(edge)
                                    
                    # Check that all adjacent edges of top_nodes are indeed modified
                    expected_adjacent_edges = set()
                    for u_node in top_nodes:
                        for v_node in sim.original_adj[u_node]:
                            expected_adjacent_edges.add(tuple(sorted((u_node, v_node))))
                            
                    print(f"  [Ratio: {ratio:.2f}, Pct: {pct:.1f}%] Modified NetShield edges count: {len(modified_edges)} (Expected: {len(expected_adjacent_edges)})")
                    assert len(modified_edges) == len(expected_adjacent_edges), f"NetShield edges mismatch: {len(modified_edges)} != {len(expected_adjacent_edges)}"
                        
                elif strategy_name == "centrality_edge_suppression":
                    # Centrality strategy suppresses edges of top nodes
                    expected_nodes_count = int(len(all_nodes) * ratio)
                    reduction_factor = 1.0 - (pct / 100.0)
                    
                    # Reconstruct top central nodes
                    _, u_cent, node_to_idx = run_sparse_power_iteration(all_nodes, sim.original_adj)
                    sorted_nodes = sorted(all_nodes, key=lambda who: u_cent[node_to_idx[who]], reverse=True)
                    top_nodes = set(sorted_nodes[:expected_nodes_count])
                    
                    # Check that only edges incident on top_nodes are modified
                    modified_edges = []
                    seen = set()
                    for u_node in sim.adj:
                        for v_node, w in sim.adj[u_node].items():
                            edge = tuple(sorted((u_node, v_node)))
                            if edge not in seen:
                                seen.add(edge)
                                orig = sim.original_adj[u_node][v_node]
                                if abs(orig - w) > 1e-5:
                                    expected_weight = orig * reduction_factor
                                    assert abs(w - expected_weight) < 1e-5, f"Scaling factor mismatch: {w} vs {expected_weight}"
                                    assert u_node in top_nodes or v_node in top_nodes, f"Edge {edge} modified but neither endpoint is a top central node!"
                                    modified_edges.append(edge)
                                    
                    # Check that all adjacent edges of top_nodes are indeed modified
                    expected_adjacent_edges = set()
                    for u_node in top_nodes:
                        for v_node in sim.original_adj[u_node]:
                            expected_adjacent_edges.add(tuple(sorted((u_node, v_node))))
                            
                    print(f"  [Ratio: {ratio:.2f}, Pct: {pct:.1f}%] Modified central edges count: {len(modified_edges)} (Expected: {len(expected_adjacent_edges)})")
                    assert len(modified_edges) == len(expected_adjacent_edges), f"Centrality edges mismatch: {len(modified_edges)} != {len(expected_adjacent_edges)}"
                    
                elif strategy_name == "greedy_edge_weight_suppression":
                    # Greedy strategy suppresses top fraction of highest weight edges
                    expected_edges_count = int(total_edges * ratio)
                    reduction_factor = 1.0 - (pct / 100.0)
                    
                    # Collect all modified unique undirected edges
                    modified_edges = []
                    seen = set()
                    for u in sim.adj:
                        for v, w in sim.adj[u].items():
                            edge = tuple(sorted((u, v)))
                            if edge not in seen:
                                seen.add(edge)
                                orig = sim.original_adj[u][v]
                                if abs(orig - w) > 1e-5:
                                    expected_weight = orig * reduction_factor
                                    assert abs(w - expected_weight) < 1e-5, f"Scaling factor mismatch: {w} vs {expected_weight}"
                                    modified_edges.append((edge, orig))
                                    
                    print(f"  [Ratio: {ratio:.2f}, Pct: {pct:.1f}%] Modified edges count: {len(modified_edges)} (Expected: {expected_edges_count})")
                    assert len(modified_edges) == expected_edges_count, f"Greedy edges mismatch: {len(modified_edges)} != {expected_edges_count}"
                    
                elif strategy_name == "reliable_cluster_edge_suppression":
                    # Reliable cluster suppresses inter-cluster bridging edges up to the total edge budget
                    reduction_factor = 1.0 - (pct / 100.0)
                    
                    # Detect communities in original graph
                    G = nx.Graph()
                    for u in adj:
                        for v, w in adj[u].items():
                            G.add_edge(u, v, weight=w)
                    try:
                        communities = nx.community.louvain_communities(G, weight='weight', seed=42)
                    except Exception:
                        communities = nx.community.label_propagation_communities(G)
                        
                    node_to_community = {}
                    for comm_idx, comm in enumerate(communities):
                        for node in comm:
                            node_to_community[node] = comm_idx
                            
                    # Get all inter-community edges
                    inter_edges = set()
                    for u in adj:
                        for v in adj[u]:
                            u_comm = node_to_community.get(u)
                            v_comm = node_to_community.get(v)
                            if u_comm is not None and v_comm is not None and u_comm != v_comm:
                                inter_edges.add(tuple(sorted((u, v))))
                                
                    # Collect all modified unique undirected edges
                    modified_edges = []
                    seen = set()
                    for u in sim.adj:
                        for v, w in sim.adj[u].items():
                            edge = tuple(sorted((u, v)))
                            if edge not in seen:
                                seen.add(edge)
                                orig = sim.original_adj[u][v]
                                if abs(orig - w) > 1e-5:
                                    expected_weight = orig * reduction_factor
                                    assert abs(w - expected_weight) < 1e-5, f"Scaling factor mismatch: {w} vs {expected_weight}"
                                    modified_edges.append(edge)
                                    
                    expected_edges_count = min(len(inter_edges), int(total_edges * ratio))
                    print(f"  [Ratio: {ratio:.2f}, Pct: {pct:.1f}%] Modified edges count: {len(modified_edges)} (Expected: {expected_edges_count}, Inter-cluster total: {len(inter_edges)})")
                    assert len(modified_edges) == expected_edges_count, f"Reliable cluster edges mismatch: {len(modified_edges)} != {expected_edges_count}"
                    
                    # Verify every modified edge is indeed an inter-cluster edge
                    for edge in modified_edges:
                        assert edge in inter_edges, f"Edge {edge} was modified but it is not an inter-cluster bridging edge!"
                
                # Check simulation run capability
                history = sim.run(max_steps=50)
                assert len(history) > 1, f"Simulation did not run steps properly under strategy {strategy_name}"
                
        print(f"-> Strategy '{strategy_name}' VERIFIED successfully!\n")
        
    print("=" * 70)
    print("ALL STRATEGIES SUCCESSFULLY VERIFIED AND COMPLY WITH SYSTEM INVARIANTS!")
    print("=" * 70)

if __name__ == "__main__":
    file_path = "vone_300_6_3.csv"
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    run_verification(file_path)
