import jwt
import json
import rq, redis
from dateutil.relativedelta import relativedelta
from time import time
from typing import Optional
from hashlib import md5
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from redis import Redis
from src.app import db

import sqlalchemy as sa
import sqlalchemy.orm as so
from src.app import db, login
from src.app.models.pipeline_run import PipelineRun
from src.app.models.searchable import SearchableMixin

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
    """A researcher user model for the gene annotation system.

    This class represents users of the gene annotation platform with authentication,
    social relationships, and research activity tracking capabilities. It implements
    a follower/following relationship system and tracks user pipeline runs and posts.

    Attributes:
        id (int): Primary key identifier for the researcher
        researcher_name (str): Unique username for the researcher
        email (str): Unique email address for the researcher
        password_hash (str): Securely hashed password (never stored in plaintext)
        about_me (str): Optional biography or profile information
        last_seen (datetime): Timestamp of the user's most recent activity
        posts (relationship): Collection of posts created by this researcher
        runs (relationship): Collection of pipeline runs initiated by this researcher
        following (relationship): Other researchers this user follows
        followers (relationship): Other researchers who follow this user

    Relationships:
        - One-to-many with Post (as author)
        - One-to-many with PipelineRun (as researcher)
        - Many-to-many with Researcher (self-referential for following/followers)
    """

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    researcher_name: so.Mapped[str] = so.mapped_column(
        sa.String(64), index=True, unique=True
    )
    email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True, unique=True)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))

    about_me: so.Mapped[Optional[str]] = so.mapped_column(sa.String(140))
    last_seen: so.Mapped[Optional[datetime]] = so.mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
    last_message_read_time: so.Mapped[Optional[datetime]]
    messages_sent: so.WriteOnlyMapped["Message"] = so.relationship(
        foreign_keys="Message.sender_id", back_populates="author"
    )
    messages_received: so.WriteOnlyMapped["Message"] = so.relationship(
        foreign_keys="Message.recipient_id", back_populates="recipient"
    )
    notifications: so.WriteOnlyMapped["Notification"] = so.relationship(
        back_populates="researcher"
    )
    posts: so.WriteOnlyMapped["Post"] = so.relationship(back_populates="author")
    tasks: so.WriteOnlyMapped["Task"] = so.relationship(back_populates="researcher")

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

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {"reset_password": self.id, "exp": time() + expires_in},
            current_app.config["SECRET_KEY"],
            algorithm="HS256",
        )

    def add_notification(self, name, data):
        """
        Helper method to add researcher's notification to database and ensure
        that if a notification with same name already exists, it is removed first.

        :params name: the name for this notification
        :params data: the notification data
        :returns n: the notification object

        """
        db.session.execute(self.notifications.delete().where(Notification.name == name))
        n = Notification(name=name, payload_json=json.dumps(data), researcher=self)
        db.session.add(n)
        return n

    def launch_task(self, name, description, *args, **kwargs):
        """
        Submits tasks to the RQ queue and adds it to the database. Note that this
        function adds new task object to the database session but it does not issue
        a commit. It is best to operate on the database session in the higher level
        functions, as that allows you to combine several updates made by lower level
        functions in a single transaction.

        Attributes:
            name: the function name
            description: helpful description of the task that can be presented to researchers
            *args and **kwargs: positional and keyword args that can be passed to the task
        """
        rq_job = current_app.task_queue.enqueue(
            f"src.app.tasks.{name}", self.id, *args, **kwargs
        )
        task = Task(
            id=rq_job.get_id(), name=name, description=description, researcher=self
        )
        db.session.add(task)
        return task

    def get_tasks_in_progress(self):
        """
        Get completed tasks
        """
        query = self.tasks.select().where(Task.complete == False)
        return db.session.scalars(query)

    def get_task_in_progress(self, name):
        """
        Get completed tasks by name

        Attributes:
            name: task name
        """
        query = self.tasks.select().where(Task.name == name, Task.complete == False)
        return db.session.scalars(query)

    @staticmethod
    def verify_reset_password_token(token):
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

    def unread_messages_count(self):
        last_read_time = self.last_message_read_time or datetime(1900, 1, 1)
        query = sa.select(Message).where(
            Message.recipient == self, Message.timestamp > last_read_time
        )
        return db.session.scalar(
            sa.select(sa.func.count()).select_from(query.subquery())
        )


class Post(SearchableMixin, db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    language: so.Mapped[Optional[str]] = so.mapped_column(sa.String(5))
    body: so.Mapped[str] = so.mapped_column(sa.String(140))
    timestamp: so.Mapped[datetime] = so.mapped_column(
        index=True, default=lambda: datetime.now(timezone.utc)
    )
    researcher_id: so.Mapped[int] = so.mapped_column(
        sa.ForeignKey(Researcher.id), index=True
    )
    # language: so.Mapped[Optional[str]] = so.mapped_column(sa.String(5))

    author: so.Mapped[Researcher] = so.relationship(back_populates="posts")
    __searchable__ = ["body"]

    def __repr__(self):
        return "<Post {}>".format(self.body)


class Message(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    sender_id: so.Mapped[int] = so.mapped_column(
        sa.ForeignKey(Researcher.id), index=True
    )
    recipient_id: so.Mapped[int] = so.mapped_column(
        sa.ForeignKey(Researcher.id), index=True
    )
    body: so.Mapped[str] = so.mapped_column(sa.String(140))
    timestamp: so.Mapped[datetime] = so.mapped_column(
        index=True, default=lambda: datetime.now(timezone.utc)
    )
    author: so.Mapped[Researcher] = so.relationship(
        foreign_keys="Message.sender_id", back_populates="messages_sent"
    )
    recipient: so.Mapped[Researcher] = so.relationship(
        foreign_keys="Message.recipient_id", back_populates="messages_received"
    )

    def __repr__(self):
        return "<Message {}>".format(self.body)


class Notification(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(128), index=True)
    researcher_id: so.Mapped[int] = so.mapped_column(
        sa.ForeignKey(Researcher.id), index=True
    )
    timestamp: so.Mapped[float] = so.mapped_column(index=True, default=time)
    payload_json: so.Mapped[str] = so.mapped_column(sa.Text)
    researcher: so.Mapped[Researcher] = so.relationship(back_populates="notifications")

    def get_data(self):
        return json.loads(str(self.payload_json))


class Task(db.Model):
    """
    Table representing tasks for a given researcher

    Attributes:
        id: primary key for the task; job identifier generated by redis
        name: the name of this task
        description: a description of this task
        researcher_id: the id of the researcher who started this task
        complete: a boolean that shows task status

    """

    id: so.Mapped[str] = so.mapped_column(sa.String(36), primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(128), index=True)
    description: so.Mapped[Optional[str]] = so.mapped_column(sa.String(128))
    researcher_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(Researcher.id))
    complete: so.Mapped[bool] = so.mapped_column(default=False)

    researcher: so.Mapped[Researcher] = so.relationship(back_populates="tasks")

    def get_rq_job(self):
        """
        Uses the task id to load the job instance from the data that exists
        in Redis about it.
        """
        try:
            rq_job = rq.job.Job.fetch(self.id, connection=current_app.redis)
        except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
            return None
        return rq_job

    def get_progress(self):
        """
        Returns the progress percentage for the task. If the job id does not
        exist in the RQ queue, that means the job already finished and the data
        has expired, and was removed from the queue, so the percentage in this
        case is 100. On the other hand, if the job exists but there is no information
        associated with it, then we assume the job is scheduled to run.
        """
        job = self.get_rq_job()
        return job.meta.get("progress", 0) if job is not None else 100


@login.user_loader
def load_user(id: int) -> Researcher:
    return db.session.get(Researcher, int(id))
