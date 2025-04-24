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
    timestamp: so.Mapped[Optional[datetime]] = so.mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
    output_dir: so.Mapped[str] = so.mapped_column(
        sa.String(120), index=True, unique=True
    )
    loaded_at: so.Mapped[Optional[datetime]] = so.mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self):
        return f"<PipelineRun {self.timestamp} {self.output_dir}>"
