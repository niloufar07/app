import streamlit as st
import geopandas as gpd
import pandas as pd
from streamlit_folium import folium_static
import folium
import json
from shapely.geometry import Point, box

# Load the data for Bari
mobility_matrix = pd.read_csv("https://raw.githubusercontent.com/niloufar07/app/main/matrix.csv", index_col=0)
city_data = gpd.read_file("https://raw.githubusercontent.com/niloufar07/app/main/updated_city_coordinates.geojson")
road_data = gpd.read_file("https://raw.githubusercontent.com/niloufar07/app/main/Apugliamain.geojson")

# Define bounding box for Bari Province
minx, miny, maxx, maxy = 16.291, 40.712, 17.517, 41.322

# Create a bounding box
bari_bbox = box(minx, miny, maxx, maxy)

# Filter city data within Bari province bounding box
bari_cities_gdf = city_data[city_data['geometry'].within(bari_bbox)]

# Create a base map centered around Bari
bari_center = [(miny + maxy) / 2, (minx + maxx) / 2]
bari_map = folium.Map(location=bari_center, zoom_start=10)

# Add GeoJSON layers to the map for filtered cities
folium.GeoJson(bari_cities_gdf.to_json(), name='Bari Cities', style_function=lambda x: {'color': 'red', 'weight': 2}).add_to(bari_map)

# Add markers for the filtered cities
for idx, row in bari_cities_gdf.iterrows():
    folium.Marker(location=[row.geometry.y, row.geometry.x], popup=row.city).add_to(bari_map)

# Add bounding box to the map for visual reference
folium.GeoJson(json.loads(gpd.GeoSeries([bari_bbox]).to_json()), name='Bounding Box', style_function=lambda x: {'color': 'green', 'weight': 2, 'fillOpacity': 0.1}).add_to(bari_map)

# Add Layer Control to the map
folium.LayerControl().add_to(bari_map)

# Display the map
st.title("Map of Bari Province with Cities and Bounding Box")
folium_static(bari_map)
