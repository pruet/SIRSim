import csv
from collections import defaultdict

def calculate_average_neighbor_degree(csv_file):
    adj = defaultdict(set)
    in_links = False
    
    with open(csv_file, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row: continue
            if row[0] == "LINKS":
                in_links = True
                next(reader) # skip headers
                continue
            if in_links:
                if not row[0].isdigit(): break # end of links
                u, v = int(row[0]), int(row[1])
                adj[u].add(v)
                adj[v].add(u)
                
    if not adj:
        return 0
        
    degrees = {node: len(neighbors) for node, neighbors in adj.items()}
    
    neighbor_degrees = []
    for node, neighbors in adj.items():
        if not neighbors:
            continue
        avg_neighbor_deg = sum(degrees[neighbor] for neighbor in neighbors) / len(neighbors)
        neighbor_degrees.append(avg_neighbor_deg)
        
    if not neighbor_degrees:
        return 0
        
    return sum(neighbor_degrees) / len(neighbor_degrees)

if __name__ == "__main__":
    avg_neigh_deg = calculate_average_neighbor_degree("oregon_export.csv")
    print(f"Average Neighbor Degree: {avg_neigh_deg:.4f}")
