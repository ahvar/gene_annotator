from datetime import datetime
import pandas as pd
import sqlalchemy as sa
from pathlib import Path
from src.app import db
from src.app.models.pipeline_run import PipelineRun
from src.app.models.gene import Gene, GeneAnnotation
from src.utils.pipeline_utils import pipeline_logger, _parse_timestamp
from src.utils.references import (
    final_results_file_name,
    gene_stable_id_col,
    gene_type_col,
    hgnc_id_col,
    hgnc_id_exists_col,
    panther_id_col,
    tigrfam_id_col,
    pid_suffix_col
)


def load_pipeline_results_into_db(final_csv_path: Path) -> None:
    """Load final results CSV into Gene and GeneAnnotation tables"""
    df = pd.read_csv(final_csv_path)

    for _, row in df.iterrows():
        # Find or create Gene
        stmt = (
            sa.select(Gene)
            .where(Gene.gene_stable_id == row[gene_stable_id_col])
            .where(Gene.hgnc_id == row[hgnc_id_col])
        )
        gene = db.session.scalar(stmt)

        if gene is None:
            gene = Gene(
                gene_stable_id=row[gene_stable_id_col],
                gene_type=row[gene_type_col],
                gene_name=row["gene_name"],
                hgnc_name=row["hgnc_name"],
                hgnc_id=row[hgnc_id_col],
                hgnc_id_exists=row[hgnc_id_exists_col],
            )
            db.session.add(gene)
            db.session.flush()

        # Find or create GeneAnnotation
        stmt = (
            sa.select(GeneAnnotation)
            .where(GeneAnnotation.gene_stable_id == row[gene_stable_id_col])
            .where(GeneAnnotation.panther_id == row[panther_id_col])
            .where(GeneAnnotation.tigrfam_id == row[tigrfam_id_col])
        )
        annotation = db.session.scalar(stmt)

        if annotation is None:
            annotation = GeneAnnotation(
                gene_stable_id=row[gene_stable_id_col],
                hgnc_id=row[hgnc_id_col],
                panther_id=row[panther_id_col],
                tigrfam_id=row[tigrfam_id_col],
                wikigene_name=row["wikigene_name"],
                gene_description=row["gene_description"],
                pid_suffix=row[pid_suffix_col],
            )
            db.session.add(annotation)

    db.session.commit()


def process_pipeline_run(output_dir: Path) -> None:
    """Process a pipeline run if not already loaded"""
    timestamp = _parse_timestamp(output_dir)
    existing = PipelineRun.query.filter_by(output_dir=str(output_dir)).first()

    if existing:
        pipeline_logger.info(f"Pipeline run {output_dir} already processed")
        return

    results_file = output_dir / "results" / final_results_file_name
    if not results_file.exists():
        raise FileNotFoundError(f"Results file not found: {results_file}")

    load_pipeline_results_into_db(results_file)

    run = PipelineRun(timestamp=timestamp, output_dir=str(output_dir))
    db.session.add(run)
    db.session.commit()
