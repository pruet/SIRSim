#!/usr/bin/env python3
"""
SIR Simulator on NetLogo Network Exports
Author: Antigravity

This script parses NetLogo export-world CSV files to reconstruct network graphs,
then runs a probabilistic SIR (Susceptible-Infected-Recovered/Resistant) simulation,
prints step-by-step progress, and generates high-quality infection curve plots.
Supports evaluating and comparing multiple static and dynamic suppression strategies.
"""

import csv
import random
import argparse
import sys
import os
from collections import defaultdict
import matplotlib.pyplot as plt

__version__ = "2.18.0"

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
                if 'end1' in data and 'end2' in data and 'weight' in data:
                    try:
                        u = parse_node_id(data['end1'])
                        v = parse_node_id(data['end2'])
                        weight = float(data['weight'])
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

# ==============================================================================
# SUPPRESSION STRATEGIES IMPORT
# ==============================================================================
from suppression_strategies import SUPPRESSION_REGISTRY, register_strategy

def run_single_mc_run(
    nodes,
    adj,
    spread_val,
    recovery_val,
    resistance_val,
    frequency_val,
    vaccination_fraction,
    quarantine_chance,
    suppression_ratio,
    suppression_percentage,
    strategy_name,
    steps,
    initial_infected_nodes,
    run_seed=None
):
    """
    Worker function to run a single independent Monte Carlo SIR simulation.
    Executed in parallel processes.
    """
    from suppression_strategies import SUPPRESSION_REGISTRY
    
    sim = SIRNetworkSimulator(
        nodes=nodes,
        original_adj=adj,
        spread_chance=spread_val,
        recovery_chance=recovery_val,
        resistance_chance=resistance_val,
        virus_check_frequency=frequency_val,
        vaccination_fraction=vaccination_fraction,
        quarantine_chance=quarantine_chance,
        suppression_ratio=suppression_ratio,
        suppression_percentage=suppression_percentage
    )
    
    if strategy_name == "baseline":
        sim.strategy_func = None
    else:
        sim.strategy_func = SUPPRESSION_REGISTRY[strategy_name]
        
    import random
    if run_seed is not None:
        random.seed(run_seed)
        
    sim.reset(initial_infected_nodes=initial_infected_nodes)
    sim.run(steps)
    return sim.history

class SIRNetworkSimulator:
    def __init__(self, nodes, original_adj, spread_chance, recovery_chance, resistance_chance, virus_check_frequency, vaccination_fraction=0.1, quarantine_chance=0.8, suppression_ratio=None, suppression_percentage=90.0):
        """
        Initializes the SIR Simulator.
        State representation:
          0: Susceptible (S)
          1: Infected (I)
          2: Recovered/Resistant (R)
        """
        self.original_adj = original_adj
        # Deep copy original_adj to self.adj, ensuring all nodes (including isolated ones) have an entry
        self.adj = {u: dict(original_adj.get(u, {})) for u in nodes}
        
        self.spread_chance = spread_chance             # global spread chance (0 to 100)
        self.recovery_chance = recovery_chance / 100.0 # gamma (0.0 to 1.0)
        self.resistance_chance = resistance_chance / 100.0 # rho (0.0 to 1.0)
        self.virus_check_frequency = int(virus_check_frequency)
        self.vaccination_fraction = vaccination_fraction
        self.quarantine_chance = quarantine_chance
        
        if suppression_ratio is None:
            self.suppression_ratio = vaccination_fraction
        else:
            self.suppression_ratio = suppression_ratio
            
        self.suppression_percentage = suppression_percentage
        self.strategy_func = None

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

    @classmethod
    def from_file(
        cls,
        file_path,
        strategy_name="baseline",
        suppression_ratio=None,
        suppression_percentage=90.0,
        spread_chance=None,
        recovery_chance=None,
        resistance_chance=None,
        virus_check_frequency=None,
        vaccination_fraction=0.1,
        quarantine_chance=0.8,
        initial_outbreak_size=None
    ):
        """
        Convenience constructor to instantiate SIRNetworkSimulator directly from a NetLogo CSV file.
        Reads parameters from the CSV's GLOBALS section if they are not explicitly overridden.
        
        Parameters:
            file_path (str): Path to the NetLogo export-world CSV file.
            strategy_name (str): Suppression strategy name (e.g. 'baseline', 'netshield_edge_suppression', etc.).
            suppression_ratio (float): Fraction of nodes/edges targeted (default: None, which maps to vaccination_fraction).
            suppression_percentage (float): Weight reduction percentage for edge strategies (default: 90.0).
            spread_chance (float): Spread chance override. If None, reads from CSV.
            recovery_chance (float): Recovery chance override. If None, reads from CSV.
            resistance_chance (float): Gain resistance chance override. If None, reads from CSV.
            virus_check_frequency (int): Virus check timer frequency override. If None, reads from CSV.
            vaccination_fraction (float): Default vaccination fraction if suppression_ratio is None (default: 0.1).
            quarantine_chance (float): Probability of isolating an infected node per step (default: 0.8).
            initial_outbreak_size (int): Override for the initial infected outbreak size.
            
        Returns:
            SIRNetworkSimulator: An instantiated, strategy-configured simulator.
        """
        globals_dict, nodes, adj = parse_netlogo_world(file_path)
        
        # Handle parameter fallbacks from CSV globals
        fallback_spread = 10.0
        fallback_recovery = 5.0
        fallback_resistance = 5.0
        fallback_frequency = 1
        
        if spread_chance is None:
            raw_val = globals_dict.get('virus-spread-chance')
            spread_val = float(raw_val) if raw_val is not None else fallback_spread
        else:
            spread_val = spread_chance
            
        if recovery_chance is None:
            raw_val = globals_dict.get('recovery-chance')
            recovery_val = float(raw_val) if raw_val is not None else fallback_recovery
        else:
            recovery_val = recovery_chance
            
        if resistance_chance is None:
            raw_val = globals_dict.get('gain-resistance-chance')
            resistance_val = float(raw_val) if raw_val is not None else fallback_resistance
        else:
            resistance_val = resistance_chance
            
        if virus_check_frequency is None:
            raw_val = globals_dict.get('virus-check-frequency')
            frequency_val = int(float(raw_val)) if raw_val is not None else fallback_frequency
        else:
            frequency_val = virus_check_frequency
            
        # Instantiate
        simulator = cls(
            nodes=nodes,
            original_adj=adj,
            spread_chance=spread_val,
            recovery_chance=recovery_val,
            resistance_chance=resistance_val,
            virus_check_frequency=frequency_val,
            vaccination_fraction=vaccination_fraction,
            quarantine_chance=quarantine_chance,
            suppression_ratio=suppression_ratio,
            suppression_percentage=suppression_percentage
        )
        
        # Configure strategy
        if strategy_name == "baseline":
            simulator.strategy_func = None
        else:
            if strategy_name not in SUPPRESSION_REGISTRY:
                raise ValueError(f"Invalid strategy '{strategy_name}'. Available: {['baseline'] + list(SUPPRESSION_REGISTRY.keys())}")
            simulator.strategy_func = SUPPRESSION_REGISTRY[strategy_name]
            
        # Apply initial outbreak override if provided (which runs the strategy setup)
        if initial_outbreak_size is not None:
            simulator.reset(initial_infected_count=initial_outbreak_size)
        else:
            # Run setup hook of suppression strategy if set
            if simulator.strategy_func is not None:
                simulator.strategy_func(simulator, "setup")
            
        return simulator

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
        # Restore original adjacency list for a fresh start, ensuring all nodes have an entry
        self.adj = {u: dict(self.original_adj.get(u, {})) for u in self.timers}
        
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

        # Run setup hook of suppression strategy if set
        if self.strategy_func is not None:
            self.strategy_func(self, "setup")

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
                        # Determine edge spread chance: link weight
                        chance = weight
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
        
        # Run step hook of suppression strategy if set
        if self.strategy_func is not None:
            self.strategy_func(self, "step", tick=tick, new_infections=new_infections)

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
    ax.annotate(f'Peak Infections: {peak_infected:.1f}\n(Tick {peak_tick})',
                xy=(peak_tick, peak_infected),
                xytext=(peak_tick + (max(ticks)*0.05), peak_infected * 0.9),
                arrowprops=dict(facecolor='#2c3e50', arrowstyle='->', lw=1.0),
                fontsize=9.5, fontweight='semibold', color='#2c3e50',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#f8f9fa', edgecolor='#bdc3c7', alpha=0.9))

    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight')
    plt.close()
    print(f"\n[Visual] Premium simulation curve chart saved to: {output_path}")

def plot_comparison(all_avg_histories, output_path):
    """
    Generates a premium comparison plot of Infected (I) curves for different strategies.
    """
    ticks_list = []
    for name, history in all_avg_histories.items():
        if history:
            ticks_list.append(max(h['tick'] for h in history))
    max_tick = max(ticks_list) if ticks_list else 100

    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    fig, ax = plt.subplots(figsize=(12, 7), dpi=150)

    # Sleek modern palette mapping for all registered and default strategies
    colors = {
        'baseline': '#e74c3c',                              # Red
        'random_vaccination': '#95a5a6',                     # Slate Grey
        'high_degree_vaccination': '#34495e',                 # Wet Asphalt (Dark Grey/Blue)
        'acquaintance_vaccination': '#7f8c8d',                # Asbestos (Medium Grey)
        'infected_quarantine': '#27ae60',                     # Dark Emerald Green
        'netshield_edge_suppression': '#ad1457',            # Deep Berry/Magenta
        'centrality_edge_suppression': '#3498db',           # Bright Blue
        'greedy_edge_weight_suppression': '#f1c40f',        # Bright Gold/Yellow
        'reliable_cluster_edge_suppression': '#9b59b6',      # Vibrant Amethyst/Purple
        'size_constrained_mpf_suppression': '#e67e22',       # Orange
        'average_linkage_mpf_suppression': '#2ecc71',        # Emerald Green
    }
    # Fallback colors for other user-defined strategies
    extra_colors = ['#16a085', '#27ae60', '#2980b9', '#8e44ad', '#2c3e50']

    color_idx = 0
    for name, history in all_avg_histories.items():
        ticks = [h['tick'] for h in history]
        I = [h['I'] for h in history]
        
        color = colors.get(name)
        if color is None:
            color = extra_colors[color_idx % len(extra_colors)]
            color_idx += 1
            
        label_name = name.replace('_', ' ').title()
        ax.plot(ticks, I, label=label_name, color=color, linewidth=2.5, alpha=0.9)
        ax.fill_between(ticks, I, color=color, alpha=0.05)

    ax.set_title('Epidemic Curve Comparison under Suppression Strategies', fontsize=14, fontweight='bold', pad=15, color='#2c3e50')
    ax.set_xlabel('Ticks (Time Steps)', fontsize=11, labelpad=10, color='#34495e')
    ax.set_ylabel('Averaged Infected Count', fontsize=11, labelpad=10, color='#34495e')
    
    ax.tick_params(colors='#7f8c8d', labelsize=10)
    ax.grid(True, linestyle='--', alpha=0.5, color='#bdc3c7')
    ax.set_xlim(0, max_tick)
    
    legend = ax.legend(frameon=True, facecolor='#ffffff', edgecolor='#bdc3c7', loc='upper right', fontsize=10)
    legend.get_frame().set_linewidth(0.8)

    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight')
    plt.close()
    print(f"\n[Visual] Premium comparison curve chart saved to: {output_path}")

def run_sir_simulation(
    file_path,
    runs=50,
    steps=500,
    alignment="align",
    strategy_name="baseline",
    suppression_ratio=None,
    suppression_percentage=90.0,
    spread_chance=None,
    recovery_chance=None,
    resistance_chance=None,
    virus_check_frequency=None,
    vaccination_fraction=0.10,
    quarantine_chance=0.80,
    initial_outbreak_size=None,
    workers=None
):
    """
    High-level API to run a multi-run Monte Carlo SIR simulation on a NetLogo CSV graph.
    
    Parameters:
        file_path (str): Path to the NetLogo export-world CSV file.
        runs (int): Number of independent simulation runs to average (default: 50).
        steps (int): Maximum number of ticks to simulate (default: 500).
        alignment (str): 'align' or 'truncate' time alignment mode for averaging (default: 'align').
        strategy_name (str): Suppression strategy name (e.g. 'baseline', 'netshield_edge_suppression', etc.).
        suppression_ratio (float): Fraction of nodes/edges targeted (default: None, which maps to vaccination_fraction).
        suppression_percentage (float): Weight reduction percentage for edge strategies (default: 90.0).
        spread_chance (float): Spread chance override. If None, reads from CSV.
        recovery_chance (float): Recovery chance override. If None, reads from CSV.
        resistance_chance (float): Gain resistance chance override. If None, reads from CSV.
        virus_check_frequency (int): Virus check timer frequency override. If None, reads from CSV.
        vaccination_fraction (float): Default vaccination fraction if suppression_ratio is None (default: 0.10).
        quarantine_chance (float): Probability of isolating an infected node per step (default: 0.80).
        initial_outbreak_size (int): Override for the initial infected outbreak size. If None, reads from CSV.
        workers (int or str): Number of parallel processes to use (None/1 for sequential, -1/'all' for all CPU cores, or positive integer to limit processes).
        
    Returns:
        tuple: (avg_history, summary_metrics)
            - avg_history (list of dict): The step-by-step averaged history (contains tick, S, I, R, and new_infections).
            - summary_metrics (dict): Standard evaluation metrics including peak infections, final percentages, and duration.
    """
    import os
    import sys
    
    resolved_path = file_path
    if not os.path.exists(resolved_path):
        datasets_path = os.path.join("Datasets", resolved_path)
        if os.path.exists(datasets_path):
            resolved_path = datasets_path
        else:
            raise FileNotFoundError(f"Error: File '{file_path}' does not exist (checked root and 'Datasets/' folder).")
    file_path = resolved_path
        
    globals_dict, nodes, adj = parse_netlogo_world(file_path)
    num_nodes = len(nodes)
    
    # Handle parameter fallbacks from CSV globals
    fallback_spread = 10.0
    fallback_recovery = 5.0
    fallback_resistance = 5.0
    fallback_frequency = 1
    
    if spread_chance is None:
        raw_val = globals_dict.get('virus-spread-chance')
        spread_val = float(raw_val) if raw_val is not None else fallback_spread
    else:
        spread_val = spread_chance
        
    if recovery_chance is None:
        raw_val = globals_dict.get('recovery-chance')
        recovery_val = float(raw_val) if raw_val is not None else fallback_recovery
    else:
        recovery_val = recovery_chance
        
    if resistance_chance is None:
        raw_val = globals_dict.get('gain-resistance-chance')
        resistance_val = float(raw_val) if raw_val is not None else fallback_resistance
    else:
        resistance_val = resistance_chance
        
    if virus_check_frequency is None:
        raw_val = globals_dict.get('virus-check-frequency')
        frequency_val = int(float(raw_val)) if raw_val is not None else fallback_frequency
    else:
        frequency_val = virus_check_frequency
        
    # Instantiate simulator
    simulator = SIRNetworkSimulator(
        nodes, adj, spread_val, recovery_val, resistance_val, frequency_val,
        vaccination_fraction=vaccination_fraction,
        quarantine_chance=quarantine_chance,
        suppression_ratio=suppression_ratio,
        suppression_percentage=suppression_percentage
    )
    
    # Resolve initial infected outbreak size
    if initial_outbreak_size is not None:
        initial_infected_count = initial_outbreak_size
    else:
        initial_infected_count = sum(1 for n in nodes.values() if n['infected'])
        if initial_infected_count == 0:
            raw_outbreak = globals_dict.get('initial-outbreak-size')
            initial_infected_count = int(raw_outbreak) if raw_outbreak is not None else 3
        
    # Pre-generate initial outbreaks to ensure identical outbreaks per run
    # Set seed to ensure consistency across separate strategy evaluations
    random.seed(1002)
    initial_outbreaks = []
    all_node_ids = list(nodes.keys())
    for run_idx in range(runs):
        if runs == 1 and initial_outbreak_size is None:
            initial_nodes = [who for who, attrs in nodes.items() if attrs['infected']]
            if not initial_nodes:
                initial_nodes = random.sample(all_node_ids, min(initial_infected_count, len(all_node_ids)))
        else:
            initial_nodes = random.sample(all_node_ids, min(initial_infected_count, len(all_node_ids)))
        initial_outbreaks.append(initial_nodes)
        
    # Configure strategy
    if strategy_name == "baseline":
        simulator.strategy_func = None
    else:
        if strategy_name not in SUPPRESSION_REGISTRY:
            raise ValueError(f"Invalid strategy '{strategy_name}'. Available: {['baseline'] + list(SUPPRESSION_REGISTRY.keys())}")
        simulator.strategy_func = SUPPRESSION_REGISTRY[strategy_name]
        
    # Run Monte Carlo simulations
    import time
    start_time = time.perf_counter()
    
    all_histories = []
    
    # Resolve workers parameter
    use_parallel = False
    max_workers = None
    
    if workers is not None:
        if isinstance(workers, bool):
            if workers:
                use_parallel = True
                max_workers = None
        elif isinstance(workers, int):
            if workers > 1:
                use_parallel = True
                max_workers = workers
            elif workers == -1:
                use_parallel = True
                max_workers = None
        elif isinstance(workers, str):
            if workers.lower() == "all":
                use_parallel = True
                max_workers = None
            else:
                try:
                    w_int = int(workers)
                    if w_int > 1:
                        use_parallel = True
                        max_workers = w_int
                    elif w_int == -1:
                        use_parallel = True
                        max_workers = None
                except ValueError:
                    pass

    if use_parallel:
        from concurrent.futures import ProcessPoolExecutor
        futures = []
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            for run_idx in range(runs):
                futures.append(
                    executor.submit(
                        run_single_mc_run,
                        nodes,
                        adj,
                        spread_val,
                        recovery_val,
                        resistance_val,
                        frequency_val,
                        vaccination_fraction,
                        quarantine_chance,
                        suppression_ratio,
                        suppression_percentage,
                        strategy_name,
                        steps,
                        initial_outbreaks[run_idx],
                        1002 + run_idx
                    )
                )
            for fut in futures:
                all_histories.append(fut.result())
    else:
        for run_idx in range(runs):
            random.seed(1002 + run_idx)
            simulator.reset(initial_infected_nodes=initial_outbreaks[run_idx])
            simulator.run(steps)
            all_histories.append(simulator.history)
            
    execution_time = time.perf_counter() - start_time
        
    # Average history
    avg_history = []
    if alignment == "align":
        max_length = max(len(hist) for hist in all_histories)
        padded_histories = []
        for hist in all_histories:
            padded = list(hist)
            while len(padded) < max_length:
                t = len(padded)
                last = padded[-1]
                padded.append({
                    'tick': t,
                    'S': last['S'],
                    'I': last['I'],
                    'R': last['R'],
                    'new_infections': 0.0
                })
            padded_histories.append(padded)

        for t in range(max_length):
            s_sum = sum(h[t]['S'] for h in padded_histories)
            i_sum = sum(h[t]['I'] for h in padded_histories)
            r_sum = sum(h[t]['R'] for h in padded_histories)
            new_inf_sum = sum(h[t]['new_infections'] for h in padded_histories)
            
            avg_history.append({
                'tick': t,
                'S': s_sum / runs,
                'I': i_sum / runs,
                'R': r_sum / runs,
                'new_infections': new_inf_sum / runs
            })
    else:
        min_length = min(len(hist) for hist in all_histories)
        for t in range(min_length):
            s_sum = sum(h[t]['S'] for h in all_histories)
            i_sum = sum(h[t]['I'] for h in all_histories)
            r_sum = sum(h[t]['R'] for h in all_histories)
            new_inf_sum = sum(h[t]['new_infections'] for h in all_histories)
            
            avg_history.append({
                'tick': t,
                'S': s_sum / runs,
                'I': i_sum / runs,
                'R': r_sum / runs,
                'new_infections': new_inf_sum / runs
            })
            
    # Compute summary metrics
    S_end = avg_history[-1]['S']
    I_end = avg_history[-1]['I']
    R_end = avg_history[-1]['R']
    
    I_vals = [h['I'] for h in avg_history]
    peak_infected = max(I_vals)
    peak_tick = I_vals.index(peak_infected)
    duration = len(avg_history) - 1
    
    summary = {
        'strategy': strategy_name,
        'peak_infected': peak_infected,
        'peak_infected_pct': (peak_infected / num_nodes) * 100.0 if num_nodes > 0 else 0.0,
        'peak_tick': peak_tick,
        'final_susceptible_pct': (S_end / num_nodes) * 100.0 if num_nodes > 0 else 0.0,
        'final_infected_pct': (I_end / num_nodes) * 100.0 if num_nodes > 0 else 0.0,
        'final_recovered_pct': (R_end / num_nodes) * 100.0 if num_nodes > 0 else 0.0,
        'duration': duration,
        'execution_time': execution_time,
    }
    
    return avg_history, summary

def main():
    parser = argparse.ArgumentParser(
        description="Run an SIR epidemic simulation comparing different suppression strategies on imported networks."
    )
    parser.add_argument("file", help="Path to the NetLogo export-world CSV file.")
    parser.add_argument("-s", "--spread-chance", type=float, help="Virus spread chance (0 to 100). If omitted, read from GLOBALS.")
    parser.add_argument("-r", "--recovery-chance", type=float, help="Recovery chance (0 to 100). If omitted, read from GLOBALS.")
    parser.add_argument("-g", "--resistance-chance", type=float, help="Gain resistance chance (0 to 100). If omitted, read from GLOBALS or defaults to 100 (standard SIR).")
    parser.add_argument("-f", "--virus-check-frequency", type=int, help="Virus check frequency (1 or greater). If omitted, read from GLOBALS.")
    parser.add_argument("-t", "--steps", type=int, default=500, help="Maximum number of ticks to simulate (default: 500).")
    parser.add_argument("-o", "--output-plot", help="Filename of the saved plot (default: sir_simulation_curves.png or sir_comparison_curves.png).")
    parser.add_argument("-n", "--runs", type=int, default=50, help="Number of simulation runs to average (default: 50).")
    parser.add_argument("-i", "--initial-outbreak-size", type=int, help="Initial number of infected nodes (outbreak size). If omitted, read from GLOBALS or uses turtles in CSV.")
    parser.add_argument(
        "-j", "--parallel",
        nargs="?",
        const="all",
        default=None,
        help="Enable parallel execution. Optionally specify the number of worker processes (e.g. -j or -j 4)."
    )
    parser.add_argument(
        "-a", "--alignment",
        choices=["align", "truncate"],
        default="align",
        help="Time alignment mechanism for multi-run averaging: 'align' (pad early-terminated runs with final state to max length) or 'truncate' (truncate averaging at first run termination) (default: align)."
    )
    parser.add_argument(
        "-S", "--strategies",
        nargs="+",
        default=["all"],
        help="List of suppression strategies to evaluate. Options: 'baseline', 'random_vaccination', 'high_degree_vaccination', 'acquaintance_vaccination', 'infected_quarantine', or 'all' (default: all)."
    )
    parser.add_argument(
        "-v", "--vaccination-fraction",
        type=float,
        default=0.10,
        help="Fraction of nodes to vaccinate in vaccination strategies (default: 0.10)."
    )
    parser.add_argument(
        "-q", "--quarantine-chance",
        type=float,
        default=0.80,
        help="Probability of isolating an infected node per step in infected_quarantine (default: 0.80)."
    )
    parser.add_argument(
        "-p", "--suppression-ratio",
        type=float,
        default=None,
        help="Fraction of nodes/edges to suppress (default: None, which maps to --vaccination-fraction)."
    )
    parser.add_argument(
        "-P", "--suppression-percentage",
        type=float,
        default=90.0,
        help="Percentage of weight reduction for suppressed edges (default: 90.0, i.e., 90% reduction)."
    )
    parser.add_argument(
        "-c", "--output-csv",
        help="Filename of the saved CSV evaluation summary (default: none)."
    )

    args = parser.parse_args()

    file_path = args.file
    if not os.path.exists(file_path):
        datasets_path = os.path.join("Datasets", file_path)
        if os.path.exists(datasets_path):
            file_path = datasets_path
        else:
            print(f"Error: File '{args.file}' does not exist (checked root and 'Datasets/' folder).", file=sys.stderr)
            sys.exit(1)
    args.file = file_path

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

    # Resolve parameters for naming suffix
    fallback_spread = 10.0
    fallback_recovery = 5.0
    
    spread_val = args.spread_chance if args.spread_chance is not None else (
        float(globals_dict.get('virus-spread-chance')) if globals_dict.get('virus-spread-chance') is not None else fallback_spread
    )
    recovery_val = args.recovery_chance if args.recovery_chance is not None else (
        float(globals_dict.get('recovery-chance')) if globals_dict.get('recovery-chance') is not None else fallback_recovery
    )
    supp_ratio_val = args.suppression_ratio if args.suppression_ratio is not None else args.vaccination_fraction

    def fmt_num(val):
        if val is None:
            return "None"
        if isinstance(val, float) and val.is_integer():
            return str(int(val))
        return str(val)

    param_suffix = f"s{fmt_num(spread_val)}_r{fmt_num(recovery_val)}_p{fmt_num(supp_ratio_val)}_P{fmt_num(args.suppression_percentage)}_v{fmt_num(args.vaccination_fraction)}_q{fmt_num(args.quarantine_chance)}"

    def add_param_suffix(filepath, suffix):
        if not filepath:
            return filepath
        dir_name = os.path.dirname(filepath)
        base_name = os.path.basename(filepath)
        base, ext = os.path.splitext(base_name)
        parameterized_name = f"{base}_{suffix}{ext}"
        if not dir_name:
            os.makedirs("Results", exist_ok=True)
            return os.path.join("Results", parameterized_name)
        else:
            return os.path.join(dir_name, parameterized_name)

    # Resolve strategies to run
    available_strategies = ["baseline"] + list(SUPPRESSION_REGISTRY.keys())
    selected_strategies = args.strategies
    if "all" in selected_strategies:
        selected_strategies = available_strategies
    else:
        invalid = [s for s in selected_strategies if s not in available_strategies]
        if invalid:
            print(f"Error: Invalid strategies: {invalid}. Available: {available_strategies}", file=sys.stderr)
            sys.exit(1)

    all_avg_histories = {}
    summary_data = []

    # Run loop for selected strategies
    for strategy_name in selected_strategies:
        print(f"Evaluating strategy: '{strategy_name}'...")
        try:
            avg_history, summary = run_sir_simulation(
                file_path=args.file,
                runs=args.runs,
                steps=args.steps,
                alignment=args.alignment,
                strategy_name=strategy_name,
                suppression_ratio=args.suppression_ratio,
                suppression_percentage=args.suppression_percentage,
                spread_chance=args.spread_chance,
                recovery_chance=args.recovery_chance,
                resistance_chance=args.resistance_chance,
                virus_check_frequency=args.virus_check_frequency,
                vaccination_fraction=args.vaccination_fraction,
                quarantine_chance=args.quarantine_chance,
                initial_outbreak_size=args.initial_outbreak_size,
                workers=args.parallel
            )
            all_avg_histories[strategy_name] = avg_history
            summary_data.append(summary)
        except Exception as e:
            print(f"Error executing strategy '{strategy_name}': {e}", file=sys.stderr)
            sys.exit(1)

    # Print step-by-step progress for 1 strategy, or summary table for multiple
    if len(selected_strategies) == 1:
        strat_name = selected_strategies[0]
        avg_history = all_avg_histories[strat_name]
        print("\n" + "=" * 60)
        if args.alignment == "align":
            print(f"Running SIR Simulation '{strat_name}' (averaged over {args.runs} runs, time-aligned to {len(avg_history)-1} steps)...")
        else:
            print(f"Running SIR Simulation '{strat_name}' (averaged over {args.runs} runs, truncated to {len(avg_history)-1} steps)...")
        print(f"{'Tick':<6} | {'Susceptible':<12} | {'Infected':<10} | {'Recovered':<10} | {'New Infections':<14}")
        print("-" * 60)
        for t in range(len(avg_history)):
            hist = avg_history[t]
            print(f"{t:<6} | {hist['S']:<12.2f} | {hist['I']:<10.2f} | {hist['R']:<10.2f} | {hist['new_infections']:<14.2f}")
        print("-" * 60)
        if args.alignment == "align":
            print(f"Simulation ended: Time-aligned to longest run duration (Step {len(avg_history)-1}).")
        else:
            print(f"Simulation ended: Truncated at first run termination (Step {len(avg_history)-1}).")
        print("=" * 60)

        # Generate single strategy curve visualization
        default_plot = args.output_plot if args.output_plot is not None else "sir_simulation_curves.png"
        output_plot_path = add_param_suffix(default_plot, param_suffix)
        try:
            plot_simulation(avg_history, output_plot_path)
        except Exception as e:
            print(f"Warning: Could not generate visualization plot: {e}", file=sys.stderr)
    else:
        # Print comparison summary table
        print("\n" + "=" * 130)
        print("SUPPRESSION STRATEGY EVALUATION SUMMARY")
        print("=" * 130)
        print(f"{'Strategy Name':<28} | {'Peak Inf. (Qty)':<16} | {'Peak Inf. (%)':<14} | {'Peak Tick':<10} | {'Final Susc. (%)':<16} | {'Duration (Steps)':<16} | {'Time (s)':<12}")
        print("-" * 130)
        for row in summary_data:
            name_str = row['strategy'].replace('_', ' ').title()
            print(f"{name_str:<28} | {row['peak_infected']:<16.2f} | {row['peak_infected_pct']:<13.2f}% | {row['peak_tick']:<10} | {row['final_susceptible_pct']:<15.2f}% | {row['duration']:<16} | {row['execution_time']:<12.4f}")
        print("=" * 130)

        # Generate comparison visualization
        default_plot = args.output_plot if args.output_plot is not None else "sir_comparison_curves.png"
        output_plot_path = add_param_suffix(default_plot, param_suffix)
        try:
            plot_comparison(all_avg_histories, output_plot_path)
        except Exception as e:
            print(f"Warning: Could not generate comparison plot: {e}", file=sys.stderr)

    # Save evaluation summary to CSV if requested
    if args.output_csv:
        output_csv_path = add_param_suffix(args.output_csv, param_suffix)
        try:
            with open(output_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'strategy', 'peak_infected', 'peak_infected_pct', 'peak_tick',
                    'final_susceptible_pct', 'final_infected_pct', 'final_recovered_pct', 'duration', 'execution_time'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for row in summary_data:
                    writer.writerow(row)
            print(f"\n[Data] Evaluation summary saved to CSV: {output_csv_path}")
        except Exception as e:
            print(f"Warning: Could not save evaluation summary to CSV: {e}", file=sys.stderr)

    print("\nSimulation Complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
