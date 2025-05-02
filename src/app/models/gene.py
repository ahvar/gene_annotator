from src.app import db
import sqlalchemy as sa
import sqlalchemy.orm as so
from datetime import datetime


class Gene(db.Model):
    __tablename__ = "gene"

    id: so.Mapped[int] = so.mapped_column(primary_key=True)

    # Columns that map to the CSV
    gene_stable_id: so.Mapped[str] = so.mapped_column(sa.String(50), index=True)
    gene_type: so.Mapped[str] = so.mapped_column(sa.String(50), nullable=True)
    gene_name: so.Mapped[str] = so.mapped_column(sa.String(100), nullable=True)
    hgnc_name: so.Mapped[str] = so.mapped_column(sa.String(100), nullable=True)
    hgnc_id: so.Mapped[str] = so.mapped_column(sa.String(50), nullable=True)

    # Optionally store the “hgnc_id_exists” flag in the DB:
    hgnc_id_exists: so.Mapped[bool] = so.mapped_column(default=False)

    # Timestamps, housekeeping, etc
    created_at: so.Mapped[datetime] = so.mapped_column(default=datetime.utcnow)
    updated_at: so.Mapped[datetime] = so.mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<Gene {self.gene_stable_id}>"


class GeneAnnotation(db.Model):
    __tablename__ = "gene_annotation"

    id: so.Mapped[int] = so.mapped_column(primary_key=True)

    # Columns that map to the TSV
    gene_stable_id: so.Mapped[str] = so.mapped_column(sa.String(50), index=True)
    hgnc_id: so.Mapped[str] = so.mapped_column(sa.String(50), nullable=True)
    panther_id: so.Mapped[str] = so.mapped_column(sa.String(100), nullable=True)
    tigrfam_id: so.Mapped[str] = so.mapped_column(sa.String(100), nullable=True)
    wikigene_name: so.Mapped[str] = so.mapped_column(sa.String(100), nullable=True)
    gene_description: so.Mapped[str] = so.mapped_column(sa.Text(), nullable=True)

    # Optionally store “pid_suffix”:
    pid_suffix: so.Mapped[str] = so.mapped_column(sa.String(50), nullable=True)

    created_at: so.Mapped[datetime] = so.mapped_column(default=datetime.utcnow)
    updated_at: so.Mapped[datetime] = so.mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<GeneAnnotation {self.id}>"
