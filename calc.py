import pandas as pd
import io
import json
from pyscript import document, window
from pyodide.ffi import create_proxy

# Helper function to convert Hex + Alpha to RGBA for Plotly
def hex_to_rgba(hex_color, alpha):
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"

def generate_graph(event):
    file_input = document.getElementById('csv-upload')
    
    if file_input.files.length == 0:
        window.alert("Please upload a CSV file first.")
        return

    file = file_input.files.item(0)

    def process_data(e):
        csv_text = e.target.result
        df = pd.read_csv(io.StringIO(csv_text))
        
        cols = df.columns
        # Now requiring at least 3 columns for 3D
        if len(cols) < 3:
            window.alert("CSV needs at least 3 columns for X, Y, and Z.")
            return
            
        x_col = cols[0]
        y_col = cols[1]
        z_col = cols[2]
        # Use the 4th column as text labels, otherwise default to X
        text_col = cols[3] if len(cols) > 3 else cols[0]

        # Get values from UI
        pt_color = document.getElementById('pt-color').value
        ln_color = document.getElementById('ln-color').value
        ln_opacity = document.getElementById('ln-opacity').value
        
        # Convert to RGBA for line transparency
        rgba_line_color = hex_to_rgba(ln_color, ln_opacity)

        # 3D Plotly Trace
        trace = {
            "x": df[x_col].tolist(),
            "y": df[y_col].tolist(),
            "z": df[z_col].tolist(),
            "mode": "markers+lines+text",
            "type": "scatter3d",  # Changed to 3D
            "text": df[text_col].tolist(),
            "textposition": "top center",
            "marker": { "color": pt_color, "size": 6 }, # Slightly smaller markers for 3D
            "line": { "color": rgba_line_color, "width": 4 } # Uses custom RGBA
        }
        
        # 3D Layout
        layout = {
            "title": "3D Anthropac Output Graph",
            "scene": {
                "xaxis": { "title": x_col },
                "yaxis": { "title": y_col },
                "zaxis": { "title": z_col }
            },
            "margin": {"l": 0, "r": 0, "b": 0, "t": 40}, # Minimizes blank space around 3D cube
            "hovermode": "closest"
        }

        window.Plotly.newPlot(
            "plot-container", 
            window.JSON.parse(json.dumps([trace])), 
            window.JSON.parse(json.dumps(layout))
        )

    file_reader = window.FileReader.new()
    file_reader.onload = create_proxy(process_data)
    file_reader.readAsText(file)
