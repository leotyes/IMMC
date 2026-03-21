import pandas as pd
import numpy as np

csv_file = "grid_features_indexed.csv"
df = pd.read_csv(csv_file)

V_map = {
    1: 0.43,
    2: 0.49,
    3: 1.00
}

df['V'] = df['biome_value'].map(V_map)
PrecipitationMax = df['rainfall_value'].max()
DistanceRoadMax = df['distance_to_road'].max()
df['RiskFire'] = df['V'] * (1 - df['rainfall_value'] / PrecipitationMax) * (1 - df['distance_to_road'] / DistanceRoadMax)
RhinoDensityMax = df["rhino_value"].max()
DistanceWaterHoleMax = df['distance_to_water_hole'].max()
DistancePoachingAreaMax = df['distance_to_poaching_area'].max()
df['RiskPoaching'] = (df["rhino_value"] / RhinoDensityMax) * (1 - df['distance_to_water_hole'] / DistanceWaterHoleMax) * (1 - df['distance_to_poaching_area'] / DistancePoachingAreaMax)
df["R"] = df['RiskFire'] * df['RiskPoaching']

df_sorted = df.sort_values(by='R', ascending=False)
df_top = df_sorted.head(7680).copy()

df_top.to_csv("grid_features_top.csv", index=False)
print("Done")