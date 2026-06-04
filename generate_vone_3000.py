import random
import math
import csv
import numpy as np

def generate_modular_spatial_network():
    print("Generating 3,000-node modular spatial network (VONE-3000)...")
    N = 3000
    num_clusters = 10
    nodes_per_cluster = N // num_clusters # 300 nodes per cluster
    avg_degree = 6
    target_links = int((N * avg_degree) / 2) # 9000 edges
    
    # 1. Generate 10 cluster centers in [-20, 20] x [-20, 20]
    # Keep them separated to ensure modularity
    centers = []
    attempts = 0
    while len(centers) < num_clusters and attempts < 1000:
        cx = random.uniform(-18, 18)
        cy = random.uniform(-18, 18)
        # Ensure minimum distance between centers to keep communities distinct
        if all(math.hypot(cx - ox, cy - oy) > 6.0 for ox, oy in centers):
            centers.append((cx, cy))
        attempts += 1
        
    # Fallback if we couldn't place them under strict distance constraints
    while len(centers) < num_clusters:
        centers.append((random.uniform(-18, 18), random.uniform(-18, 18)))
        
    # 2. Place nodes around centers using Gaussian distribution
    nodes = []
    node_to_cluster = {}
    node_id = 0
    std_dev = 1.2  # Controls how tight the spatial clusters are
    
    for c_idx, (cx, cy) in enumerate(centers):
        for _ in range(nodes_per_cluster):
            # Generate coordinates around the center
            xcor = np.random.normal(cx, std_dev)
            ycor = np.random.normal(cy, std_dev)
            # Clip to NetLogo screen boundaries
            xcor = max(-20.0, min(20.0, xcor))
            ycor = max(-20.0, min(20.0, ycor))
            
            nodes.append((node_id, xcor, ycor, c_idx))
            node_to_cluster[node_id] = c_idx
            node_id += 1
            
    # 3. Connect nodes using nearest neighbor proximity
    # We will find the closest nodes in terms of Euclidean distance
    adj = {i: set() for i in range(N)}
    links = []
    
    coords = [(n[1], n[2]) for n in nodes]
    
    # Precompute pairwise distances
    print("Computing distances and sorting spatial neighbors...")
    neighbors_sorted = []
    for i in range(N):
        x1, y1 = coords[i]
        dists = []
        for j in range(N):
            if i != j:
                x2, y2 = coords[j]
                d = (x1 - x2) ** 2 + (y1 - y2) ** 2
                dists.append((d, j))
        dists.sort()
        # Store closest 50 neighbors
        neighbors_sorted.append([node_idx for dist, node_idx in dists[:50]])
        
    print("Building intra-cluster and inter-cluster connections...")
    links_count = 0
    
    # Connect each node to its closest neighbor first to ensure no isolated nodes
    for i in range(N):
        if not adj[i]:
            j = neighbors_sorted[i][0]
            adj[i].add(j)
            adj[j].add(i)
            w = random.uniform(1.0, 10.0)
            links.append((i, j, w))
            links_count += 1
            
    # Add links greedily favoring closest spatial neighbors
    # Also add a few long-range bridging connections (inter-cluster) randomly
    # to mimic NetLogo's layout and maintain global connectedness
    neighbor_ptrs = [0] * N
    
    while links_count < target_links:
        u = random.randint(0, N - 1)
        found = False
        
        # 95% chance to connect to nearest spatial neighbor
        if random.random() < 0.95:
            while neighbor_ptrs[u] < len(neighbors_sorted[u]):
                v = neighbors_sorted[u][neighbor_ptrs[u]]
                neighbor_ptrs[u] += 1
                if v not in adj[u]:
                    adj[u].add(v)
                    adj[v].add(u)
                    w = random.uniform(1.0, 10.0)
                    links.append((u, v, w))
                    links_count += 1
                    found = True
                    break
        else:
            # 5% chance to create a random long-range bridge to another cluster
            attempts = 0
            u_cluster = node_to_cluster[u]
            while attempts < 100:
                v = random.randint(0, N - 1)
                v_cluster = node_to_cluster[v]
                if u != v and u_cluster != v_cluster and v not in adj[u]:
                    adj[u].add(v)
                    adj[v].add(u)
                    w = random.uniform(1.0, 5.0) # slightly weaker transmission for long-range links
                    links.append((u, v, w))
                    links_count += 1
                    found = True
                    break
                attempts += 1
                
        # If we couldn't connect u, try next loop
        if not found and neighbor_ptrs[u] >= len(neighbors_sorted[u]):
            # Fallback to connect to any random node if neighbors exhausted
            attempts = 0
            while attempts < 50:
                v = random.randint(0, N - 1)
                if u != v and v not in adj[u]:
                    adj[u].add(v)
                    adj[v].add(u)
                    w = random.uniform(1.0, 10.0)
                    links.append((u, v, w))
                    links_count += 1
                    break
                attempts += 1

    print(f"Graph generation complete: {N} nodes, {len(links)} links.")
    
    # 4. Save to NetLogo export-world CSV format
    csv_file = "vone_3000.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["export-world data (NetLogo 6.3.0)"])
        writer.writerow(["Virus on a Network Extended.nlogo"])
        writer.writerow(["06/04/2026 14:00:00:000 +0000"])
        writer.writerow([])
        writer.writerow(["RANDOM STATE"])
        writer.writerow(["0 0 -1 110 0.0 false 0 0 0 0 0 0 0 0 0"])
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
        avg_degree = (2 * len(links) / N)
        global_values = [
            "-20", "20", "-20", "20", "0", "nobody", 
            str(N), "\"UNDIRECTED\"", "0", str(round(avg_degree, 2)),
            "5", "10", str(N), "5", "1", "10"
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
        
        # Infect 10 random nodes
        infected_indices = set(random.sample(range(N), 10))
        
        for i in range(N):
            _, x, y, c_idx = nodes[i]
            is_infected = i in infected_indices
            color = "15" if is_infected else "105"
            check_timer = random.randint(0, 0) # check timer starts at 0
            writer.writerow([
                str(i), color, "0", f"{x:.6f}", f"{y:.6f}", "\"circle\"", "", "9.9", 
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
        for u, v, w in links:
            writer.writerow([
                str(u), str(v), "5", "", "9.9", "false", 
                "{all-links}", "0", "\"default\"", "\"none\"", f"{w:.6f}"
            ])
        writer.writerow([])
        
    print(f"VONE-3000 dataset saved to {csv_file}!")

if __name__ == "__main__":
    generate_modular_spatial_network()
