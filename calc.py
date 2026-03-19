import pandas as pd
import numpy as np
import json
import io
from scipy.spatial.distance import pdist, squareform
from scipy.cluster.hierarchy import linkage, fcluster
from sklearn.manifold import MDS
from pyscript import document, window
from pyodide.ffi import create_proxy

def process_data(event):
    file_input = document.getElementById('csv-upload')
    mode = document.getElementById('current-mode').value
    k_val = int(document.getElementById('k-value').value)
    
    if file_input.files.length == 0:
        window.alert("Please upload a .csv file.")
        return

    file = file_input.files.item(0)

    def on_file_load(e):
        csv_text = e.target.result
        df = pd.read_csv(io.StringIO(csv_text))
        
        try:
            # ---------------------------------------------------------
            # PATH 1: FREE LIST & PARTITIONS
            # ---------------------------------------------------------
            if mode in ["freelist", "freelist-filter", "partitions"]:
                # Error checking for exact headers required by the SOP
                if not all(col in df.columns for col in ['Subj', 'Order', 'Code']):
                    window.alert("Error: Free List CSV must contain 'Subj', 'Order', and 'Code' columns.")
                    return
                
                # Filtering logic
                if mode in ["freelist-filter", "partitions"]:
                    counts = df['Code'].value_counts()
                    items_to_keep = counts[counts >= 2].index
                    df = df[df['Code'].isin(items_to_keep)].copy()
                    
                # Calculate Smith's Salience
                list_lengths = df.groupby("Subj")["Order"].max().reset_index()
                list_lengths.rename(columns={"Order": "L"}, inplace=True)
                df_final = pd.merge(df, list_lengths, on="Subj")
                df_final["Salience"] = (df_final["L"] - df_final["Order"] + 1) / df_final["L"]
                
                # Convert to wide matrix
                wide_data = df_final.pivot_table(index="Code", columns="Subj", values="Salience", fill_value=0)
                
                # Calculate Distance Matrix
                condensed_dist = pdist(wide_data, metric='braycurtis')
                dist_matrix_sq = squareform(condensed_dist)
                labels = wide_data.index.tolist()

            # ---------------------------------------------------------
            # PATH 2: PILE SORT
            # ---------------------------------------------------------
            elif mode == "pilesort":
                # Error checking for exact headers required by the SOP
                if not all(col in df.columns for col in ['Subject', 'Item', 'Pile']):
                    window.alert("Error: Pile Sort CSV must contain 'Subject', 'Item', and 'Pile' columns.")
                    return
                    
                wide_ps = df.pivot(index="Item", columns="Subject", values="Pile")
                n_items = len(wide_ps)
                similarity = np.zeros((n_items, n_items))
                
                # Iterate and count pile matches
                for i in range(n_items):
                    for j in range(n_items):
                        similarity[i, j] = (wide_ps.iloc[i] == wide_ps.iloc[j]).sum()
                        
                max_subj = df["Subject"].nunique()
                dist_matrix_sq = max_subj - similarity
                condensed_dist = squareform(dist_matrix_sq, checks=False)
                labels = wide_ps.index.tolist()

            # ---------------------------------------------------------
            # UNIVERSAL MATH: MDS SCALING
            # ---------------------------------------------------------
            # Added normalized_stress='auto' to suppress scikit-learn FutureWarning
            mds = MDS(n_components=2, dissimilarity='precomputed', random_state=123, normalized_stress='auto')
            coords = mds.fit_transform(dist_matrix_sq)
            stress = mds.stress_
            
            mds_df = pd.DataFrame(coords, columns=["NMDS1", "NMDS2"], index=labels)
            mds_df["Item"] = labels
            
            # ---------------------------------------------------------
            # PLOTTING LOGIC (Trace Generation)
            # ---------------------------------------------------------
            traces = []
            
            # If clustering is required
            if mode in ["partitions", "pilesort"]:
                Z = linkage(condensed_dist, method='average')
                clusters = fcluster(Z, t=k_val, criterion='maxclust')
                mds_df["Cluster"] = clusters
                
                unique_clusters = np.unique(clusters)
                colors = ['#EF553B', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3', '#FF6692', '#B6E880', '#FF97FF']
                
                for i, c in enumerate(unique_clusters):
                    cluster_data = mds_df[mds_df["Cluster"] == c]
                    color = colors[i % len(colors)]
                    traces.append({
                        "x": cluster_data["NMDS1"].tolist(),
                        "y": cluster_data["NMDS2"].tolist(),
                        "mode": "markers+text",
                        "type": "scatter",
                        "name": f"Cluster {c}",
                        "text": cluster_data["Item"].tolist(),
                        "textposition": "top right", # Offset to mimic ggrepel
                        "textfont": {"weight": "bold", "color": "black"},
                        "marker": {"size": 12, "color": color, "line": {"width": 1, "color": "white"}}
                    })
            
            # If standard plotting without clusters
            else:
                traces.append({
                    "x": mds_df["NMDS1"].tolist(),
                    "y": mds_df["NMDS2"].tolist(),
                    "mode": "markers+text",
                    "type": "scatter",
                    "text": mds_df["Item"].tolist(),
                    "textposition": "top right", # Offset to mimic ggrepel
                    "textfont": {"weight": "bold", "color": "black"},
                    "marker": {"size": 12, "color": "#f39c12"}
                })
                
            # Dynamic Layout Titles based on Mode
            titles = {
                "freelist": f"Semantic Space (MDS)<br><sup>Stress: {stress:.3f}</sup>",
                "freelist-filter": f"Filtered Semantic Space<br><sup>Stress: {stress:.3f}</sup>",
                "partitions": f"Filtered Space with Average-Link Partitions (k={k_val})<br><sup>Stress: {stress:.3f}</sup>",
                "pilesort": f"Pile Sort MDS: Average-Link Partitions (k={k_val})<br><sup>Stress: {stress:.3f}</sup>"
            }

            # Define axes titles based on Anthropac conventions
            x_title = "Dimension 1" if mode == "pilesort" else "NMDS1"
            y_title = "Dimension 2" if mode == "pilesort" else "NMDS2"

            # Layout to mimic R's theme_bw()
            layout = {
                "title": titles[mode],
                "xaxis": {
                    "title": x_title, 
                    "showgrid": True, 
                    "gridcolor": "#e0e6ed", 
                    "zeroline": False, 
                    "showticklabels": True,
                    "linecolor": "black",
                    "mirror": True
                },
                "yaxis": {
                    "title": y_title, 
                    "showgrid": True, 
                    "gridcolor": "#e0e6ed", 
                    "zeroline": False, 
                    "showticklabels": True,
                    "linecolor": "black",
                    "mirror": True
                },
                "plot_bgcolor": "#ffffff",
                "paper_bgcolor": "#ffffff",
                "hovermode": "closest",
                "margin": {"t": 80, "b": 60, "l": 60, "r": 40}
            }

            # Clear the "Awaiting data..." placeholder text before plotting
            document.getElementById("plot-container").innerHTML = ""

            # Draw the Plot
            window.Plotly.newPlot("plot-container", window.JSON.parse(json.dumps(traces)), window.JSON.parse(json.dumps(layout)))
            
        except Exception as ex:
            window.alert(f"Error processing data. Check your CSV formatting. System read: {str(ex)}")

    # Execute file read sequence
    file_reader = window.FileReader.new()
    file_reader.onload = create_proxy(on_file_load)
    file_reader.readAsText(file)
