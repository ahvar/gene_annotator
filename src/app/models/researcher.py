from typing import Optional
from hashlib import md5
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from src.app import db

import sqlalchemy as sa
import sqlalchemy.orm as so
from src.app import db, login
from src.app.models.pipeline_run import PipelineRun

followers = sa.Table(
    "followers",
    db.metadata,
    sa.Column(
        "follower_id", sa.Integer, sa.ForeignKey("researcher.id"), primary_key=True
    ),
    sa.Column(
        "followed_id", sa.Integer, sa.ForeignKey("researcher.id"), primary_key=True
    ),
)


class Researcher(UserMixin, db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    researcher_name: so.Mapped[str] = so.mapped_column(
        sa.String(64), index=True, unique=True
    )
    email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True, unique=True)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))

    # gene table

    about_me: so.Mapped[Optional[str]] = so.mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
    last_seen: so.Mapped[Optional[datetime]] = so.mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )

    runs: so.Mapped[list["PipelineRun"]] = so.relationship(
        "PipelineRun", back_populates="researcher"
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    following: so.WriteOnlyMapped["Researcher"] = so.relationship(
        secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        back_populates="followers",
    )

    followers: so.WriteOnlyMapped["Researcher"] = so.relationship(
        secondary=followers,
        primaryjoin=(followers.c.followed_id == id),
        secondaryjoin=(followers.c.follower_id == id),
        back_populates="following",
    )

    def follow(self, researcher):
        if not self.is_following(researcher):
            self.following.add(researcher)

    def unfollow(self, researcher):
        if self.is_following(researcher):
            self.following.remove(researcher)

    def is_following(self, researcher):
        query = self.following.select().where(Researcher.id == researcher.id)
        return db.session.scalar(query) is not None

    def followers_count(self):
        query = sa.select(sa.func.count()).select_from(
            self.followers.select().subquery()
        )
        return db.session.scalar(query)

    def following_count(self):
        query = sa.select(sa.func.count()).select_from(
            self.following.select().subquery()
        )
        return db.session.scalar(query)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User {self.researcher_name}>"

    def avatar(self, size):
        digest = md5(self.email.lower().encode("utf-8")).hexdigest()
        return f"https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}"

    def following_pipeline_runs(self):
        """
        Returns a list of (researcher_id, researcher_name, total pipeline runs, names of pipelines that were run)
        for each researcher that self is following, for pipelines run in the last 3 months.
        """
        from dateutil.relativedelta import relativedelta

        three_months_ago = datetime.now(timezone.utc) - relativedelta(months=3)

        # Query to get pipeline runs from followed researchers
        query = (
            sa.select(
                Researcher.id,
                Researcher.researcher_name,
                sa.func.count(PipelineRun.id).label("total_runs"),
                sa.func.array_agg(sa.distinct(PipelineRun.pipeline_name)).label(
                    "pipeline_names"
                ),
            )
            .join(followers, followers.c.followed_id == Researcher.id)
            .join(PipelineRun, PipelineRun.researcher_id == Researcher.id)
            .where(followers.c.follower_id == self.id)
            .where(PipelineRun.timestamp >= three_months_ago)
            .group_by(Researcher.id, Researcher.researcher_name)
            .order_by(sa.desc("total_runs"))
        )

        return db.session.execute(query).all()


@login.user_loader
def load_user(id: int) -> Researcher:
    return db.session.get(Researcher, int(id))
