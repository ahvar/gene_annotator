import jwt
from dateutil.relativedelta import relativedelta
from time import time
from typing import Optional
from hashlib import md5
from flask import current_app
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
    posts: so.WriteOnlyMapped["Post"] = so.relationship(back_populates="author")

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

    def get_reset_password(self, expires_in=600):
        return jwt.encode(
            {"reset_password": self.id, "exp": time() + expires_in},
            current_app.config["SECRET_KEY"],
            algorithm="HS256",
        )

    @staticmethod
    def verify_reset_password(token):
        try:
            id = jwt.decode(
                token, current_app.config["SECRET_KEY"], algorithms=["HS256"]
            )["reset_password"]
        except:
            return
        return db.session.get(Researcher, id)

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
        three_months_ago = datetime.now(timezone.utc) - relativedelta(months=3)
        base_query = (
            sa.select(
                Researcher.id,
                Researcher.researcher_name,
                sa.func.count(PipelineRun.id).label("total_runs"),
            )
            .join(followers, followers.c.follower_id == Researcher.id)
            .join(PipelineRun, PipelineRun.researcher_id == Researcher.id)
            .where(followers.c.follower_id == self.id)
            .where(PipelineRun.timestamp >= three_months_ago)
            .group_by(Researcher.id, Researcher.researcher_name)
            .order_by(sa.desc("total_runs"))
        )

        results = []
        for researcher_id, researcher_name, total_runs in db.session.execute(
            base_query
        ).all():
            pipeline_names_query = (
                sa.select(sa.func.group_concat(sa.distinct(PipelineRun.pipeline_name)))
                .where(PipelineRun.researcher_id == researcher_id)
                .where(PipelineRun.timestamp >= three_months_ago)
            )
            pipeline_names = db.session.scalar(pipeline_names_query)
            pipeline_names = pipeline_names.split(",") if pipeline_names else []
            results.append((researcher_id, researcher_name, total_runs, pipeline_names))
        return results

    def following_posts(self):
        Author = so.aliased(Researcher)
        Follower = so.aliased(Researcher)
        return (
            sa.select(Post)
            .join(Post.author.of_type(Author))
            .join(Author.followers.of_type(Follower), isouter=True)
            .where(
                sa.or_(
                    Follower.id == self.id,
                    Author.id == self.id,
                )
            )
            .group_by(Post)
            .order_by(Post.timestamp.desc())
        )


class Post(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    language: so.Mapped[Optional[str]] = so.mapped_column(sa.String(5))
    body: so.Mapped[str] = so.mapped_column(sa.String(140))
    timestamp: so.Mapped[datetime] = so.mapped_column(
        index=True, default=lambda: datetime.now(timezone.utc)
    )
    researcher_id: so.Mapped[int] = so.mapped_column(
        sa.ForeignKey(Researcher.id), index=True
    )
    language: so.Mapped[Optional[str]] = so.mapped_column(sa.String(5))

    author: so.Mapped[Researcher] = so.relationship(back_populates="posts")

    def __repr__(self):
        return "<Post {}>".format(self.body)


@login.user_loader
def load_user(id: int) -> Researcher:
    return db.session.get(Researcher, int(id))
