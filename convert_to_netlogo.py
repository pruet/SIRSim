import csv
import random
import datetime
import os

__version__ = "1.1.0"

def convert_graph_to_netlogo(input_file, output_file, sample_size=None, initial_infected=3,
                             virus_spread_chance=10, recovery_chance=5, gain_resistance_chance=5,
                             virus_check_frequency=1):
    print(f"Reading graph from {input_file}...")
    
    all_nodes = set()
    all_edges = []
    
    with open(input_file, 'r') as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 2:
                u, v = parts[0], parts[1]
                all_nodes.add(u)
                all_nodes.add(v)
                all_edges.append((u, v))
                
    sorted_all_nodes = sorted(list(all_nodes))
    
    if sample_size and sample_size < len(sorted_all_nodes):
        print(f"Sampling edges to reach ~{sample_size} nodes...")
        sampled_nodes = set()
        
        # Shuffle edges to pick randomly
        shuffled_edges = all_edges[:]
        random.shuffle(shuffled_edges)
        
        for u, v in shuffled_edges:
            if len(sampled_nodes) >= sample_size:
                break
            sampled_nodes.add(u)
            sampled_nodes.add(v)
            
        nodes_list = sorted(list(sampled_nodes))
        sampled_nodes_lookup = set(nodes_list)
        edges = [(u, v) for u, v in all_edges if u in sampled_nodes_lookup and v in sampled_nodes_lookup]
        nodes = nodes_list
    else:
        nodes = sorted_all_nodes
        edges = all_edges

    node_to_who = {node: i for i, node in enumerate(nodes)}
    num_nodes = len(nodes)
    
    # Select nodes to infect
    infected_indices = set(random.sample(range(num_nodes), min(initial_infected, num_nodes)))
    
    print(f"Graph processed: {num_nodes} nodes, {len(edges)} edges. Infected: {len(infected_indices)}")
    
    now = datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S:%f")[:-3] + " +0000"
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        
        # Metadata
        writer.writerow(["export-world data (NetLogo 6.3.0)"])
        writer.writerow(["Virus on a Network Extended.nlogo"])
        writer.writerow([now])
        writer.writerow([])
        
        # RANDOM STATE (Dummy)
        writer.writerow(["RANDOM STATE"])
        writer.writerow(["0 0 -1 110 0.0 false 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0"])
        writer.writerow([])
        
        # GLOBALS
        writer.writerow(["GLOBALS"])
        global_headers = [
            "min-pxcor", "max-pxcor", "min-pycor", "max-pycor", "perspective", "subject", 
            "nextIndex", "directed-links", "ticks", "average-node-degree", 
            "gain-resistance-chance", "initial-outbreak-size", "number-of-nodes", 
            "recovery-chance", "virus-check-frequency", "virus-spread-chance"
        ]
        writer.writerow(global_headers)
        avg_degree = (2 * len(edges) / num_nodes) if num_nodes > 0 else 0
        global_values = [
            "-20", "20", "-20", "20", "0", "nobody", 
            str(num_nodes), "\"UNDIRECTED\"", "0", str(round(avg_degree, 2)),
            str(gain_resistance_chance), str(len(infected_indices)), str(num_nodes),
            str(recovery_chance), str(virus_check_frequency), str(virus_spread_chance)
        ]
        writer.writerow(global_values)
        writer.writerow([])
        
        # TURTLES
        writer.writerow(["TURTLES"])
        turtle_headers = [
            "who", "color", "heading", "xcor", "ycor", "shape", "label", "label-color", 
            "breed", "hidden?", "size", "pen-size", "pen-mode", "infected?", 
            "resistant?", "virus-check-timer", "infected-chance"
        ]
        writer.writerow(turtle_headers)
        for i in range(num_nodes):
            xcor = random.uniform(-20, 20)
            ycor = random.uniform(-20, 20)
            heading = random.randint(0, 359)
            is_infected = i in infected_indices
            color = "15" if is_infected else "105"
            check_timer = random.randint(0, max(0, virus_check_frequency - 1))
            writer.writerow([
                str(i), color, str(heading), str(xcor), str(ycor), "\"circle\"", "", "9.9", 
                "{all-turtles}", "false", "1", "1", "\"up\"", "true" if is_infected else "false", "false", str(check_timer), "0"
            ])
        writer.writerow([])
        
        # PATCHES
        writer.writerow(["PATCHES"])
        patch_headers = ["pxcor", "pycor", "pcolor", "plabel", "plabel-color"]
        writer.writerow(patch_headers)
        for y in range(20, -21, -1):
            for x in range(-20, 21):
                writer.writerow([str(x), str(y), "0", "", "9.9"])
        writer.writerow([])
        
        # LINKS
        writer.writerow(["LINKS"])
        link_headers = [
            "end1", "end2", "color", "label", "label-color", "hidden?", 
            "breed", "thickness", "shape", "tie-mode", "weight"
        ]
        writer.writerow(link_headers)
        for u, v in edges:
            weight = random.uniform(0, virus_spread_chance)
            writer.writerow([
                str(node_to_who[u]), str(node_to_who[v]), "5", "", "9.9", "false", 
                "{all-links}", "0", "\"default\"", "\"none\"", f"{weight:.6f}"
            ])
        writer.writerow([])

if __name__ == "__main__":
    input_txt = "oregon1_010331.txt"
    output_csv = "oregon_3000_5_50.csv"
    if os.path.exists(input_txt):
        # Set sample_size and initial_infected as needed
        convert_graph_to_netlogo(input_txt, output_csv, sample_size=3000, initial_infected=50)
        print(f"Successfully created {output_csv} with 3,000 nodes and 10 infected.")
    else:
        print(f"Error: {input_txt} not found.")


