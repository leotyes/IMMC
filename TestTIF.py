import rasterio
from pathlib import Path

tif_path = Path(__file__).parent / "GeoTIFFs" / "rhino.tif"

with rasterio.open(tif_path) as src:
    print("CRS:", src.crs)
    print("Bounds:", src.bounds)
    print("Width x Height:", src.width, "x", src.height)
    print("Number of bands:", src.count)