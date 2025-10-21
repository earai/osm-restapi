import folium

# Coordinates (lon, lat) from the user
coords = [
    [-115.157891, 36.155421],
    [-115.121709, 36.155421],
    [-115.121709, 36.184379],
    [-115.157891, 36.184379],
    [-115.157891, 36.155421]
]
coords_amenity2 =  [[-115.140000, 36.170000],
    [-115.105000, 36.170000],
    [-115.105000, 36.195000],
    [-115.140000, 36.195000],
    [-115.140000, 36.170000]]

coords_road=   [      [-115.280990, 36.105152],
            [-115.279788, 36.121655],
            [-115.296182, 36.111462],
            [-115.280990, 36.105152],
            [-115.280990, 36.105152]]

# Convert to [lat, lon] for folium
coords_latlon = [[lat, lon] for lon, lat in coords]
coords_latlon_amenity2 = [[lat, lon] for lon, lat in coords_amenity2]
coords_latlon_road = [[lat, lon] for lon, lat in coords_road]

# Center of the polygon
center_lat = sum([c[0] for c in coords_latlon]) / len(coords_latlon)
center_lon = sum([c[1] for c in coords_latlon]) / len(coords_latlon)

# Create map
m = folium.Map(location=[center_lat, center_lon], zoom_start=14)


# Add polygon
folium.Polygon(
    locations=coords_latlon,
    color="blue",
    weight=2,
    fill=True,
    fill_color="blue",
    fill_opacity=0.4
).add_to(m)
folium.Polygon(
    locations=coords_latlon_amenity2,
    color="purple",
    weight=2,
    fill=True,
    fill_color="purple",
    fill_opacity=0.4
).add_to(m)
folium.Polygon(
    locations=coords_latlon_road,
    color="green",
    weight=2,
    fill=True,
    fill_color="green",
    fill_opacity=0.4
).add_to(m)

for point in coords_latlon:
    folium.Marker(point).add_to(m)
# save & open
map_file = "polygon_map.html"
m.save(map_file)

# auto-open in browser (optional)
import webbrowser
webbrowser.open(map_file)
