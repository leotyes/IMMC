import geopandas as gpd
from shapely.geometry import box, Point
from shapely.ops import unary_union
import numpy as np
from pathlib import Path
import rasterio
from shapely.geometry.polygon import Polygon

grid_size = 1000
output_csv = "grid_features.csv"
output_gpkg = "grid_with_features.gpkg"

rhino_path = Path(__file__).parent / "GeoTIFFs" / "rhino.tif"

raster0 = rasterio.open(rhino_path)
minx, miny, maxx, maxy = raster0.bounds
crs = raster0.crs

polygons = []
x = minx
while x < maxx:
    y = miny
    while y < maxy:
        polygons.append(box(x, y, x + grid_size, y + grid_size))
        y += grid_size
    x += grid_size

grid = gpd.GeoDataFrame({'geometry': polygons}, crs=crs)
grid['centroid_x'] = grid.geometry.centroid.x
grid['centroid_y'] = grid.geometry.centroid.y

x_min = grid['centroid_x'].min()
x_max = grid['centroid_x'].max()
grid['rainfall_value'] = ((grid['centroid_x'] - x_min) / (x_max - x_min) * 255).astype(int)

# 1 is shrub savanna, 2 is tree savanna, 3 is grass savanna
biome_bounds = [
    (Polygon([
        (1635397.1320482916, -2154458.183458643),
        (1649702.4120330198, -2181210.914858654),
        (1658619.9891663566, -2176566.343435041),
        (1701569.2700347926, -2151152.061405029),
        (1726301.9612083891, -2151766.5382043733),
        (1730040.0284043986, -2139016.144617985),
        (1666236.8540725114, -2132103.2806253643),
        (1666288.0604724572, -2109777.2902491987),
        (1651862.1377450002, -2133023.486338669),
        (1621672.4234915148, -2113562.7320737303),
        (1625364.8577732875, -2127984.126344049),
        (1631681.4749094013, -2133557.6120523848),
        (1623321.2463468977, -2141546.274900999),
    ]), 1),
    (Polygon([
        (1612879.785329473, -2192885.2773604775),
        (1608783.2733338461, -2204662.749347904),
        (1618410.0765235692, -2193397.3413599306),
        (1623428.3037182118, -2204560.3365480136),
        (1624657.2573169, -2193499.7541598217),
        (1618512.4893234598, -2184077.77656988),
        (1647597.72449241, -2183463.299770536),
        (1621482.4605202891, -2142703.0054140496),
        (1598849.2317444514, -2157348.035798415),
        (1605198.8253376728, -2183770.5381702078),
    ]), 2),
    (Polygon([
        (1690574.6405608142, -2163143.532020798),
        (1684165.1319962281, -2171875.3262971905),
        (1669488.286297611, -2180049.7720027496),
        (1705344.3776879034, -2176798.572006221),
        (1709710.2748260996, -2183393.863427751),
        (1772597.7719018203, -2170017.4977277457),
        (1751325.6347816726, -2152182.343461071),
        (1756063.097633758, -2149116.9263214865),
        (1762751.2804837606, -2135926.343478426),
        (1752626.1147802842, -2135276.10347912),
        (1734419.3947997212, -2146051.509181902),
        (1725687.6005233289, -2153947.280602044),
        (1702186.0691198467, -2158498.960597185),
    ]), 3)
]

pan_bounds = [
    Polygon([
        (1859487.60129477432929, -2096483.714034817647189),
        (1773563.262186504201964, -2121779.675607812590897),
        (1763526.807797218672931, -2139394.677189007401466),
        (1775611.518184317508712, -2170528.168355770409107),
        (1818420.068538616644219, -2153732.46917370101437),
        (1855493.502099038334563, -2147382.875580479390919),
        (1861843.095692259725183, -2136629.531591959297657),
        (1881403.94047137722373, -2136015.054792615585029),
    ]),
    Polygon([
        (1751339.68461022968404, -2137141.595591412857175),
        (1754412.068606949644163, -2149226.305978511925787),
        (1744068.375817992258817, -2147485.288380370475352),
        (1737821.195024661486968, -2147280.462780589237809),
        (1734441.572628269437701, -2141647.758786602411419),
        (1742327.358219850808382, -2144720.142783322371542),
    ]),
    Polygon([
        (1749905.90541176032275, -2119270.562010491732508),
        (1754053.623807332245633, -2119014.530010764952749),
        (1757945.310203177621588, -2124135.170005298219621),
        (1754616.894206731114537, -2125568.949203767813742),
    ])
]

etosha_bounds = Polygon([
    (1608806.960648106178269, -2204317.657691128086299),
    (1623994.70920332078822, -2204549.88626230834052),
    (1624575.280631272355095, -2193565.474845463875681),
    (1618467.669209221377969, -2193565.47484546341002),
    (1618398.000637867487967, -2184044.103427057154477),
    (1660710.04630698217079, -2182999.074856744147837),
    (1672971.71486532012932, -2179980.103431395255029),
    (1691271.326274355407804, -2181698.594858132302761),
    (1704508.354831652948633, -2177518.480576880276203),
    (1704926.366259778151289, -2183695.760570285376161),
    (1745380.583359447773546, -2186946.96056681452319),
    (1847561.154678934719414, -2206732.834831406362355),
    (1858522.343238661298528, -2212213.429111269768327),
    (1891870.366060202941298, -2195307.189129318576306),
    (1906361.428901875158772, -2176264.446292504668236),
    (1896143.371769926743582, -2126010.183489012066275),
    (1896143.371769926743582, -2110961.77207650616765),
    (1908590.823185209650546, -2110404.423505672253668),
    (1905153.840331735787913, -2099257.452089001424611),
    (1897722.526053955079988, -2096192.034949416527525),
    (1743894.320503891445696, -2095541.794950110837817),
    (1740178.663365001091734, -2117092.6063556750305),
    (1703393.657689985819161, -2108918.160650115925819),
    (1622206.549205230083317, -2113934.297787617892027),
    (1624993.292059398023412, -2128239.577772346325219),
    (1631681.474909400800243, -2133998.846337626688182),
    (1598240.560659386916086, -2157593.269169580657035),
    (1604185.612081611528993, -2182488.172000146470964),
    (1612731.623501059599221, -2192613.337703623343259),
    (1609759.097789947409183, -2198372.606268903706223),
])

grid['biome_value'] = 2
for idx, row in grid.iterrows():
    point = row.geometry.centroid
    if not etosha_bounds.contains(point):
        grid.at[idx, 'biome_value'] = 0
        continue
    if any(water.contains(point) for water in pan_bounds):
        grid.at[idx, 'biome_value'] = 0
        continue
    for poly, code in biome_bounds:
        if poly.contains(point):
            grid.at[idx, 'biome_value'] = code
            break

valid_grid = grid[grid['biome_value'] != 0].copy()

def sample_raster(raster, x, y):
    row, col = raster.index(x, y)
    return float(raster.read(1)[row, col])

valid_grid['rhino_value'] = valid_grid.geometry.centroid.apply(
    lambda pt: sample_raster(raster0, pt.x, pt.y)
)

roads_gdf = gpd.read_file(Path(__file__).parent / "roads.geojson")
road_union = unary_union(roads_gdf.geometry)
def point_to_road_distance(pt):
    return pt.distance(road_union)
valid_grid['distance_to_road'] = valid_grid.geometry.centroid.apply(point_to_road_distance)

water_gdf = gpd.read_file(Path(__file__).parent / "water_holes.geojson")
water_union = unary_union(water_gdf.geometry)
def point_to_water_distance(pt):
    return pt.distance(water_union)
valid_grid['distance_to_water_hole'] = valid_grid.geometry.centroid.apply(point_to_water_distance)

poaching_areas_gdf = gpd.read_file(Path(__file__).parent / "poaching_area.geojson")
poaching_union = unary_union(poaching_areas_gdf.geometry)
def point_to_poaching_distance(pt):
    return pt.distance(poaching_union)
valid_grid['distance_to_poaching_area'] = valid_grid.geometry.centroid.apply(point_to_poaching_distance)

# python
# Insert this into `GridCreation.py` after you compute rhino_value and the distance columns, before writing files.

V_map = {
    1: 0.43,
    2: 0.49,
    3: 1.00
}
valid_grid['V'] = valid_grid['biome_value'].map(V_map).fillna(0)

precip_max = valid_grid['rainfall_value'].max()
road_dist_max = valid_grid['distance_to_road'].max()
rhino_max = valid_grid['rhino_value'].max()
water_dist_max = valid_grid['distance_to_water_hole'].max()
poach_dist_max = valid_grid['distance_to_poaching_area'].max()

precip_denom = precip_max
road_denom = road_dist_max
rhino_denom = rhino_max
water_denom = water_dist_max
poach_denom = poach_dist_max

rain_norm = valid_grid['rainfall_value'] / precip_denom
road_norm = valid_grid['distance_to_road'] / road_denom
rhino_norm = valid_grid['rhino_value'] / rhino_denom
water_norm = valid_grid['distance_to_water_hole'] / water_denom
poach_norm = valid_grid['distance_to_poaching_area'] / poach_denom

valid_grid['RiskFire'] = valid_grid['V'] * (1.0 - rain_norm) * (1.0 - road_norm)
valid_grid['RiskPoaching'] = rhino_norm * (1.0 - water_norm) * (1.0 - poach_norm)

valid_grid['R'] = valid_grid['RiskFire'] * valid_grid['RiskPoaching']

valid_grid.to_file(output_gpkg, layer="grid_features", driver="GPKG")
valid_grid.drop(columns='geometry').to_csv(output_csv, index=False)

import geopandas as gpd
from shapely.geometry import Point

valid_grid_sorted = valid_grid.sort_values("RiskFire", ascending=False).head(42)
camera_points = [
    Point(xy) for xy in zip(valid_grid_sorted['centroid_x'], valid_grid_sorted['centroid_y'])
]
cams_gdf = gpd.GeoDataFrame({'geometry': camera_points}, crs=valid_grid.crs)
cams_gdf['camera_id'] = range(1, 43)

cams_gdf.to_file("thermal_cameras.geojson", driver="GeoJSON")

import geopandas as gpd
from shapely.geometry import Point

valid_grid_sorted_gun = valid_grid.sort_values("RiskPoaching", ascending=False).head(13)
gun_points = [
    Point(xy) for xy in zip(valid_grid_sorted_gun['centroid_x'], valid_grid_sorted_gun['centroid_y'])
]
gun_gdf = gpd.GeoDataFrame({'geometry': gun_points}, crs=valid_grid.crs)
gun_gdf['sensor_id'] = range(1, 14)

gun_gdf.to_file("acoustic_gunshot_sensors.geojson", driver="GeoJSON")

import geopandas as gpd
from shapely.geometry import Point

valid_grid_sorted_cams = valid_grid.sort_values("RiskPoaching", ascending=False).iloc[13:45]
cam_points = []
for xy in zip(valid_grid_sorted_cams['centroid_x'], valid_grid_sorted_cams['centroid_y']):
    cam_points.append(Point(xy))
    cam_points.append(Point(xy))
cam_gdf = gpd.GeoDataFrame({'geometry': cam_points}, crs=valid_grid.crs)
cam_gdf['camera_id'] = range(1, 65)

cam_gdf.to_file("normal_cameras.geojson", driver="GeoJSON")

print("Done")