#!/usr/bin/env python3
"""
Suppression Strategies for SIR Simulator
Author: Antigravity

This module defines the registry and standard static and dynamic suppression strategies
for evaluating epidemic control on network structures.

To add your own suppression algorithm:
1. Write a function with the signature: `def my_algorithm(simulator, event_type, **kwargs)`
2. Decorate it with `@register_strategy("my_algorithm_name")`
3. It will automatically be loaded and evaluated by `sir_simulator.py`!
"""

import random

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

@register_strategy("random_vaccination")
def random_vaccination(simulator, event_type, **kwargs):
    """
    Static random vaccination: vaccinates a random fraction of susceptible nodes at setup.
    """
    if event_type == "setup":
        susceptible_nodes = [who for who, state in simulator.states.items() if state == 0]
        num_to_vaccinate = int(len(susceptible_nodes) * simulator.vaccination_fraction)
        if num_to_vaccinate > 0:
            to_vaccinate = random.sample(susceptible_nodes, num_to_vaccinate)
            for who in to_vaccinate:
                simulator.states[who] = 2  # Set to Resistant

@register_strategy("high_degree_vaccination")
def high_degree_vaccination(simulator, event_type, **kwargs):
    """
    Static high-degree vaccination: vaccinates the top hubs (highest degrees) at setup.
    """
    if event_type == "setup":
        susceptible_nodes = [who for who, state in simulator.states.items() if state == 0]
        susceptible_nodes.sort(key=lambda who: len(simulator.adj[who]), reverse=True)
        num_to_vaccinate = int(len(susceptible_nodes) * simulator.vaccination_fraction)
        if num_to_vaccinate > 0:
            to_vaccinate = susceptible_nodes[:num_to_vaccinate]
            for who in to_vaccinate:
                simulator.states[who] = 2  # Set to Resistant

@register_strategy("acquaintance_vaccination")
def acquaintance_vaccination(simulator, event_type, **kwargs):
    """
    Static acquaintance vaccination: picks random nodes and vaccinates a random neighbor.
    This naturally biases towards high-degree nodes without global degree calculations.
    """
    if event_type == "setup":
        susceptible_nodes = [who for who, state in simulator.states.items() if state == 0]
        num_to_vaccinate = int(len(susceptible_nodes) * simulator.vaccination_fraction)
        vaccinated = set()
        all_nodes = list(simulator.states.keys())
        attempts = 0
        while len(vaccinated) < num_to_vaccinate and attempts < num_to_vaccinate * 10:
            attempts += 1
            u = random.choice(all_nodes)
            neighbors = list(simulator.original_adj[u].keys())
            if neighbors:
                v = random.choice(neighbors)
                if simulator.states[v] == 0 and v not in vaccinated:
                    simulator.states[v] = 2
                    vaccinated.add(v)

@register_strategy("infected_quarantine")
def infected_quarantine(simulator, event_type, **kwargs):
    """
    Dynamic quarantine: dynamically isolates infected nodes with some probability per step.
    A node is isolated by clearing all its incoming and outgoing links.
    """
    if event_type == "step":
        infected = [who for who, state in simulator.states.items() if state == 1]
        for u in infected:
            if random.random() < simulator.quarantine_chance:
                neighbors = list(simulator.adj[u].keys())
                for v in neighbors:
                    if u in simulator.adj[v]:
                        del simulator.adj[v][u]
                simulator.adj[u] = {}  # Disconnect completely

@register_strategy("social_distancing")
def social_distancing(simulator, event_type, **kwargs):
    """
    Static social distancing: reduces the spread probability (edge weight) of all links by 50% at setup.
    """
    if event_type == "setup":
        for u in simulator.adj:
            for v in simulator.adj[u]:
                w = simulator.adj[u][v]
                base_chance = w if w is not None else simulator.spread_chance
                simulator.adj[u][v] = base_chance * 0.5

@register_strategy("local_caution")
def local_caution(simulator, event_type, **kwargs):
    """
    Dynamic local caution: dynamically reduces link weights by 80% if any neighbor is infected.
    """
    if event_type == "step":
        for u in simulator.states:
            # Only apply caution to susceptible or immune nodes
            if simulator.states[u] != 1:
                has_infected_neighbor = any(simulator.states[v] == 1 for v in simulator.adj[u])
                if has_infected_neighbor:
                    for v in simulator.adj[u]:
                        w = simulator.adj[u][v]
                        base_chance = w if w is not None else simulator.spread_chance
                        simulator.adj[u][v] = base_chance * 0.2
