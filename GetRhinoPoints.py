import rasterio
import numpy as np
import geopandas as gpd
from shapely.geometry import Point, shape
from skimage import measure
from pathlib import Path

tif_path = Path(__file__).parent / "GeoTIFFs" / "rhino.tif"

with rasterio.open(tif_path) as src:
    arr = src.read(1)
    transform = src.transform
    crs = src.crs

mask = arr == 0
labels = measure.label(mask, connectivity=2)

points = []
for region_label in range(1, labels.max() + 1):
    region_mask = labels == region_label
    if np.sum(region_mask) < 5:
        continue
    rows, cols = np.where(region_mask)
    row_centroid = rows.mean()
    col_centroid = cols.mean()
    x, y = transform * (col_centroid, row_centroid)
    points.append(Point(x, y))

rhino_points = gpd.GeoDataFrame({'geometry': points}, crs=crs)
rhino_points.to_file("rhino_points.geojson", driver="GeoJSON")
print(len(points))