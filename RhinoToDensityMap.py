import geopandas as gpd
import numpy as np
from sklearn.neighbors import KernelDensity
import rasterio
from rasterio.transform import from_bounds

rhinos = gpd.read_file("rhino_points_new.geojson")

rhinos = rhinos[~rhinos.geometry.is_empty]
rhinos = rhinos[rhinos.geometry.notnull()]

x = rhinos.geometry.x.values
y = rhinos.geometry.y.values

mask = (~np.isnan(x)) & (~np.isnan(y))
x = x[mask]
y = y[mask]

coords = np.vstack([x, y]).T

buffer = 10000
bandwidth = 5000
kde = KernelDensity(bandwidth=bandwidth, kernel='gaussian')
kde.fit(coords)

minx, miny, maxx, maxy = rhinos.total_bounds
minx -= buffer
miny -= buffer
maxx += buffer
maxy += buffer
res = 1000

x_grid = np.arange(minx, maxx, res)
y_grid = np.arange(miny, maxy, res)
xx, yy = np.meshgrid(x_grid, y_grid)

grid_coords = np.vstack([xx.ravel(), yy.ravel()]).T
z = np.exp(kde.score_samples(grid_coords))
z = z.reshape(xx.shape)

z = np.log1p(z)
z = z / z.max()
z = (z * 255).astype("uint8")

z = np.flipud(z)

transform = from_bounds(minx, miny, maxx, maxy, z.shape[1], z.shape[0])

with rasterio.open(
        "GeoTIFFs/rhino.tif",
    "w",
    driver="GTiff",
    height=z.shape[0],
    width=z.shape[1],
    count=1,
    dtype="uint8",
    crs=rhinos.crs,
    transform=transform,
) as dst:
    dst.write(z, 1)