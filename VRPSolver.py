import math
import pandas as pd
from sklearn.cluster import KMeans
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import json

df = pd.read_csv("grid_features_top.csv")
df.columns = df.columns.str.strip()

coords = df[["centroid_x", "centroid_y"]].values
weights = df["R"].values

num_vehicles = 32
k = min(len(df), num_vehicles * 6 * 2)

kmeans = KMeans(n_clusters=k, random_state=0, n_init=10)
df["cluster"] = kmeans.fit_predict(coords, sample_weight=weights)

cluster_centers = df.groupby("cluster")[["centroid_x", "centroid_y"]].mean()

cluster_features = []
for cluster_id, row in cluster_centers.iterrows():
    cluster_features.append({
        "type": "Feature",
        "properties": {"cluster_id": int(cluster_id)},
        "geometry": {
            "type": "Point",
            "coordinates": [row["centroid_x"], row["centroid_y"]]
        }
    })

with open("cluster_centers.geojson", "w") as f:
    json.dump({"type": "FeatureCollection", "features": cluster_features}, f, indent=2)

print(f"Cluster centers exported to cluster_centers.geojson ({len(cluster_features)} points)")

locations = list(zip(cluster_centers["centroid_x"], cluster_centers["centroid_y"]))
n_clusters = len(locations)
print(f"Clusters: {n_clusters}  |  Vehicles: {num_vehicles}")

depot_coords = [
    (1612587.8774063976, -2156831.5530044525),
    (1649571.6997669148, -2152274.1834093174),
    (1772467.0596357184, -2177570.1449823114),
    (1832224.9283719237, -2161286.5097996956),
    (1887476.6339129393, -2134351.9434284484),
    (1863665.6579383593, -2117300.2122466522),
]
num_depots = len(depot_coords)


def euclid(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


cluster_depot = [
    min(range(num_depots), key=lambda d: euclid(locations[c], depot_coords[d]))
    for c in range(n_clusters)
]
depot_cluster_counts = [cluster_depot.count(d) for d in range(num_depots)]
active_depots = [d for d in range(num_depots) if depot_cluster_counts[d] > 0]
active_total = sum(depot_cluster_counts[d] for d in active_depots)

vehicle_depot = []
for d in active_depots:
    n_veh = max(1, round(num_vehicles * depot_cluster_counts[d] / active_total))
    vehicle_depot.extend([d] * n_veh)

busiest = max(active_depots, key=lambda d: depot_cluster_counts[d])
while len(vehicle_depot) < num_vehicles:
    vehicle_depot.append(busiest)
while len(vehicle_depot) > num_vehicles:
    vehicle_depot.pop()

print("Depot allocation:")
for d in active_depots:
    print(f"  Depot {d}: {vehicle_depot.count(d)} vehicles, {depot_cluster_counts[d]} clusters")

vehicle_start_coords = [depot_coords[vehicle_depot[v]] for v in range(num_vehicles)]
vehicle_end_coords = [depot_coords[vehicle_depot[v]] for v in range(num_vehicles)]

all_locations = locations + vehicle_start_coords + vehicle_end_coords

starts = [n_clusters + v for v in range(num_vehicles)]
ends = [n_clusters + num_vehicles + v for v in range(num_vehicles)]


def raw_distance(i, j):
    x1, y1 = all_locations[i]
    x2, y2 = all_locations[j]
    return int(math.hypot(x1 - x2, y1 - y2))


manager = pywrapcp.RoutingIndexManager(len(all_locations), num_vehicles, starts, ends)
routing = pywrapcp.RoutingModel(manager)


def distance_callback(from_index, to_index):
    return raw_distance(manager.IndexToNode(from_index), manager.IndexToNode(to_index))


transit_index = routing.RegisterTransitCallback(distance_callback)
routing.SetArcCostEvaluatorOfAllVehicles(transit_index)

max_distance_per_vehicle = 240_000
routing.AddDimension(transit_index, 0, max_distance_per_vehicle, True, "Distance")


def counter_callback(from_index, to_index):
    to_node = manager.IndexToNode(to_index)
    return 1 if to_node < n_clusters else 0


counter_index = routing.RegisterTransitCallback(counter_callback)
routing.AddDimension(counter_index, 0, 12, True, "Stops")

stops_dimension = routing.GetDimensionOrDie("Stops")
for v in range(num_vehicles):
    stops_dimension.CumulVar(routing.End(v)).SetMin(6)

for node in range(n_clusters):
    routing.AddDisjunction([manager.NodeToIndex(node)], 240_000)

search_params = pywrapcp.DefaultRoutingSearchParameters()
search_params.first_solution_strategy = (
    routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
)
search_params.local_search_metaheuristic = (
    routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
)
search_params.time_limit.seconds = 60

print("Running solver...")
solution = routing.SolveWithParameters(search_params)
print(f"Solver status: {routing.status()}")

if solution:
    import json

    features = []

    for v in range(num_vehicles):
        index = routing.Start(v)
        route_coords = []

        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            x, y = all_locations[node]
            route_coords.append([x, y])  # GeoJSON uses [x, y]

            index = solution.Value(routing.NextVar(index))

        node = manager.IndexToNode(index)
        x, y = all_locations[node]
        route_coords.append([x, y])

        cluster_visits = [n for n in route_coords if n in locations]

        if len(route_coords) > 1:
            feature = {
                "type": "Feature",
                "properties": {
                    "vehicle_id": v,
                    "depot": vehicle_depot[v]
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": route_coords
                }
            }
            features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features
    }

    with open("routes.geojson", "w") as f:
        json.dump(geojson, f, indent=2)

    print("GeoJSON exported to routes.geojson")
    print("\n=== SOLUTION FOUND ===\n")
    total_distance = 0
    nodes_visited = set()
    active_vehicles = 0

    for v in range(num_vehicles):
        index = routing.Start(v)
        route = []
        route_dist = 0

        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            route.append(node)
            if node < n_clusters:
                nodes_visited.add(node)
            prev = index
            index = solution.Value(routing.NextVar(index))
            route_dist += raw_distance(manager.IndexToNode(prev), manager.IndexToNode(index))

        route.append(manager.IndexToNode(index))
        stops = [n for n in route if n < n_clusters]

        if stops:
            active_vehicles += 1
            print(
                f"Vehicle {v:2d} (depot {vehicle_depot[v]}) | dist: {route_dist / 1000:6.1f} km | stops: {len(stops)}")
            total_distance += route_dist

    skipped = set(range(n_clusters)) - nodes_visited
    print(f"\n=== SUMMARY ===")
    print(f"Active vehicles : {active_vehicles} / {num_vehicles}")
    print(f"Total distance  : {total_distance / 1000:.1f} km")
    print(f"Nodes visited   : {len(nodes_visited)} / {n_clusters} ({100 * len(nodes_visited) / n_clusters:.1f}%)")
    print(f"Nodes skipped   : {len(skipped)}")

else:
    print(f"\nNo solution found. Status: {routing.status()}")
