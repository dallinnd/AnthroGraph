import pandas as pd
import io
import json
from pyscript import document, window
from pyodide.ffi import create_proxy

def generate_graph(event):
    # 1. Get the file from the input element
    file_input = document.getElementById('csv-upload')
    
    if file_input.files.length == 0:
        window.alert("Please upload a CSV file first.")
        return

    file = file_input.files.item(0)

    # 2. Define a callback to process the file once it's read
    def process_data(e):
        # Read the text content of the CSV
        csv_text = e.target.result
        
        # Load into Pandas
        df = pd.read_csv(io.StringIO(csv_text))
        
        # We assume the CSV has at least two numeric columns and a label column
        # For robustness, we'll just grab the first three columns
        cols = df.columns
        if len(cols) < 2:
            window.alert("CSV needs at least 2 columns for X and Y.")
            return
            
        x_col = cols[0]
        y_col = cols[1]
        text_col = cols[2] if len(cols) > 2 else cols[0]

        # Get the custom colors from the UI
        pt_color = document.getElementById('pt-color').value
        ln_color = document.getElementById('ln-color').value

        # 3. Create the Plotly JSON trace data
        trace = {
            "x": df[x_col].tolist(),
            "y": df[y_col].tolist(),
            "mode": "markers+lines+text",
            "type": "scatter",
            "text": df[text_col].tolist(),
            "textposition": "top center",
            "marker": { "color": pt_color, "size": 10 },
            "line": { "color": ln_color, "width": 2 }
        }
        
        layout = {
            "title": "Anthropac Output Graph",
            "xaxis": { "title": x_col },
            "yaxis": { "title": y_col },
            "hovermode": "closest"
        }

        # 4. Render the graph using Plotly.js via window object
        # We stringify the Python dicts into JSON so JavaScript can read them
        window.Plotly.newPlot(
            "plot-container", 
            window.JSON.parse(json.dumps([trace])), 
            window.JSON.parse(json.dumps(layout))
        )

    # 5. Use the JavaScript FileReader to read the file
    file_reader = window.FileReader.new()
    # create_proxy allows the JS FileReader to call our Python function
    file_reader.onload = create_proxy(process_data)
    file_reader.readAsText(file)
