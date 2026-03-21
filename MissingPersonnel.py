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

fire_sensor_positions = [tuple(pt.coords[0]) for pt in thermal_gdf.geometry]
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
fire_move_dist = 1

risk_poaching_map = {tuple(row[['centroid_x','centroid_y']]): row['RiskPoaching'] for _, row in df.iterrows()}
risk_fire_map = {tuple(row[['centroid_x','centroid_y']]): row['RiskFire'] for _, row in df.iterrows()}

poacher_results = []
fire_results = []

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
            clipped_x = max(min(new_x, max_x), min_x)
            clipped_y = max(min(new_y, max_y), min_y)
            temp.add((clipped_x, clipped_y))
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
    DETECTION_RADIUS = 1000
    for fire_coord in fire_pos:
        for sensor_coord in fire_sensor_positions:
            if math.dist(fire_coord, sensor_coord) <= DETECTION_RADIUS:
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
    event_type = random.choice(['poacher', 'fire'])
    poacher_detected = False
    fire_detected = False
    in_area = True
    active_ranger_ids = ranger_ids.copy()
    num_to_remove = int(0.1 * len(active_ranger_ids))
    rangers_removed = random.sample(active_ranger_ids, num_to_remove)
    for rid in rangers_removed:
        active_ranger_ids.remove(rid)

    ranger_states = [RangerState(ranger_routes[rid], ranger_speed, dt) for rid in active_ranger_ids]
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
        fire_origin = spawn_fire(risk_fire_map)[0]
        ranger_positions = [ranger_routes[rid][0] for rid in ranger_ids]
        min_sensor_dist = min([math.dist(fire_origin, s) for s in fire_sensor_positions])
        min_ranger_dist = min([math.dist(fire_origin, r) for r in ranger_positions])

        sensor_radius = 1000
        sensor_time = max(0, (min_sensor_dist - sensor_radius) / fire_move_dist)
        ranger_time = max(0, (min_ranger_dist - ranger_detect_fire_radius) / (ranger_speed + fire_move_dist))

        if sensor_time < ranger_time:
            print(f"{sensor_time:.1f} seconds (sensor)")
            fire_results.append(sensor_time)
            return sensor_time
        else:
            print(f"{ranger_time:.1f} seconds (ranger)")
            fire_results.append(ranger_time)
            return ranger_time

N = 500
results = [run_simulation() for _ in range(N)]
results.sort()
print(poacher_results)
print(sum(poacher_results) / len(poacher_results))
print(fire_results)
print(sum(fire_results) / len(fire_results))