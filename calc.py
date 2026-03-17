import pandas as pd
import io
import json
from pyscript import document, window
from pyodide.ffi import create_proxy

# Global variables to hold state
global_df = None
x_col = y_col = z_col = text_col = ""

def hex_to_rgba(hex_color, alpha):
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"

def update_plot(event=None):
    """Reads UI state (checkboxes and colors) and redraws the plot."""
    if global_df is None or global_df.empty:
        return

    # 1. Get Selected Colors
    pt_color = document.getElementById('pt-color').value
    ln_color = document.getElementById('ln-color').value
    ln_opacity = document.getElementById('ln-opacity').value
    rgba_line_color = hex_to_rgba(ln_color, ln_opacity)

    # 2. Find which rows are checked in the HTML table
    checkboxes = document.querySelectorAll('.row-checkbox')
    selected_indices = []
    for cb in checkboxes:
        if cb.checked:
            selected_indices.append(int(cb.value))
            
    # 3. Filter DataFrame
    filtered_df = global_df.iloc[selected_indices]

    if filtered_df.empty:
        window.Plotly.purge("plot-container")
        return

    # 4. Redraw Plotly Graph
    trace = {
        "x": filtered_df[x_col].tolist(),
        "y": filtered_df[y_col].tolist(),
        "z": filtered_df[z_col].tolist(),
        "mode": "markers+lines+text",
        "type": "scatter3d",
        "text": filtered_df[text_col].tolist(),
        "textposition": "top center",
        "marker": { "color": pt_color, "size": 6 },
        "line": { "color": rgba_line_color, "width": 4 }
    }
    
    layout = {
        "margin": {"l": 0, "r": 0, "b": 0, "t": 20},
        "scene": {
            "xaxis": { "title": x_col },
            "yaxis": { "title": y_col },
            "zaxis": { "title": z_col }
        },
        "hovermode": "closest"
    }

    window.Plotly.newPlot(
        "plot-container", 
        window.JSON.parse(json.dumps([trace])), 
        window.JSON.parse(json.dumps(layout))
    )

def load_csv(event):
    """Triggered when user clicks 'Load Data'"""
    file_input = document.getElementById('csv-upload')
    if file_input.files.length == 0:
        window.alert("Please select a CSV file first.")
        return

    file = file_input.files.item(0)

    def process_data(e):
        global global_df, x_col, y_col, z_col, text_col
        
        csv_text = e.target.result
        global_df = pd.read_csv(io.StringIO(csv_text))
        
        cols = global_df.columns
        if len(cols) < 3:
            window.alert("CSV needs at least 3 columns for X, Y, and Z.")
            return
            
        x_col, y_col, z_col = cols[0], cols[1], cols[2]
        text_col = cols[3] if len(cols) > 3 else cols[0]

        # Build the HTML Table
        table_html = "<table><thead><tr><th>Show</th>"
        for col in global_df.columns:
            table_html += f"<th>{col}</th>"
        table_html += "</tr></thead><tbody>"
        
        for idx, row in global_df.iterrows():
            table_html += f"<tr><td><input type='checkbox' class='row-checkbox' value='{idx}' checked></td>"
            for val in row:
                table_html += f"<td>{val}</td>"
            table_html += "</tr>"
        table_html += "</tbody></table>"
        
        document.getElementById("table-container").innerHTML = table_html
        
        # Attach event listeners to new checkboxes so they update the graph
        proxy_update = create_proxy(update_plot)
        checkboxes = document.querySelectorAll('.row-checkbox')
        for cb in checkboxes:
            cb.addEventListener('change', proxy_update)

        # Draw the initial plot
        update_plot()

    file_reader = window.FileReader.new()
    file_reader.onload = create_proxy(process_data)
    file_reader.readAsText(file)

# Attach event listeners to color pickers and slider so they update in real-time
proxy_realtime_update = create_proxy(update_plot)
document.getElementById('pt-color').addEventListener('input', proxy_realtime_update)
document.getElementById('ln-color').addEventListener('input', proxy_realtime_update)
document.getElementById('ln-opacity').addEventListener('input', proxy_realtime_update)
