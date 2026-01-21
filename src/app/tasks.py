"""
The task function that exports blog posts needs access to the database and email helper functions.
Because this will run in a separate process, we initialize Flask-SQLAlchemy and Flask-Mail,
which in turn need a Flask instance from which to get their configuration.

The application is created in this module because this is the only module the RQ worker is going
to import; separate from the app initialized in gene_annotator_flask_shell_ctx
"""

import time
import json
import sys
import sqlalchemy as sa
from rq import get_current_job
from flask import render_template
from src.app import create_app, db
from src.app.models.researcher import Researcher, Task, Post
from src.app.email_service import send_email

app = create_app()
app.app_context().push()


def _set_task_progress(progress):
    job = get_current_job()
    if job:
        job.meta["progress"] = progress
        job.save_meta()
        task = db.session.get(Task, job.get_id())
        task.researcher.add_notification(
            "task_progress", {"task_id": job.get_id(), "progress": progress}
        )
        if progress >= 100:
            task.complete = True
        db.session.commit()


def export_posts(researcher_id):
    """
    This function to run in a separate process controlled by RQ
    """

    try:
        researcher = db.session.get(Researcher, researcher_id)
        _set_task_progress(0)
        data = []
        i = 0
        total_posts = db.session.scalar(
            sa.select(sa.func.count()).select_from(researcher.posts.select().subquery())
        )
        for post in db.session.scalars(
            researcher.posts.select().order_by(Post.timestamp.asc())
        ):
            data.append(
                {"body": post.body, "timestamp": post.timestamp.isoformat() + "Z"}
            )
            time.sleep(5)
            i += 1
            _set_task_progress(100 * i)
            send_email(
                "[Gene Annotator] Your blog posts",
                sender=app.config["ADMINS"][0],
                recipients=[researcher.email],
                text_body=render_template(
                    "email/export_posts.txt", researcher=researcher
                ),
                html_body=render_template(
                    "email/export_posts.html", researcher=researcher
                ),
                attachments=[
                    (
                        "posts.json",
                        "application/json",
                        json.dumps({"posts": data}, indent=4),
                    )
                ],
                sync=True,
            )
    except Exception:
        _set_task_progress(100)
        app.logger.error("Unhandled exception", exc_info=sys.exc_info())
    finally:
        _set_task_progress(100)
