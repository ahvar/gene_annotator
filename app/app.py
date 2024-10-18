#!/usr/bin/env python3

import os
from datetime import datetime
from pathlib import Path
import pandas as pd
from flask import Flask, request, jsonify

app = Flask(__name__)


def get_most_recent_output_dir(base_path: Path):
    """
    find the most recent output directory and load
    the final results
    """
    dirs = [d for d in base_path.iterdir() if d.is_dir() and "output_" in d.name]
    dirs.sort(
        key=lambda x: datetime.strptime(x.name.split("_")[-1], "%m%d%yT%H%M%S"),
        reverse=True,
    )
    return dirs[0] if dirs else None


current_file_path = Path(__file__).resolve()
project_root = current_file_path.parent.parent
data_path = get_most_recent_output_dir(project_root / "etl")

if data_path:
    data = pd.read_csv(data_path / "results" / "final_results.csv")
else:
    data = None


@app.route("/genes", methods=["GET"])
def get_genes():
    """
    Add a single route to API, ".../genes", that allows users to query the data
    that has been loaded into memory by specifying filtering criteria via query
    parameters in the url
    """
    if data is None:
        return jsonify({"error": "Data not initialized. Run the pipeline first!"}), 500

    gene_name = request.args.get("gene_name")
    gene_type = request.args.get("gene_type")

    filtered_data = data
    if gene_name:
        filtered_data = filtered_data[filtered_data["gene_name"] == gene_name]
    if gene_type:
        filtered_data = filtered_data[filtered_data["gene_type"] == gene_type]

    return jsonify(filtered_data.to_dict(orient="records"))


if __name__ == "__main__":
    app.run(port=5000, threaded=True, debug=True)
