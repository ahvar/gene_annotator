"""
Useful variables for later reference
"""

from typing import Any
from dataclasses import dataclass, field

__version__ = "0.1.0"
__copyright__ = "Copyright \xa9 2025 Arthur Vargas | All rights reserved.".encode(
    "utf-8", "ignore"
)
__Application__ = "GENE_ANNOTATOR"

GENE_ANNOTATOR_CLI = f"{__Application__}_{__version__}_cli"
GENE_ANNOTATOR_FRONTEND = f"{__Application__}_{__version__}_frontend"

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
