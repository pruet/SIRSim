import random
import math
import csv

def generate_sensor_network_3000():
    print("Generating spatially clustered sensor network (3,000 nodes)...")
    N = 3000
    target_avg_degree = 8
    target_links = int((N * target_avg_degree) / 2)
    
    # 1. Place nodes in a 2D space [-20, 20] x [-20, 20]
    nodes = []
    for i in range(N):
        # Scale by 0.95 as in NetLogo code
        xcor = (random.random() * 40 - 20) * 0.95
        ycor = (random.random() * 40 - 20) * 0.95
        nodes.append((i, xcor, ycor))
        
    # 2. Add edges using nearest spatial proximity (similar to NetLogo algorithm)
    adj = {i: set() for i in range(N)}
    links = []
    
    # Pre-calculate pairwise distances to make it extremely fast
    print("Computing pairwise distances...")
    coords = [(n[1], n[2]) for n in nodes]
    
    # We can do a fast search for nearest neighbors.
    # For each node, find other nodes sorted by distance
    print("Sorting neighbors by distance...")
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
        # Keep only the closest 100 neighbors for each node to save memory/speed
        neighbors_sorted.append([node_idx for dist, node_idx in dists[:100]])
        
    print("Connecting nodes spatially...")
    links_count = 0
    # To avoid getting stuck, keep a pointer for each node indicating which neighbor index to check next
    neighbor_ptrs = [0] * N
    
    # First, connect each node to its closest neighbor to ensure connectedness
    for i in range(N):
        if not adj[i]:
            j = neighbors_sorted[i][0]
            adj[i].add(j)
            adj[j].add(i)
            w = random.uniform(1.0, 10.0) # spread chance is 10.0
            links.append((i, j, w))
            links_count += 1
            
    # Then greedily add remaining links
    while links_count < target_links:
        u = random.randint(0, N - 1)
        # Find closest node that is not a neighbor
        found = False
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
        if not found:
            # Fallback to random if closest 100 are already connected
            attempts = 0
            while attempts < 100:
                v = random.randint(0, N - 1)
                if u != v and v not in adj[u]:
                    adj[u].add(v)
                    adj[v].add(u)
                    w = random.uniform(1.0, 10.0)
                    links.append((u, v, w))
                    links_count += 1
                    break
                attempts += 1
                
    print(f"Generated {N} nodes and {len(links)} links.")
    
    # 3. Write in NetLogo export-world CSV format
    csv_file = "sensor_network_3000.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["export-world data (NetLogo 6.3.0)"])
        writer.writerow(["Virus on a Network Extended.nlogo"])
        writer.writerow(["06/04/2026 12:45:00:000 +0000"])
        writer.writerow([])
        writer.writerow(["RANDOM STATE"])
        writer.writerow(["0 0 -1 110 0.0 false 0 0 0 0 0 0 0 0 0"])
        writer.writerow([])
        writer.writerow(["GLOBALS"])
        writer.writerow(["min-pxcor","max-pxcor","min-pycor","max-pycor","perspective","subject","nextIndex","directed-links","ticks","average-node-degree","gain-resistance-chance","initial-outbreak-size","number-of-nodes","recovery-chance","virus-check-frequency","virus-spread-chance"])
        writer.writerow(["-20","20","-20","20","0","nobody",str(N),'"UNDIRECTED"',"0",str(target_avg_degree),"5.0","1",str(N),"5.0","1","10.0"])
        writer.writerow([])
        
        # Write TURTLES
        writer.writerow(["TURTLES"])
        writer.writerow(["who","color","heading","xcor","ycor","shape","label","label-color","breed","hidden?","size","pen-size","pen-mode","infected?","resistant?","virus-check-timer","infected-chance"])
        for idx, x, y in nodes:
            # First 10 nodes are infected seeds
            infected = "true" if idx < 10 else "false"
            color = "55" if idx < 10 else "15"
            writer.writerow([str(idx), color, "0", f"{x:.6f}", f"{y:.6f}", '"circle"', "", "9.9", "{all-turtles}", "false", "1", "1", '"up"', infected, "false", "0", "0"])
            
        writer.writerow([])
        
        # Write LINKS
        writer.writerow(["LINKS"])
        writer.writerow(["end1","end2","color","label","label-color","hidden?","breed","thickness","shape","tie-mode","weight"])
        for u, v, w in links:
            writer.writerow([str(u), str(v), "9.9", "", "9.9", "false", "{all-links}", "0", '"default"', '"none"', f"{w:.6f}"])
            
    print(f"Successfully saved to {csv_file}")

if __name__ == "__main__":
    generate_sensor_network_3000()
