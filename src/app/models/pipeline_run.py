from datetime import datetime, timezone
from typing import Optional
import sqlalchemy as sa
import sqlalchemy.orm as so
from src.app import db


class PipelineRun(db.Model):
    """
    Model representing a pipeline execution run.
    Tracks when pipeline data was loaded into the database.
    """

    __tablename__ = "pipeline_run"
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    pipeline_name: so.Mapped[str] = so.mapped_column(sa.String(140))
    pipeline_type: so.Mapped[str] = so.mapped_column(sa.String(140))
    researcher_id: so.Mapped[int] = so.mapped_column(
        sa.ForeignKey("researcher.id"),
        name="fk_pipeline_run_researcher_id",
        nullable=False,
    )
    researcher: so.Mapped["Researcher"] = so.relationship(
        "Researcher", back_populates="runs"
    )
    # results: so.Mapped[list["Results"]] = so.relationship("Result", back_populates=)
    timestamp: so.Mapped[Optional[datetime]] = so.mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
    output_dir: so.Mapped[str] = so.mapped_column(
        sa.String(120), index=True, unique=True
    )
    loaded_at: so.Mapped[Optional[datetime]] = so.mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
    status: so.Mapped[str] = so.mapped_column(sa.String(50), default="pending")
    results: so.Mapped[list["PipelineResult"]] = so.relationship(
        "PipelineResult", back_populates="run", cascade="all, delete-orphan"
    )

    @property
    def formatted_timestamp(self):
        return self.timestamp.strftime("%Y-%m-%d %H:%M:%S")

    def __repr__(self):
        return f"<PipelineRun {self.timestamp} {self.output_dir}>"


class PipelineResult(db.Model):
    """Model representing results from a pipeline run"""

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    run_id: so.Mapped[int] = so.mapped_column(
        sa.ForeignKey("pipeline_run.id"),
        name="fk_pipeline_result_run_id",
        nullable=False,
    )
    gene_stable_id: so.Mapped[str] = so.mapped_column(sa.String(128))
    gene_type: so.Mapped[str] = so.mapped_column(sa.String(64))
    gene_name: so.Mapped[str] = so.mapped_column(sa.String(128))
    hgnc_name: so.Mapped[Optional[str]] = so.mapped_column(sa.String(128))
    hgnc_id: so.Mapped[Optional[str]] = so.mapped_column(sa.String(128))
    panther_id: so.Mapped[Optional[str]] = so.mapped_column(sa.String(128))
    tigrfam_id: so.Mapped[Optional[str]] = so.mapped_column(sa.String(128))
    wikigene_name: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))
    gene_description: so.Mapped[Optional[str]] = so.mapped_column(sa.String(1024))
    pid_suffix: so.Mapped[Optional[str]] = so.mapped_column(sa.String(64))

    run: so.Mapped["PipelineRun"] = so.relationship(
        "PipelineRun", back_populates="results"
    )
