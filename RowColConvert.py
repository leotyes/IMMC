import pandas as pd
import numpy as np

csv_file = "grid_features.csv"
df = pd.read_csv(csv_file)

x_min, y_min = df['centroid_x'].min(), df['centroid_y'].min()
x_max, y_max = df['centroid_x'].max(), df['centroid_y'].max()
print(f"Centroid X range: {x_min} to {x_max}")
print(f"Centroid Y range: {y_min} to {y_max}")

df['col_index'] = ((df['centroid_x'] - x_min) / 1000).round().astype(int)
df['row_index'] = ((df['centroid_y'] - y_min) / 1000).round().astype(int)

df.to_csv("grid_features_indexed.csv", index=False)
print("Done")