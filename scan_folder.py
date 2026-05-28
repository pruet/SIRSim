import os
import csv
import sys
from collections import defaultdict

def parse_node_id(value):
    val = value.strip()
    if val.startswith("{turtle ") and val.endswith("}"):
        return int(val[len("{turtle "):-1])
    return int(val)

def parse_netlogo_metadata(csv_file):
    globals_dict = {}
    nodes = {}
    edges = []
    current_section = None
    headers = []

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            first_cell = row[0].strip()
            if first_cell in ("GLOBALS", "TURTLES", "PATCHES", "LINKS", "RANDOM STATE"):
                current_section = first_cell
                headers = []
                continue
            if current_section is None or current_section == "RANDOM STATE" or first_cell.startswith("export-world data"):
                continue
            if not headers:
                headers = [h.strip() for h in row]
                continue
            if current_section == "GLOBALS":
                for h, val in zip(headers, row):
                    globals_dict[h] = val.strip()
            elif current_section == "TURTLES":
                data = dict(zip(headers, row))
                if 'who' in data:
                    who = int(data['who'])
                    is_infected = data.get('infected?', 'false').strip().lower() == 'true'
                    is_resistant = data.get('resistant?', 'false').strip().lower() == 'true'
                    nodes[who] = {'infected': is_infected, 'resistant': is_resistant}
            elif current_section == "LINKS":
                data = dict(zip(headers, row))
                if 'end1' in data and 'end2' in data:
                    try:
                        u = parse_node_id(data['end1'])
                        v = parse_node_id(data['end2'])
                        edges.append((u, v))
                    except ValueError:
                        continue

    # Clean up nodes
    adj = defaultdict(set)
    for u, v in edges:
        adj[u].add(v)
        adj[v].add(u)
    
    all_node_ids = set(nodes.keys()).union(adj.keys())
    for who in all_node_ids:
        if who not in nodes:
            nodes[who] = {'infected': False, 'resistant': False}

    num_nodes = len(nodes)
    num_edges = sum(len(neighbors) for neighbors in adj.values()) // 2
    infected = sum(1 for n in nodes.values() if n['infected'])
    resistant = sum(1 for n in nodes.values() if n['resistant'])

    return {
        'nodes': num_nodes,
        'edges': num_edges,
        'infected': infected,
        'resistant': resistant,
        'spread_chance': globals_dict.get('virus-spread-chance', 'N/A'),
        'recovery_chance': globals_dict.get('recovery-chance', 'N/A'),
        'resistance_chance': globals_dict.get('gain-resistance-chance', 'N/A')
    }

def main():
    folder = "."
    files = sorted([f for f in os.listdir(folder) if f.endswith('.csv')])
    
    print("| File Name | Nodes | Edges | Initial Infected | Spread Chance | Recovery Chance | Resistance Chance |")
    print("|---|---|---|---|---|---|---|")
    
    for f in files:
        path = os.path.join(folder, f)
        try:
            meta = parse_netlogo_metadata(path)
            print(f"| `{f}` | {meta['nodes']} | {meta['edges']} | {meta['infected']} | {meta['spread_chance']}% | {meta['recovery_chance']}% | {meta['resistance_chance']}% |")
        except Exception as e:
            # Skip non-NetLogo format files silently or print error
            pass

if __name__ == '__main__':
    main()
