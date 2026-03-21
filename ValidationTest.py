import pandas as pd
import numpy as np
import rasterio
from rasterio.transform import from_origin
from pathlib import Path

csv_file = Path("grid_features.csv")
df = pd.read_csv(csv_file)

grid_columns = ["rainfall_value", "biome_value", "rhino_value"]

x_sorted = np.sort(df['centroid_x'].unique())
y_sorted = np.sort(df['centroid_y'].unique())
res_x = np.min(np.diff(x_sorted))
res_y = np.min(np.diff(y_sorted))

for col in grid_columns:
    nx = len(x_sorted)
    ny = len(y_sorted)
    grid = np.full((ny, nx), np.nan, dtype=np.float32)

    x_index = {x:i for i, x in enumerate(x_sorted)}
    y_index = {y:i for i, y in enumerate(y_sorted)}

    for _, row in df.iterrows():
        ix = x_index[row['centroid_x']]
        iy = y_index[row['centroid_y']]
        grid[iy, ix] = row[col]

    grid = np.flipud(grid)

    transform = from_origin(
        x_sorted.min() - res_x/2,
        y_sorted.max() + res_y/2,
        res_x,
        res_y
    )

    output_path = Path(f"{col}.tif")
    with rasterio.open(
        output_path,
        'w',
        driver='GTiff',
        height=grid.shape[0],
        width=grid.shape[1],
        count=1,
        dtype=grid.dtype,
        crs="EPSG:3857",
        transform=transform
    ) as dst:
        dst.write(grid, 1)