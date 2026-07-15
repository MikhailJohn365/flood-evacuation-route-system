from flask import Flask, request, render_template_string
import osmnx as ox
import networkx as nx
import folium
from geopy.geocoders import Nominatim
import random

app = Flask(__name__)

graph = None
geolocator = None


def load_graph():
    global graph
    if graph is not None:
        return graph

    try:
        print("Loading targeted road network into memory...")
        place = "Aluva, Kerala, India"
        graph = ox.graph_from_place(place, network_type="drive")
        print("Road network loaded successfully!")

        for u, v, key, data in graph.edges(keys=True, data=True):
            mock_elevation = random.uniform(1.0, 30.0)
            mock_river_proximity = random.uniform(0.0, 3.0)

            if mock_elevation < 10.0 and mock_river_proximity < 1.2:
                flood_probability = random.uniform(0.75, 1.0)
            else:
                flood_probability = random.uniform(0.0, 0.25)

            data['flood_risk'] = flood_probability
            penalty_factor = 15.0
            data['risk_adjusted_weight'] = data['length'] * (1 + penalty_factor * flood_probability)

        return graph
    except Exception as exc:
        print(f"Warning: Unable to load road network: {exc}")
        return None


def get_geolocator():
    global geolocator
    if geolocator is None:
        geolocator = Nominatim(user_agent="kerala_flood_web")
    return geolocator


def geocode_location(query):
    try:
        return get_geolocator().geocode(query)
    except Exception as exc:
        print(f"Warning: Geocoding failed for {query}: {exc}")
        return None

# --- 2. FRONTEND HTML INTERFACE DESIGN (Embedded directly as a string) ---
HTML_INTERFACE = """
<!DOCTYPE html>
<html>
<head>
    <title>Flood Evacuation Route Recommendation System</title>
    <style>
        body { font-family: Arial, sans-serif; background: #e9f4ff; margin: 0; padding: 20px; }
        .container { width: 500px; margin: 60px auto; background: white; padding: 40px; border-radius: 15px; box-shadow: 0 0 15px gray; }
        h1 { color: #0066cc; text-align: center; font-size: 24px; }
        p { text-align: center; color: #555; }
        input { width: 100%; padding: 12px; margin-top: 10px; margin-bottom: 20px; border-radius: 8px; border: 1px solid gray; box-sizing: border-box; }
        button { width: 100%; padding: 14px; background: #007BFF; color: white; border: none; border-radius: 8px; font-size: 18px; cursor: pointer; font-weight: bold; }
        button:hover { background: #0056b3; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Flood Evacuation Route System</h1>
        <p>AI & Data Science Based Safe Route Recommendation for Kerala</p>
        <form action="/get_route" method="POST">
            <label><b>Current Location</b></label>
            <input type="text" name="source" placeholder="e.g., Aluva Railway Station" required>
            
            <label><b>Destination Shelter</b></label>
            <input type="text" name="destination" placeholder="e.g., Aluva Manappuram" required>
            
            <button type="submit">Find Safest Route</button>
        </form>
    </div>
</body>
</html>
"""

# --- 3. FLASK ROUTING ENDPOINTS ---
@app.route('/')
def home():
    with app.app_context():
        return render_template_string(HTML_INTERFACE)

@app.route('/get_route', methods=['POST'])
def get_route():
    source = request.form.get('source', '').strip()
    destination = request.form.get('destination', '').strip()

    if not source or not destination:
        return "<h3>Error: Please enter both a starting location and a destination shelter.</h3>"

    network_graph = load_graph()
    if network_graph is None:
        return "<h3>Service unavailable: the road network could not be loaded right now. Please try again shortly.</h3>"

    source_loc = geocode_location(source + ", Aluva, Kerala")
    dest_loc = geocode_location(destination + ", Aluva, Kerala")

    if not source_loc or not dest_loc:
        return "<h3>Error: One or both locations could not be verified in the local target area. Go back and try again.</h3>"

    try:
        orig = ox.distance.nearest_nodes(network_graph, X=source_loc.longitude, Y=source_loc.latitude)
        dest = ox.distance.nearest_nodes(network_graph, X=dest_loc.longitude, Y=dest_loc.latitude)

        standard_route = nx.shortest_path(network_graph, orig, dest, weight="length")
        ai_evac_route = nx.shortest_path(network_graph, orig, dest, weight="risk_adjusted_weight")

        m = folium.Map(location=[source_loc.latitude, source_loc.longitude], zoom_start=14)

        folium.Marker([source_loc.latitude, source_loc.longitude], popup="START", icon=folium.Icon(color="green")).add_to(m)
        folium.Marker([dest_loc.latitude, dest_loc.longitude], popup="SHELTER", icon=folium.Icon(color="red")).add_to(m)

        std_coords = [(network_graph.nodes[node]['y'], network_graph.nodes[node]['x']) for node in standard_route]
        folium.PolyLine(std_coords, color="red", weight=3, opacity=0.5, dash_array='5,5', tooltip="Standard Distance Path").add_to(m)

        evac_coords = [(network_graph.nodes[node]['y'], network_graph.nodes[node]['x']) for node in ai_evac_route]
        folium.PolyLine(evac_coords, color="blue", weight=6, opacity=0.9, tooltip="AI Recommended Safe Route").add_to(m)

        return m._repr_html_()
    except Exception as e:
        return f"<h3>Routing Error: Could not compute paths between these points. Details: {str(e)}</h3>"

if __name__ == '__main__':
    # use_reloader=False prevents Python 3.14 alpha crash loops on Windows
    app.run(debug=True, use_reloader=False, port=5000)