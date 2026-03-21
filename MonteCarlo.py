import numpy as np
import pandas as pd
import random
import math
import json
import geopandas as gpd

def load_ranger_routes_from_geojson(geojson_path):
    with open(geojson_path, 'r') as f:
        geojson = json.load(f)
    routes = {}
    for feature in geojson['features']:
        vehicle_id = feature['properties']['vehicle_id']
        coords = feature['geometry']['coordinates']
        routes[vehicle_id] = [tuple(coord) for coord in coords]
    return routes

def weighted_choice(keys, weights):
    total = sum(weights)
    r = random.uniform(0, total)
    upto = 0
    for k, w in zip(keys, weights):
        if upto + w >= r:
            return k
        upto += w
    return keys[-1]

df = pd.read_csv("grid_features.csv")
geojson_file = "routes.geojson"
ranger_routes = load_ranger_routes_from_geojson(geojson_file)
ranger_ids = sorted(ranger_routes.keys())

thermal_gdf = gpd.read_file("thermal_cameras.geojson")
acoustic_gdf = gpd.read_file("acoustic_gunshot_sensors.geojson")
normal_gdf = gpd.read_file("normal_cameras.geojson")

centroids_set = set((row['centroid_x'], row['centroid_y']) for _, row in df.iterrows())
fire_sensor_positions = set((pt.coords[0][0], pt.coords[0][1]) for pt in thermal_gdf.geometry)
acoustic_sensor_positions = [tuple(pt.coords[0]) for pt in acoustic_gdf.geometry]
normal_camera_positions = [tuple(pt.coords[0]) for pt in normal_gdf.geometry]

min_x = df['centroid_x'].min()
max_x = df['centroid_x'].max()
min_y = df['centroid_y'].min()
max_y = df['centroid_y'].max()

ranger_detect_poacher_radius = 1000
ranger_detect_fire_radius = 2000
ranger_catch_radius = 5000
ranger_speed = 40 / 3.6
dt = 1.0
poacher_speed = 5 / 3.6
fire_move_dist = 0.5

risk_poaching_map = {tuple(row[['centroid_x','centroid_y']]): row['RiskPoaching'] for _, row in df.iterrows()}
risk_fire_map = {tuple(row[['centroid_x','centroid_y']]): row['RiskFire'] for _, row in df.iterrows()}

poacher_results = []
fire_results = []

def snap_to_grid_centroid(x, y, centroids):
    return min(centroids, key=lambda c: (x-c[0])**2 + (y-c[1])**2)

def spawn_poacher(risk_map):
    coord_list = list(risk_map.keys())
    weights = [max(risk_map[coord], 0) for coord in coord_list]
    if sum(weights) > 0:
        return weighted_choice(coord_list, weights)
    else:
        return random.choice(coord_list)

def spawn_fire(risk_map):
    coord_list = list(risk_map.keys())
    weights = [max(risk_map[coord], 0) for coord in coord_list]
    if sum(weights) > 0:
        coord = weighted_choice(coord_list, weights)
    else:
        coord = random.choice(coord_list)
    return [coord]

def move_poacher_north_or_northeast(pos):
    angle = random.choice([np.pi/2, np.pi/4])
    new_x = pos[0] + poacher_speed * np.cos(angle)
    new_y = pos[1] + poacher_speed * np.sin(angle)
    return (new_x, new_y)

def move_fire(fire_pos):
    temp = set()
    directions = [
        0, np.pi/4, np.pi/2, 3*np.pi/4,
        np.pi, 5*np.pi/4, 3*np.pi/2, 7*np.pi/4
    ]
    for coord in fire_pos:
        for angle in directions:
            new_x = coord[0] + fire_move_dist * np.cos(angle)
            new_y = coord[1] + fire_move_dist * np.sin(angle)
            # Clip to bounds
            clipped_x = max(min(new_x, max_x), min_x)
            clipped_y = max(min(new_y, max_y), min_y)
            snapped = snap_to_grid_centroid(clipped_x, clipped_y, centroids_set)
            temp.add(snapped)
    fire_pos = list(temp)
    return fire_pos

def sensor_detect_poacher(poacher_pos, ranger_positions):
    for sensor_pos in acoustic_sensor_positions:
        if math.dist(poacher_pos, sensor_pos) <= 1500:
            return True
    for sensor_pos in normal_camera_positions:
        if math.dist(poacher_pos, sensor_pos) <= 1000:
            if random.random() < 0.3:
                return True
    for ranger_pos in ranger_positions:
        if math.dist(poacher_pos, ranger_pos) <= ranger_catch_radius:
            return True
    return False

def ranger_detect_poacher(poacher_pos, ranger_positions):
    for ranger_pos in ranger_positions:
        if math.dist(poacher_pos, ranger_pos) <= ranger_detect_poacher_radius:
            if random.random() < 0.5:
                return True
    return False

def detect_fire(fire_pos, ranger_positions):
    for fire_coord in fire_pos:
        if fire_coord in fire_sensor_positions:
            return True
    for fire_coord in fire_pos:
        for ranger_pos in ranger_positions:
            if math.dist(fire_coord, ranger_pos) <= ranger_detect_fire_radius:
                return True
    return False

class RangerState:
    def __init__(self, route, speed_mps, dt_seconds):
        self.route = route
        self.speed = speed_mps
        self.dt = dt_seconds
        self.curr_seg = 0
        self.seg_progress = 0.0
        self.pos = route[0]
    def step(self):
        remaining = self.speed * self.dt
        while remaining > 0:
            a = self.route[self.curr_seg]
            b = self.route[(self.curr_seg + 1) % len(self.route)]
            seg_len = math.dist(a, b)
            advance = min(seg_len - self.seg_progress, remaining)
            frac = (self.seg_progress + advance) / seg_len if seg_len > 0 else 1.0
            new_x = a[0] + frac * (b[0] - a[0])
            new_y = a[1] + frac * (b[1] - a[1])
            self.pos = (new_x, new_y)
            self.seg_progress += advance
            remaining -= advance
            if self.seg_progress >= seg_len:
                self.curr_seg = (self.curr_seg + 1) % len(self.route)
                self.seg_progress = 0.0

def in_bounds(pos):
    x, y = pos
    return (min_x <= x <= max_x) and (min_y <= y <= max_y)

def run_simulation():
    MAX_FIRE_STEPS = 2000
    event_type = random.choice(['poacher', 'fire'])
    poacher_detected = False
    fire_detected = False
    in_area = True
    ranger_states = [RangerState(ranger_routes[rid], ranger_speed, dt) for rid in ranger_ids]
    # TODO remove later this is for testing
    event_type = 'fire'
    if event_type == 'poacher':
        poacher = spawn_poacher(risk_poaching_map)
        while True:
            poacher = move_poacher_north_or_northeast(poacher)
            if not in_bounds(poacher):
                in_area = False
                break
            for ranger in ranger_states:
                ranger.step()
            ranger_positions = [ranger.pos for ranger in ranger_states]
            if sensor_detect_poacher(poacher, ranger_positions):
                poacher_detected = True
            if ranger_detect_poacher(poacher, ranger_positions):
                poacher_detected = True
            if poacher_detected:
                break
        poacher_results.append(int(in_area))
        return int(in_area)
    else:
        fire = spawn_fire(risk_fire_map)
        t = 0
        detection_time = None
        detection_source = None
        while t < MAX_FIRE_STEPS:
            fire = move_fire(fire)
            for ranger in ranger_states:
                ranger.step()
            ranger_positions = [ranger.pos for ranger in ranger_states]
            fire_detected = False
            for fire_coord in fire:
                if fire_coord in fire_sensor_positions:
                    detection_time = t + 1
                    detection_source = 'sensor'
                    fire_detected = True
                    break
            if fire_detected:
                break
            for fire_coord in fire:
                for ranger_pos in ranger_positions:
                    if math.dist(fire_coord, ranger_pos) <= ranger_detect_fire_radius:
                        detection_time = t + 1
                        detection_source = 'ranger'
                        fire_detected = True
                        break
                if fire_detected:
                    break
            if fire_detected:
                break
            t += 1
        if detection_time is not None:
            if detection_source == 'sensor':
                print(f"{detection_time} seconds (sensor)")
            else:
                print(f"{detection_time} seconds (ranger)")
            fire_results.append(detection_time)
            return detection_time
        else:
            print(f"Timeout: No fire detected after {MAX_FIRE_STEPS} seconds.")
            fire_results.append(None)
            return None

N = 50
results = [run_simulation() for _ in range(N)]
results.sort()