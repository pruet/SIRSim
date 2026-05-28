#!/usr/bin/env python3
"""
SIR Simulator on NetLogo Network Exports
Author: Antigravity

This script parses NetLogo export-world CSV files to reconstruct network graphs,
then runs a probabilistic SIR (Susceptible-Infected-Recovered/Resistant) simulation,
prints step-by-step progress, and generates high-quality infection curve plots.
"""

import csv
import random
import argparse
import sys
import os
from collections import defaultdict
import matplotlib.pyplot as plt

__version__ = "1.2.0"

def parse_node_id(value):
    """
    Parses a NetLogo turtle node ID.
    Can be formatted as '{turtle 42}' or simply '42'.
    """
    val = value.strip()
    if val.startswith("{turtle ") and val.endswith("}"):
        return int(val[len("{turtle "):-1])
    return int(val)

def parse_netlogo_world(csv_file):
    """
    Parses NetLogo export-world CSV format.
    Extracts GLOBALS, TURTLES (nodes & initial states), and LINKS (edges).
    """
    globals_dict = {}
    nodes = {}  # who -> {'infected': bool, 'resistant': bool, 'virus_check_timer': int}
    edges = []  # list of (u, v, weight)

    current_section = None
    headers = []

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                # Empty row often marks the end of a section in NetLogo exports
                continue

            first_cell = row[0].strip()

            # Detect section headers
            if first_cell in ("GLOBALS", "TURTLES", "PATCHES", "LINKS", "RANDOM STATE"):
                current_section = first_cell
                headers = []
                continue

            # Skip the first few lines of metadata or dummy sections
            if current_section is None or current_section == "RANDOM STATE" or first_cell.startswith("export-world data"):
                continue

            # Capture headers for the current section
            if not headers:
                headers = [h.strip() for h in row]
                continue

            # Process section data
            if current_section == "GLOBALS":
                for h, val in zip(headers, row):
                    globals_dict[h] = val.strip()
            
            elif current_section == "TURTLES":
                data = dict(zip(headers, row))
                if 'who' in data:
                    who = int(data['who'])
                    # Convert string values "true"/"false" to boolean
                    is_infected = data.get('infected?', 'false').strip().lower() == 'true'
                    is_resistant = data.get('resistant?', 'false').strip().lower() == 'true'
                    timer_val = data.get('virus-check-timer')
                    virus_check_timer = int(timer_val) if timer_val is not None else None
                    nodes[who] = {
                        'infected': is_infected,
                        'resistant': is_resistant,
                        'virus_check_timer': virus_check_timer
                    }

            elif current_section == "LINKS":
                data = dict(zip(headers, row))
                if 'end1' in data and 'end2' in data:
                    try:
                        u = parse_node_id(data['end1'])
                        v = parse_node_id(data['end2'])
                        w_val = data.get('weight')
                        weight = float(w_val) if w_val is not None else None
                        edges.append((u, v, weight))
                    except ValueError:
                        # Ignore rows that aren't valid node connections
                        continue

    # Standardize nodes in case some nodes exist only in links
    adj = defaultdict(dict)
    for u, v, weight in edges:
        adj[u][v] = weight
        adj[v][u] = weight

    # If TURTLES section was missing or empty, populate nodes from edges
    all_node_ids = set(nodes.keys()).union(adj.keys())
    for who in all_node_ids:
        if who not in nodes:
            nodes[who] = {'infected': False, 'resistant': False, 'virus_check_timer': None}

    return globals_dict, nodes, adj

class SIRNetworkSimulator:
    def __init__(self, nodes, adj, spread_chance, recovery_chance, resistance_chance, virus_check_frequency):
        """
        Initializes the SIR Simulator.
        State representation:
          0: Susceptible (S)
          1: Infected (I)
          2: Recovered/Resistant (R)
        """
        self.adj = adj
        self.spread_chance = spread_chance             # global spread chance (0 to 100)
        self.recovery_chance = recovery_chance / 100.0 # gamma (0.0 to 1.0)
        self.resistance_chance = resistance_chance / 100.0 # rho (0.0 to 1.0)
        self.virus_check_frequency = int(virus_check_frequency)

        # Build initial state mapping & timers
        self.states = {}
        self.timers = {}
        for who, attrs in nodes.items():
            if attrs['infected']:
                self.states[who] = 1  # Infected
            elif attrs['resistant']:
                self.states[who] = 2  # Resistant
            else:
                self.states[who] = 0  # Susceptible
            
            # Initialize virus-check-timer
            timer = attrs.get('virus_check_timer')
            if timer is None:
                timer = random.randint(0, self.virus_check_frequency - 1)
            self.timers[who] = timer

        self.history = []
        self._record_history(0, 0)

    def _record_history(self, tick, new_infections):
        counts = {0: 0, 1: 0, 2: 0}
        for state in self.states.values():
            counts[state] += 1
        self.history.append({
            'tick': tick,
            'S': counts[0],
            'I': counts[1],
            'R': counts[2],
            'new_infections': new_infections
        })

    def reset(self, initial_infected_count=None, initial_infected_nodes=None):
        """
        Resets the simulator state for a new run.
        """
        self.states = {who: 0 for who in self.timers} # Reset all to susceptible
        
        if initial_infected_nodes is not None:
            for who in initial_infected_nodes:
                self.states[who] = 1
        elif initial_infected_count is not None:
            all_ids = list(self.states.keys())
            count = min(initial_infected_count, len(all_ids))
            infected_sample = random.sample(all_ids, count)
            for who in infected_sample:
                self.states[who] = 1
        
        # Re-initialize timers randomly
        for who in self.timers:
            self.timers[who] = random.randint(0, self.virus_check_frequency - 1)

        self.history = []
        self._record_history(0, 0)

    def step(self, tick):
        """
        Runs one step of the simulation synchronously matching NetLogo's loop order.
        """
        # 1. Update check timers for all nodes
        for u in self.states:
            self.timers[u] += 1
            if self.timers[u] >= self.virus_check_frequency:
                self.timers[u] = 0

        # 2. Infection transmission
        # We loop through all infected nodes and try to infect their susceptible neighbors
        next_states = self.states.copy()
        
        for u, state in self.states.items():
            if state == 1:  # Infected
                for v, weight in self.adj[u].items():
                    if self.states[v] == 0:  # Susceptible neighbor
                        # Determine edge spread chance: link weight, falling back to global spread_chance
                        chance = weight if weight is not None else self.spread_chance
                        if random.random() < (chance / 100.0):
                            next_states[v] = 1

        # Calculate new infections strictly for statistics
        new_infections = 0
        for who, old_state in self.states.items():
            if old_state == 0 and next_states[who] == 1:
                new_infections += 1

        # 3. Recovery / Gaining Resistance
        # Note: newly infected nodes can immediately be checked if their timer is 0 (matching NetLogo)
        for u in self.states:
            state = next_states[u]
            if state == 1:  # Infected
                if self.timers[u] == 0:
                    if random.random() < self.recovery_chance:
                        if random.random() < self.resistance_chance:
                            next_states[u] = 2  # Recovered/Resistant (Immune)
                        else:
                            next_states[u] = 0  # Reverts to Susceptible (SIS style)

        self.states = next_states
        self._record_history(tick, new_infections)
        return new_infections

    def run(self, max_steps):
        """
        Runs simulation until max_steps or no infected individuals remain.
        """
        for tick in range(1, max_steps + 1):
            # Check if there are any infected nodes left
            infected_count = sum(1 for s in self.states.values() if s == 1)
            if infected_count == 0:
                break
            self.step(tick)

        return self.history

def plot_simulation(history, output_path):
    """
    Generates a premium visualization of S, I, R curves over time using Matplotlib.
    """
    ticks = [h['tick'] for h in history]
    S = [h['S'] for h in history]
    I = [h['I'] for h in history]
    R = [h['R'] for h in history]

    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    fig, ax = plt.subplots(figsize=(10, 6), dpi=150)

    # Sleek palette colors
    color_s = '#7f8c8d'  # Sleek slate grey for Susceptible
    color_i = '#e74c3c'  # Vibrant red/coral for Infected
    color_r = '#2ecc71'  # Fresh emerald green for Recovered/Resistant

    # Plot curves with clean visual styling
    ax.plot(ticks, S, label='Susceptible (S)', color=color_s, linewidth=2.5, alpha=0.9)
    ax.plot(ticks, I, label='Infected (I)', color=color_i, linewidth=2.5, alpha=0.9)
    ax.plot(ticks, R, label='Recovered/Resistant (R)', color=color_r, linewidth=2.5, alpha=0.9)

    # Optional shaded region under infected curve for impact
    ax.fill_between(ticks, I, color=color_i, alpha=0.1)

    # Design tuning
    ax.set_title('Network SIR Epidemic Simulation Curves', fontsize=14, fontweight='bold', pad=15, color='#2c3e50')
    ax.set_xlabel('Ticks (Time Steps)', fontsize=11, labelpad=10, color='#34495e')
    ax.set_ylabel('Node Count', fontsize=11, labelpad=10, color='#34495e')
    
    ax.tick_params(colors='#7f8c8d', labelsize=10)
    ax.grid(True, linestyle='--', alpha=0.5, color='#bdc3c7')
    
    # Legend formatting
    legend = ax.legend(frameon=True, facecolor='#ffffff', edgecolor='#bdc3c7', loc='upper right', fontsize=10)
    legend.get_frame().set_linewidth(0.8)

    # Display peak info on plot
    peak_infected = max(I)
    peak_tick = ticks[I.index(peak_infected)]
    ax.annotate(f'Peak Infections: {peak_infected}\n(Tick {peak_tick})',
                xy=(peak_tick, peak_infected),
                xytext=(peak_tick + (max(ticks)*0.05), peak_infected * 0.9),
                arrowprops=dict(facecolor='#2c3e50', arrowstyle='->', lw=1.0),
                fontsize=9.5, fontweight='semibold', color='#2c3e50',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#f8f9fa', edgecolor='#bdc3c7', alpha=0.9))

    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight')
    plt.close()
    print(f"\n[Visual] Premium simulation curve chart saved to: {output_path}")

def main():
    parser = argparse.ArgumentParser(
        description="Run an SIR epidemic simulation on a network imported from a NetLogo export-world CSV file."
    )
    parser.add_argument("file", help="Path to the NetLogo export-world CSV file.")
    parser.add_argument("-s", "--spread-chance", type=float, help="Virus spread chance (0 to 100). If omitted, read from GLOBALS.")
    parser.add_argument("-r", "--recovery-chance", type=float, help="Recovery chance (0 to 100). If omitted, read from GLOBALS.")
    parser.add_argument("-g", "--resistance-chance", type=float, help="Gain resistance chance (0 to 100). If omitted, read from GLOBALS or defaults to 100 (standard SIR).")
    parser.add_argument("-t", "--steps", type=int, default=500, help="Maximum number of ticks to simulate (default: 500).")
    parser.add_argument("-o", "--output-plot", default="sir_simulation_curves.png", help="Filename of the saved plot (default: sir_simulation_curves.png).")
    parser.add_argument("-n", "--runs", type=int, default=50, help="Number of simulation runs to average (default: 50).")

    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"Error: File '{args.file}' does not exist.", file=sys.stderr)
        sys.exit(1)

    print("=" * 60)
    print(f"Loading NetLogo world from: {args.file}")
    try:
        globals_dict, nodes, adj = parse_netlogo_world(args.file)
    except Exception as e:
        print(f"Error parsing file: {e}", file=sys.stderr)
        sys.exit(1)

    num_nodes = len(nodes)
    num_edges = sum(len(neighbors) for neighbors in adj.values()) // 2
    initial_infected = sum(1 for n in nodes.values() if n['infected'])
    initial_resistant = sum(1 for n in nodes.values() if n['resistant'])

    print(f"Graph loaded successfully:")
    print(f"  - Nodes: {num_nodes}")
    print(f"  - Edges: {num_edges}")
    print(f"  - Initial Infected: {initial_infected}")
    print(f"  - Initial Resistant: {initial_resistant}")
    print("-" * 60)

    # Determine simulation parameters
    # Fallbacks if GLOBALS not found or missing specific headers
    fallback_spread = 10.0
    fallback_recovery = 5.0
    fallback_resistance = 5.0  # Default to 5% resistance chance (matching NetLogo setup default)
    fallback_frequency = 1        # Default check frequency is 1

    spread_val = args.spread_chance
    if spread_val is None:
        raw_val = globals_dict.get('virus-spread-chance')
        spread_val = float(raw_val) if raw_val is not None else fallback_spread
        print(f"  * Using file-defined 'virus-spread-chance': {spread_val}%")
    else:
        print(f"  * Using command-override spread chance: {spread_val}%")

    recovery_val = args.recovery_chance
    if recovery_val is None:
        raw_val = globals_dict.get('recovery-chance')
        recovery_val = float(raw_val) if raw_val is not None else fallback_recovery
        print(f"  * Using file-defined 'recovery-chance': {recovery_val}%")
    else:
        print(f"  * Using command-override recovery chance: {recovery_val}%")

    resistance_val = args.resistance_chance
    if resistance_val is None:
        raw_val = globals_dict.get('gain-resistance-chance')
        resistance_val = float(raw_val) if raw_val is not None else fallback_resistance
        print(f"  * Using file-defined 'gain-resistance-chance': {resistance_val}%")
    else:
        print(f"  * Using command-override resistance chance: {resistance_val}%")

    # Parse virus-check-frequency
    raw_val = globals_dict.get('virus-check-frequency')
    frequency_val = int(float(raw_val)) if raw_val is not None else fallback_frequency
    print(f"  * Using file-defined 'virus-check-frequency': {frequency_val}")

    print("=" * 60)
    
    simulator = SIRNetworkSimulator(nodes, adj, spread_val, recovery_val, resistance_val, frequency_val)

    # Resolve initial infected count/nodes
    initial_infected_count = sum(1 for n in nodes.values() if n['infected'])
    if initial_infected_count == 0:
        raw_outbreak = globals_dict.get('initial-outbreak-size')
        initial_infected_count = int(raw_outbreak) if raw_outbreak is not None else 3

    # Run loop for multiple simulations
    all_histories = []
    
    for run_idx in range(args.runs):
        if args.runs == 1:
            # For 1 run, use the exact parsed states from the CSV
            initial_nodes = [who for who, attrs in nodes.items() if attrs['infected']]
            simulator.reset(initial_infected_nodes=initial_nodes)
        else:
            # For multiple runs, randomize the initial outbreak
            simulator.reset(initial_infected_count=initial_infected_count)
        
        # Run simulator until end or max_steps
        simulator.run(args.steps)
        all_histories.append(simulator.history)

    # Determine the minimum history length among all runs to truncate
    min_length = min(len(hist) for hist in all_histories)

    # Compute averaged histories up to min_length
    avg_history = []
    for t in range(min_length):
        s_sum = sum(h[t]['S'] for h in all_histories)
        i_sum = sum(h[t]['I'] for h in all_histories)
        r_sum = sum(h[t]['R'] for h in all_histories)
        new_inf_sum = sum(h[t]['new_infections'] for h in all_histories)
        
        avg_history.append({
            'tick': t,
            'S': s_sum / args.runs,
            'I': i_sum / args.runs,
            'R': r_sum / args.runs,
            'new_infections': new_inf_sum / args.runs
        })

    # Print averaged results in real time
    print(f"Running SIR Simulation (averaged over {args.runs} runs, truncated to {min_length - 1} steps)...")
    print(f"{'Tick':<6} | {'Susceptible':<12} | {'Infected':<10} | {'Recovered':<10} | {'New Infections':<14}")
    print("-" * 60)
    for t in range(min_length):
        hist = avg_history[t]
        print(f"{t:<6} | {hist['S']:<12.2f} | {hist['I']:<10.2f} | {hist['R']:<10.2f} | {hist['new_infections']:<14.2f}")
    
    print("-" * 60)
    print(f"Simulation ended: Truncated at first run termination (Step {min_length - 1}).")
    print("=" * 60)
    
    # Generate visualization
    try:
        plot_simulation(avg_history, args.output_plot)
    except Exception as e:
        print(f"Warning: Could not generate visualization plot: {e}", file=sys.stderr)

    print("Simulation Complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
