#!/usr/bin/env python3
"""
Test script to programmatically import, instantiate, and run the SIR simulation.
"""
from sir_simulator import run_sir_simulation, SIRNetworkSimulator

def main():
    print("=" * 60)
    print("1. Testing High-Level Functional API (`run_sir_simulation`)...")
    print("=" * 60)
    history, summary = run_sir_simulation(
        file_path="vone_300_6_3.csv",
        runs=3,
        steps=100,
        strategy_name="netshield_edge_suppression",
        suppression_ratio=0.15,
        suppression_percentage=80.0,
        parallel=True
    )
    print("\n[SUCCESS] Functional API executed programmatically! Summary returned:")
    for k, v in summary.items():
        print(f"  - {k}: {v}")

    print("\n" + "=" * 60)
    print("2. Testing Direct Class Invocation (`SIRNetworkSimulator`)...")
    print("=" * 60)
    
    # Initialize the simulator class directly from the CSV using our new classmethod
    sim = SIRNetworkSimulator.from_file(
        file_path="vone_300_6_3.csv",
        strategy_name="reliable_cluster_edge_suppression",
        suppression_ratio=0.20,
        suppression_percentage=90.0
    )
    
    print(f"Simulator instantiated successfully:")
    print(f"  - Spread Chance: {sim.spread_chance}%")
    print(f"  - Recovery Chance: {sim.recovery_chance * 100.0}%")
    print(f"  - Resistance Chance: {sim.resistance_chance * 100.0}%")
    print(f"  - Node states count: {len(sim.states)}")
    
    # Simulate first 10 steps programmatically via step-by-step invocation
    print("\nRunning first 10 steps interactively:")
    print(f"{'Tick':<6} | {'Susceptible':<12} | {'Infected':<10} | {'Recovered':<10} | {'New Infections':<14}")
    print("-" * 60)
    
    # Print tick 0 (initial state)
    init_hist = sim.history[0]
    print(f"{0:<6} | {init_hist['S']:<12} | {init_hist['I']:<10} | {init_hist['R']:<10} | {0:<14}")
    
    for tick in range(1, 11):
        new_infections = sim.step(tick)
        latest = sim.history[-1]
        print(f"{tick:<6} | {latest['S']:<12} | {latest['I']:<10} | {latest['R']:<10} | {new_infections:<14}")
        
    print("-" * 60)
    print("[SUCCESS] Direct class invocation and step-by-step execution succeeded!")
    print("=" * 60)

if __name__ == "__main__":
    main()
