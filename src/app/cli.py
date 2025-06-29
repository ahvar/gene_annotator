import os
import click
import logging
import json
import random
import sqlalchemy as sa
from datetime import timedelta, timezone
from flask import Blueprint
from pathlib import Path
from datetime import datetime
from src.utils.references import __Application__, __version__, GENE_ANNOTATOR_FRONTEND
from src.utils.logging_utils import LogFileCreationError, LoggingUtils
from src.utils.pipeline_utils import set_error_and_exit


bp = Blueprint("cli", __name__, cli_group=None)


@bp.cli.group()
def translate():
    """Translation and localization commands"""
    pass


@translate.command()
def update():
    """Update all languages"""
    if os.system("pybabel extract -F ./src/babel.cfg -k _l -o messages.pot ."):
        raise RuntimeError("extract command failed")
    if os.system("pybabel update -i messages.pot -d ./src/app/translations"):
        raise RuntimeError("update command failed")
    os.remove("messages.pot")


@translate.command()
def compile():
    """Compile all languages"""
    if os.system("pybabel compile -d ./src/app/translations"):
        raise RuntimeError("compile command failed")


@translate.command()
@click.argument("lang")
def init(lang):
    """Initialize a new language"""
    if os.system("pybabel extract -F ./src/babel.cfg -k _l -o messages.pot ."):
        raise RuntimeError("extract command failed")
    if os.system("pybabel init -i messages.pot -d ./src/app/translations -l " + lang):
        raise RuntimeError("init command failed")
    os.remove("messages.pot")


def _make_frontend_logfile():
    """
    Create a log file path for the Gene Annotator frontend application.

    Creates a hierarchical directory structure with the following pattern:
    /base_dir/GENE_ANNOTATOR/version/timestamp/GENE_ANNOTATOR_version_frontend.log

    The base directory is:
    - /opt/eon/log if it exists and is writable
    - A temporary directory (from TEMP env var or /tmp) as fallback

    The timestamp format is YYYYMMDDHHMMSS for unique log directories.

    Returns:
        Path: Full path to the log file

    Note:
        Creates all necessary directories with parents=True
    """
    log_base = Path("/opt/eon/log")
    if not log_base.exists():
        try:
            log_base.mkdir(exist_ok=True, parents=True)
            print(f"Created log directory: {log_base}")
        except (PermissionError, OSError):
            log_base = Path(os.environ.get("TEMP", "/tmp"))
            print(f"Cannot create /opt/eon/log - using {log_base} instead")
    elif not os.access(str(log_base), os.W_OK):
        # Directory exists but isn't writable
        log_base = Path(os.environ.get("TEMP", "/tmp"))
        print(f"/opt/eon/log exists but is not writable - using {log_base} instead")
    # Create timestamped directory
    logfile_parent = (
        log_base
        / __Application__
        / __version__.replace(".", "_")
        / datetime.now().strftime("%Y%m%d%H%M%S")
    )
    logfile_parent.mkdir(exist_ok=True, parents=True)
    return logfile_parent / f"{GENE_ANNOTATOR_FRONTEND}.log"


def init_frontend_logger(log_level):
    """
    Initialize a logger for the Gene Annotator frontend application.

    Creates a logger with both file and console output. The log file is stored in
    a timestamped directory to prevent overwrites.

    Args:
        log_level: Logging level (e.g., logging.INFO, logging.DEBUG)

    Returns:
        LoggingUtils: Configured logger object with file and console handlers,
                     or console-only logger if file creation fails

    Note:
        Attempts to create log directories if they don't exist.
        Falls back to a temporary directory if permission denied or creation fails.
        Will not fail even if logging setup encounters errors - provides a console
        logger as fallback.
    """
    try:
        log_file = _make_frontend_logfile()
        logging_utils = LoggingUtils(
            application_name=GENE_ANNOTATOR_FRONTEND,
            log_file=log_file,
            file_level=log_level,
            console_level=logging.ERROR,
        )
        return logging_utils

    except Exception as e:
        # Print the error but don't exit the application
        print(f"Warning: Unable to initialize frontend logger: {str(e)}")
        # Return a basic console-only logger as fallback
        return LoggingUtils(
            application_name=GENE_ANNOTATOR_FRONTEND,
            console_level=logging.ERROR,
        )


@bp.cli.command("load-data")
def load_gene_data():
    from src.app.main.routes import load_gene_and_annotation_data

    result = load_gene_and_annotation_data()
    if result:
        genes_count, annotations_count = result
        print(
            "Successfully loaded {} genes and {} annotations".format(
                genes_count, annotations_count
            )
        )
    else:
        print("Failed to load data")


@bp.cli.command("load-test-users")
def load_test_users():
    """Load test users from test_users.json into the database"""
    from src.app.models.researcher import Researcher, Post
    from src.app import db

    # Get the path to test_users.json
    # project_root = Path(__file__).resolve().parent.parent.parent.parent
    test_users_file = Path("/opt/test_users.json")

    if not test_users_file.exists():
        print(f"Test users file not found: {test_users_file}")
        return

    try:
        with open(test_users_file) as f:
            test_users = json.load(f)

        # First create all users (needed before establishing relationships)
        user_map = {}  # Map usernames to Researcher objects

        # Check if users already exist
        existing_users = db.session.scalar(sa.func.count(Researcher.id))
        if existing_users > 0:
            print(
                f"Database already contains {existing_users} users. Skipping test user creation."
            )
            return

        print(f"Loading {len(test_users)} test users...")

        # Create users first
        for user_data in test_users:
            user = Researcher(
                researcher_name=user_data["researcher_name"],
                email=user_data["email"],
                about_me=user_data.get("about_me", ""),
            )
            user.set_password(user_data["password"])
            db.session.add(user)
            user_map[user_data["researcher_name"]] = user

        # Commit to generate IDs before establishing relationships
        db.session.commit()

        # Create posts and following relationships
        now = datetime.now(timezone.utc)

        for user_data in test_users:
            user = user_map[user_data["researcher_name"]]

            # Add posts
            if "posts" in user_data:
                for i, post_text in enumerate(user_data["posts"]):
                    # Create posts with staggered timestamps for a realistic timeline
                    post_time = now - timedelta(
                        days=random.randint(0, 10),
                        hours=random.randint(0, 23),
                        minutes=random.randint(0, 59),
                    )
                    post = Post(body=post_text, author=user, timestamp=post_time)
                    db.session.add(post)

            # Add following relationships
            if "following" in user_data:
                for followed_name in user_data["following"]:
                    if followed_name in user_map:
                        user.follow(user_map[followed_name])

        db.session.commit()
        print(f"Successfully loaded {len(user_map)} users with posts and relationships")

    except Exception as e:
        db.session.rollback()
        print(f"Error loading test users: {str(e)}")


@bp.cli.command("create-search-indices")
def create_search_indices():
    """Create Elasticsearch indices and index existing data"""
    from src.app.models.researcher import Post
    from src.app import db
    from flask import current_app
    import sqlalchemy as sa

    if not current_app.elasticsearch:
        print("Elasticsearch not configured, skipping index creation")
        return

    print("Creating search indices and indexing existing posts...")

    # Get all posts from the database
    posts = db.session.scalars(sa.select(Post)).all()

    # Index each post
    for post in posts:
        try:
            post.add_to_index()
        except Exception as e:
            print(f"Error indexing post {post.id}: {str(e)}")

    print(f"Successfully indexed {len(posts)} posts")
