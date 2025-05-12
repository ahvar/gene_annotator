from datetime import datetime, timezone
import pandas as pd
import typer
from unittest.mock import MagicMock
from flask_babel import _
from flask import render_template, flash, redirect, url_for, request
from flask_login import current_user
import sqlalchemy as sa
from pathlib import Path
from src.app import db
from src.app.models.pipeline_run import PipelineRun, PipelineResult
from src.app.models.gene import Gene, GeneAnnotation
from src.utils.pipeline_utils import (
    pipeline_logger,
    _parse_timestamp,
    GeneReader,
    validate_outputdir,
)
from src.utils.references import (
    final_results_file_name,
    gene_stable_id_col,
    gene_type_col,
    hgnc_id_col,
    hgnc_id_exists_col,
    panther_id_col,
    tigrfam_id_col,
    pid_suffix_col,
)


def load_pipeline_results_into_db(final_csv_path: Path) -> None:
    """
    Load final results CSV produced by the pipeline into the database
    Returns the created PipelineRun object
    """
    # Get the output directory containing the results
    output_dir = final_csv_path.parent.parent
    # Parse timestamp from the output directory name instead of creating a new one
    timestamp = _parse_timestamp(output_dir)
    # Ensure the timestamp is timezone-aware
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    run = PipelineRun(
        timestamp=timestamp,
        output_dir=str(
            final_csv_path.parent.parent
        ),  # The output directory containing results
        pipeline_name=_("Gene Annotation Pipeline"),
        pipeline_type="UI",
        researcher_id=current_user.id,
        status="complete",
    )

    # Add and commit the run to get an ID
    db.session.add(run)
    db.session.commit()

    df = pd.read_csv(final_csv_path)
    df = df.fillna("")

    # Create PipelineResult records linked to this run
    for unused_index, row in df.iterrows():
        result = PipelineResult(
            run_id=run.id,
            gene_stable_id=row[gene_stable_id_col],
            gene_type=row[gene_type_col],
            gene_name=row["gene_name"],
            hgnc_name=row["hgnc_name"],
            hgnc_id=row[hgnc_id_col],
            panther_id=row[panther_id_col],
            tigrfam_id=row[tigrfam_id_col],
            wikigene_name=row["wikigene_name"],
            gene_description=row["gene_description"],
            pid_suffix=row[pid_suffix_col],
        )
        db.session.add(result)

    db.session.commit()
    return run


def process_pipeline_run(output_dir: Path = None) -> None:
    """Process a pipeline run if not already loaded"""
    if output_dir is None:
        mock_ctx = MagicMock(spec=typer.Context)
        output_dir = validate_outputdir(mock_ctx, None)
        gene_reader = GeneReader()
    else:
        gene_reader = GeneReader(input_dir=output_dir)

    try:
        gene_reader.find_and_load_gene_data()
        gene_reader.log_duplicates()
        gene_reader.remove_duplicates()
        gene_reader.log_unique_records()
        gene_reader.determine_if_hgnc_id_exists()
        gene_reader.parse_panther_id_suffix()
        gene_reader.merge_gene_and_annotations(
            col_one=gene_stable_id_col, col_two=hgnc_id_col
        )

        results_dir = output_dir / "results"
        results_dir.mkdir(exist_ok=True)
        gene_reader.write_gene_and_annotations_final(results_dir)
        results_file = results_dir / final_results_file_name
        run = load_pipeline_results_into_db(results_file)
        return run
    except Exception as e:
        pipeline_logger.error(f"Pipeline error: {e}")
        raise
