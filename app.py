import pandas as pd
import geopandas as gpd
import networkx as nx
from shapely.geometry import Point, box
import matplotlib.pyplot as plt
import folium
import json
import streamlit as st
from streamlit_folium import folium_static

st.title("Map of Bari Province with Cities and Bounding Box")

# Load the data for Bari
mobility_matrix_url = "https://raw.githubusercontent.com/niloufar07/app/main/matrix.csv"
city_data_url = "https://raw.githubusercontent.com/niloufar07/app/main/updated_city_coordinates%20.geojson"
road_data_url = "https://raw.githubusercontent.com/niloufar07/app/main/Apugliamain.geojson"

# Check if the URLs are accessible
try:
    mobility_matrix = pd.read_csv(mobility_matrix_url, index_col=0)
except Exception as e:
    st.error(f"Failed to load mobility matrix: {e}")
    st.stop()

try:
    city_data = gpd.read_file(city_data_url)
except Exception as e:
    st.error(f"Failed to load city data: {e}")
    st.stop()

try:
    road_data = gpd.read_file(road_data_url)
except Exception as e:
    st.error(f"Failed to load road data: {e}")
    st.stop()

# Define bounding box for Bari Province
minx, miny, maxx, maxy = 16.291, 40.712, 17.517, 41.322

# Create a bounding box
bari_bbox = box(minx, miny, maxx, maxy)

# Filter city data within Bari province bounding box
bari_cities_gdf = city_data[city_data['geometry'].within(bari_bbox)]

# Filter road data to only include entries within the bounding box
bari_gdf = gpd.GeoDataFrame(road_data, crs='EPSG:4326')
bari_gdf = bari_gdf[bari_gdf['geometry'].apply(lambda geom: geom.bounds[0] >= minx and geom.bounds[2] <= maxx and geom.bounds[1] >= miny and geom.bounds[3] <= maxy)]

# Filter the mobility matrix to only include the cities in the Bari bounding box
city_names_gdf = set(bari_cities_gdf['city'])
filtered_city_names = list(city_names_gdf.intersection(mobility_matrix.index))
mobility_matrix = mobility_matrix.loc[filtered_city_names, filtered_city_names]

# Step 2: Create directed graph and add road nodes and edges
G = nx.DiGraph()
pos = {}

for idx, row in bari_gdf.iterrows():
    coords = list(row['geometry'].coords)
    for i in range(len(coords) - 1):
        start = coords[i]
        end = coords[i + 1]
        G.add_edge(start, end, weight=1)
        pos[start] = start
        pos[end] = end

# Step 3: Check road nodes
road_nodes = list(G.nodes)
road_nodes_gdf = gpd.GeoDataFrame(geometry=[Point(node) for node in road_nodes], crs='EPSG:4326')
road_nodes_gdf.sindex

# Step 4: Function to find nearest road node
def find_nearest_road_node(city_point, road_nodes_gdf):
    city_point_geom = Point(city_point.x, city_point.y)
    nearest_node_idx = road_nodes_gdf.sindex.nearest([city_point_geom], return_distance=False)[0]
    nearest_node = road_nodes_gdf.iloc[nearest_node_idx].geometry
    if isinstance(nearest_node, gpd.GeoSeries):
        nearest_node = nearest_node.iloc[0]
    return nearest_node

# Step 5: Associate each city with the nearest road node
city_to_nearest_road_node = {}
for idx, city in bari_cities_gdf.iterrows():
    city_name = city['city']
    city_point = city['geometry']
    nearest_node_geom = find_nearest_road_node(city_point, road_nodes_gdf)
    nearest_node_coords = (nearest_node_geom.x, nearest_node_geom.y)

    G.add_node(city_name, pos=(city_point.x, city_point.y))
    pos[city_name] = (city_point.x, city_point.y)

    if nearest_node_coords not in pos:
        G.add_node(nearest_node_coords, pos=nearest_node_coords)
        pos[nearest_node_coords] = nearest_node_coords

    G.add_edge(city_name, nearest_node_coords, weight=0)
    city_to_nearest_road_node[city_name] = nearest_node_coords

# Step 6: Add mobility data (between city nodes only, and directed)
city_graph = nx.DiGraph()
for city1 in city_to_nearest_road_node.keys():
    city_graph.add_node(city1, pos=pos[city1])  # Ensure city_graph has the same nodes with positions
    for city2 in city_to_nearest_road_node.keys():
        if city1 != city2:
            try:
                weight = mobility_matrix.at[city1, city2]
                if weight > 0:
                    city_graph.add_edge(city1, city2, weight=weight)
            except KeyError:
                continue

# Visualize the directed city graph
plt.figure(figsize=(20, 8))
pos = nx.get_node_attributes(city_graph, 'pos')
nx.draw(city_graph, pos, with_labels=True, node_size=2000, node_color='lightblue', font_size=8, font_weight='bold', arrowstyle='->', arrowsize=20, edge_color='darkgrey')

plt.title("City-to-City Mobility Network in Bari Province")
st.pyplot(plt)

# Visualize on a folium map
cities_gdf = gpd.GeoDataFrame(bari_cities_gdf, crs='EPSG:4326')

# Create a base map centered around Bari
bari_center = [(miny + maxy) / 2, (minx + maxx) / 2]
bari_map = folium.Map(location=bari_center, zoom_start=10)

# Add GeoJSON layers to the map for filtered cities
folium.GeoJson(cities_gdf.to_json(), name='Bari Cities', style_function=lambda x: {'color': 'red', 'weight': 2}).add_to(bari_map)

# Add markers for the filtered cities
for idx, row in cities_gdf.iterrows():
    folium.Marker(location=[row.geometry.y, row.geometry.x], popup=row.city).add_to(bari_map)

# Add bounding box to the map for visual reference
folium.GeoJson(json.loads(gpd.GeoSeries([bari_bbox]).to_json()), name='Bounding Box', style_function=lambda x: {'color': 'green', 'weight': 2, 'fillOpacity': 0.1}).add_to(bari_map)

# Add Layer Control to the map
folium.LayerControl().add_to(bari_map)

# Display the map
folium_static(bari_map)
