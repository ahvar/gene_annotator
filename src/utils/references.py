"""
Useful variables for later reference
"""
from typing import Any
from dataclasses import dataclass, field

genes_file_name = "genes.csv"
gene_annotations_file_name = "gene_annotation.tsv"
gene_type_col = "gene_type"
gene_type_count_out_file = "gene_type_count.csv"
count_col = "count"
hgnc_id_exists_col = "hgnc_id_exists"
hgnc_id_col = "hgnc_id"
pid_suffix_col = "pid_suffix"
panther_id_col = "panther_id"
gene_stable_id_col = "gene_stable_id"
excluded_tigrfam_file_name = "excluded_tigrfam_ids.csv"
tigrfam_id_col = "tigrfam_id"
excluded_tigrfam_vals = ["TIGR00658", "TIGR00936"]
final_results_file_name = "final_results.csv"

summary_styles = ["json", "txt"]
