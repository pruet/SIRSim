#!/usr/bin/env python3
"""
SIR Network Epidemic Batch Simulation Runner
Author: Antigravity
Version: 1.0.0 (compatible with Engine v2.15.0)

Runs comparative simulations for combinations of parameters (average degree,
initial infected, suppression ratio, and suppression percentage) specified in a 
JSON configuration file, outputting aggregated results into a single, unified CSV file.
"""

import os
import sys
import json
import csv
import time
from itertools import product

# Import components from our simulator
from sir_simulator import run_sir_simulation, parse_netlogo_world

def calculate_network_stats(file_path):
    """
    Parses a NetLogo world export CSV file to programmatically calculate
    the number of nodes, edges, and the true average degree.
    """
    try:
        globals_dict, nodes, adj = parse_netlogo_world(file_path)
        num_nodes = len(nodes)
        num_edges = sum(len(neighbors) for neighbors in adj.values()) // 2
        avg_degree = (2.0 * num_edges) / num_nodes if num_nodes > 0 else 0.0
        return num_nodes, num_edges, avg_degree
    except Exception as e:
        print(f"Warning: Could not parse network stats for '{file_path}': {e}", file=sys.stderr)
        return 0, 0, 0.0

def load_config(config_path):
    """Loads and validates the batch configuration JSON file."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file '{config_path}' does not exist.")
        
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
        
    # Required keys validation
    required_keys = ["runs", "steps", "strategies", "batch_parameters", "output_csv"]
    for key in required_keys:
        if key not in config:
            raise KeyError(f"Missing required configuration key: '{key}'")
            
    batch_params = config["batch_parameters"]
    required_batch = ["networks", "initial_infected_population", "suppression_ratio", "suppression_percentage"]
    for key in required_batch:
        if key not in batch_params:
            raise KeyError(f"Missing required batch parameter key: '{key}'")
            
    return config

def main():
    print("=" * 70)
    print("SIR Epidemic Network Simulator - Batch Simulation System")
    print("=" * 70)
    
    # Resolve config file path
    config_path = "batch_config.json"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
        
    print(f"Loading configuration from: {config_path}")
    try:
        config = load_config(config_path)
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        sys.exit(1)
        
    # Parse global settings
    runs = config["runs"]
    steps = config["steps"]
    alignment = config.get("alignment", "align")
    strategies = config["strategies"]
    vacc_fraction = config.get("vaccination_fraction", 0.10)
    quar_chance = config.get("quarantine_chance", 0.80)
    workers = config.get("workers", "all")
    
    # Extract disease parameters overrides
    disease_params = config.get("disease_params", {})
    spread_chance = disease_params.get("spread_chance", None)
    recovery_chance = disease_params.get("recovery_chance", None)
    resistance_chance = disease_params.get("resistance_chance", None)
    virus_check_frequency = disease_params.get("virus_check_frequency", None)
    
    # Extract grid parameters
    batch_params = config["batch_parameters"]
    networks_list = batch_params["networks"]
    infected_list = batch_params["initial_infected_population"]
    ratio_list = batch_params["suppression_ratio"]
    pct_list = batch_params["suppression_percentage"]
    
    output_csv = config["output_csv"]
    if not os.path.dirname(output_csv):
        os.makedirs("Results", exist_ok=True)
        output_csv = os.path.join("Results", output_csv)
    
    # pre-calculate true network degrees and resolve files
    resolved_networks = []
    print("\nPre-processing network graph files...")
    for net in networks_list:
        if isinstance(net, dict):
            filename = net["file"]
            declared_degree = net.get("average_degree", None)
        else:
            filename = net
            declared_degree = None
            
        if not os.path.exists(filename):
            datasets_path = os.path.join("Datasets", filename)
            if os.path.exists(datasets_path):
                filename = datasets_path
            else:
                print(f"  [Skip] File '{filename}' does not exist. Skipping.", file=sys.stderr)
                continue
            
        # Programmatically parse to find stats
        num_nodes, num_edges, calc_degree = calculate_network_stats(filename)
        final_degree = declared_degree if declared_degree is not None else calc_degree
        
        resolved_networks.append({
            "file": filename,
            "nodes": num_nodes,
            "edges": num_edges,
            "average_degree": final_degree
        })
        print(f"  - {filename}: {num_nodes} nodes, {num_edges} edges, true avg degree: {calc_degree:.2f} (using: {final_degree:.2f})")
        
    if not resolved_networks:
        print("Error: No valid network files found to execute. Exiting.", file=sys.stderr)
        sys.exit(1)
        
    # Generate Cartesian product combinations
    combinations = list(product(resolved_networks, infected_list, ratio_list, pct_list))
    total_simulations = len(combinations) * len(strategies)
    print(f"\nGrid Combinations Generated:")
    print(f"  - Networks: {len(resolved_networks)}")
    print(f"  - Outbreak Sizes: {len(infected_list)}")
    print(f"  - Suppression Ratios: {len(ratio_list)}")
    print(f"  - Suppression Percentages: {len(pct_list)}")
    print(f"  - Strategies per Combination: {len(strategies)}")
    print(f"  => Total simulations to run: {total_simulations}")
    print(f"  => Unified results file: {output_csv}")
    print("=" * 70)
    
    # Setup output CSV file and write header
    fieldnames = [
        'network_file', 'average_degree', 'network_nodes', 'network_edges', 
        'initial_infected', 'suppression_ratio', 'suppression_percentage', 
        'strategy', 'peak_infected', 'peak_infected_pct', 'peak_tick',
        'final_susceptible_pct', 'final_infected_pct', 'final_recovered_pct', 
        'duration', 'execution_time'
    ]
    
    # Overwrite output file with fresh header
    try:
        with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
    except Exception as e:
        print(f"Error opening output CSV file '{output_csv}' for writing: {e}", file=sys.stderr)
        sys.exit(1)
        
    start_time = time.perf_counter()
    completed_count = 0
    success_count = 0
    
    # Progressively run combinations and append results to CSV
    for combo_idx, (net_info, initial_infected, supp_ratio, supp_pct) in enumerate(combinations, 1):
        filename = net_info["file"]
        avg_deg = net_info["average_degree"]
        
        print(f"\n[Combo {combo_idx}/{len(combinations)}] Grid Node:")
        print(f"  Network: {os.path.basename(filename)} (avg degree: {avg_deg:.2f})")
        print(f"  Params: outbreak={initial_infected}, ratio={supp_ratio}, percentage={supp_pct}%")
        print("-" * 50)
        
        for strategy in strategies:
            completed_count += 1
            print(f"  ({completed_count}/{total_simulations}) Simulating strategy '{strategy}'...", end="", flush=True)
            
            sim_start = time.perf_counter()
            try:
                # Execute simulation using our engine
                avg_history, summary = run_sir_simulation(
                    file_path=filename,
                    runs=runs,
                    steps=steps,
                    alignment=alignment,
                    strategy_name=strategy,
                    suppression_ratio=supp_ratio,
                    suppression_percentage=supp_pct,
                    spread_chance=spread_chance,
                    recovery_chance=recovery_chance,
                    resistance_chance=resistance_chance,
                    virus_check_frequency=virus_check_frequency,
                    vaccination_fraction=vacc_fraction,
                    quarantine_chance=quar_chance,
                    initial_outbreak_size=initial_infected,
                    workers=workers
                )
                
                # Construct output row dict
                row_data = {
                    'network_file': os.path.basename(filename),
                    'average_degree': round(avg_deg, 4),
                    'network_nodes': net_info["nodes"],
                    'network_edges': net_info["edges"],
                    'initial_infected': initial_infected,
                    'suppression_ratio': supp_ratio,
                    'suppression_percentage': supp_pct,
                    'strategy': strategy,
                    'peak_infected': round(summary['peak_infected'], 2),
                    'peak_infected_pct': round(summary['peak_infected_pct'], 2),
                    'peak_tick': summary['peak_tick'],
                    'final_susceptible_pct': round(summary['final_susceptible_pct'], 2),
                    'final_infected_pct': round(summary['final_infected_pct'], 2),
                    'final_recovered_pct': round(summary['final_recovered_pct'], 2),
                    'duration': summary['duration'],
                    'execution_time': round(summary['execution_time'], 4)
                }
                
                # Progressively append to unified CSV file
                with open(output_csv, 'a', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writerow(row_data)
                    
                sim_duration = time.perf_counter() - sim_start
                print(f" Done ({sim_duration:.2f}s) | Peak Infected: {row_data['peak_infected']} ({row_data['peak_infected_pct']}%)")
                success_count += 1
                
            except Exception as e:
                print(f" FAILED! Error: {e}", file=sys.stderr)
                # Continue with the next strategy/combination to prevent losing progress
                continue
                
    elapsed_time = time.perf_counter() - start_time
    print("=" * 70)
    print("BATCH RUN COMPLETE!")
    print(f"  - Total Simulations Executed: {completed_count}")
    print(f"  - Successful Runs: {success_count}")
    print(f"  - Failed Runs: {completed_count - success_count}")
    print(f"  - Total Elapsed Duration: {elapsed_time:.2f} seconds ({elapsed_time/60.0:.2f} minutes)")
    print(f"  - Unified Results Saved: {os.path.abspath(output_csv)}")
    print("=" * 70)

if __name__ == "__main__":
    main()
