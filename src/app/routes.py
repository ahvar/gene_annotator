import logging
from datetime import datetime, UTC, timezone
from pathlib import Path
from flask import render_template, flash, redirect, url_for, request, g
from urllib.parse import urlsplit
from flask import g
from flask_login import current_user, login_user, logout_user, login_required
from flask_babel import _, get_locale
from src.app import app, db
from src.app.forms import (
    GeneAnnotationForm,
    RegistrationForm,
    LoginForm,
    EmptyForm,
    EditProfileForm,
    ResetPasswordRequestForm,
    ResetPasswordForm,
    PostForm,
)
from src.app.models.researcher import Researcher, Post
from src.app.models.gene import Gene, GeneAnnotation
from src.app.models.pipeline_run import PipelineRun, PipelineResult
from src.app.models.pipeline_run_service import (
    process_pipeline_run,
    load_pipeline_results_into_db,
)
from src.app.email_service import send_password_reset_email
from src.utils.references import excluded_tigrfam_vals, GENE_ANNOTATOR_FRONTEND
from src.utils.pipeline_utils import validate_outputdir
import sqlalchemy as sa

frontend_logger = logging.getLogger(GENE_ANNOTATOR_FRONTEND)


@app.route("/", methods=["GET", "POST"])
@app.route("/index", methods=["GET", "POST"])
@login_required
def index():
    """Home page with pipeline controls and datasets"""
    post_form = PostForm()
    if post_form.validate_on_submit():
        post = Post(body=post_form.post.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash(_("Your post is now live!"))
        return redirect(url_for("index"))

    # Set up page and pagination for posts
    page = request.args.get("page", 1, type=int)
    posts = db.paginate(
        current_user.following_posts(),
        page=page,
        per_page=app.config["POSTS_PER_PAGE"],
        error_out=False,
    )

    posts_next_url = url_for("index", page=posts.next_num) if posts.has_next else None
    posts_prev_url = url_for("index", page=posts.prev_num) if posts.has_prev else None

    page = request.args.get("page", 1, type=int)

    latest_run = get_latest_pipeline_run()

    genes = get_paginated_genes(page)
    annotations = get_paginated_annotations(page)
    form = EmptyForm()
    return render_template(
        "index.html",
        title="Gene Database",
        form=form,
        post_form=post_form,
        posts=posts,
        genes=genes,
        latest_run=latest_run,
        posts_next_url=posts_next_url,
        posts_prev_url=posts_prev_url,
        annotations=annotations,
        next_url=url_for("index", page=genes.next_num) if genes.has_next else None,
        prev_url=url_for("index", page=genes.prev_num) if genes.has_prev else None,
        annotations_next_url=(
            url_for("index", page=annotations.next_num)
            if annotations.has_next
            else None
        ),
        annotations_prev_url=(
            url_for("index", page=annotations.prev_num)
            if annotations.has_prev
            else None
        ),
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(Researcher).where(
                Researcher.researcher_name == form.researcher_name.data
            )
        )
        if user is None or not user.check_password(form.password.data):
            flash(_("Invalid username or password"))
            return redirect(url_for("login"))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get("next", "index")
        if next_page:
            parsed_url = urlsplit(next_page)
            if parsed_url.netloc != "" or parsed_url.scheme:
                frontend_logger.warning(
                    _(
                        "Blocked redirect to external URL: %(next_page)s",
                        next_page=next_page,
                    )
                )
                next_page = "index"
            else:
                next_page = next_page.lstrip("/") or "index"
        return redirect(url_for(next_page))
    return render_template("login.html", title="Sign In", form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))


def get_pagination(model, page, order_by=None, per_page_config="GENES_PER_PAGE"):
    """Generic pagination helper for database models

    Args:
        model: SQLAlchemy model class (Gene or GeneAnnotation)
        page: Page number to retrieve
        order_by: Optional column to order by (defaults to created_at desc)
        per_page_config: Config key for items per page (defaults to GENES_PER_PAGE)
    """
    query = sa.select(model)
    if order_by is None:
        query = query.order_by(model.created_at.desc())
    else:
        query = query.order_by(order_by)

    return db.paginate(
        query,
        page=page,
        per_page=app.config[per_page_config],
        error_out=False,
    )


def get_paginated_genes(page):
    """Get paginated genes"""
    return get_pagination(Gene, page)


def get_paginated_annotations(page):
    """Get paginated annotations"""
    return get_pagination(GeneAnnotation, page)


@app.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.researcher_name)
    if form.validate_on_submit():
        current_user.researcher_name = form.researcher_name.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash(_("Your changes have been saved"))
        return redirect(url_for("edit_profile"))
    elif request.method == "GET":
        form.researcher_name.data = current_user.researcher_name
        form.about_me.data = current_user.about_me
    return render_template("edit_profile.html", title="Edit Profile", form=form)


@app.route("/explore/genes")
@login_required
def explore_genes():
    page = request.args.get("page", 1, type=int)
    genes = get_paginated_genes(page)
    return render_template(
        "explore_genes.html",
        title="Explore Genes Dataset",
        genes=genes.items,
        next_url=(
            url_for("explore_genes", page=genes.next_num) if genes.has_next else None
        ),
        prev_url=(
            url_for("explore_genes", page=genes.prev_num) if genes.has_prev else None
        ),
    )


@app.route("/explore/annotations")
@login_required
def explore_annotations():
    page = request.args.get("page", 1, type=int)
    annotations = get_paginated_annotations(page)
    return render_template(
        "explore_annotations.html",
        title="Explore Gene Annotations Dataset",
        annotations=annotations.items,
        next_url=(
            url_for("explore_annotations", page=annotations.next_num)
            if annotations.has_next
            else None
        ),
        prev_url=(
            url_for("explore_annotations", page=annotations.prev_num)
            if annotations.has_prev
            else None
        ),
    )


@app.route("/find_more_researchers")
@login_required
def find_more_researchers():
    """Page for finding more researchers to follow"""
    page = request.args.get("page", 1, type=int)
    researchers = db.paginate(
        sa.select(Researcher).order_by(Researcher.researcher_name),
        page=page,
        per_page=app.config.get("RESEARCHERS_PER_PAGE", 10),
        error_out=False,
    )

    form = EmptyForm()  # For follow/unfollow actions

    return render_template(
        "find_more_researchers.html",
        title=_("Find More Researchers"),
        researchers=researchers.items,
        next_url=(
            url_for("find_more_researchers", page=researchers.next_num)
            if researchers.has_next
            else None
        ),
        prev_url=(
            url_for("find_more_researchers", page=researchers.prev_num)
            if researchers.has_prev
            else None
        ),
        form=form,
    )


@app.route("/microblog", methods=["GET", "POST"])
@login_required
def microblog():
    """Research community microblog page where researchers can post and see activity"""
    post_form = PostForm()
    if post_form.validate_on_submit():
        post = Post(body=post_form.post.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash(_("Your post is now live!"))
        return redirect(url_for("microblog"))

    # Set up page and pagination for posts
    page = request.args.get("page", 1, type=int)
    posts = db.paginate(
        current_user.following_posts(),
        page=page,
        per_page=app.config["POSTS_PER_PAGE"],
        error_out=False,
    )

    posts_next_url = (
        url_for("microblog", page=posts.next_num) if posts.has_next else None
    )
    posts_prev_url = (
        url_for("microblog", page=posts.prev_num) if posts.has_prev else None
    )

    # Get list of researchers to suggest following
    researchers_to_follow = (
        db.session.execute(
            sa.select(Researcher)
            .where(Researcher.id != current_user.id)
            .where(~Researcher.followers.of_type(Researcher).contains(current_user))
            .order_by(sa.func.random())
            .limit(5)
        )
        .scalars()
        .all()
    )

    form = EmptyForm()  # For follow/unfollow actions

    return render_template(
        "microblog.html",
        title=_("Research Community"),
        post_form=post_form,
        posts=posts.items,
        posts_next_url=posts_next_url,
        posts_prev_url=posts_prev_url,
        researchers_to_follow=researchers_to_follow,
        form=form,
    )


@app.route("/run_pipeline", methods=["POST"])
@login_required
def run_pipeline():
    """Execute pipeline steps and store results in database"""
    try:
        run = process_pipeline_run()

        if run and run.status == "complete":
            flash(_("Pipeline run complete! Viewing Results."))
            return redirect(url_for("pipeline_run_results", run_id=run.id))
        else:
            flash(_("Pipeline run failed"))
            frontend_logger.error(_("Pipeline run failure."))
            return redirect(url_for("index"))

    except Exception as e:
        flash(_("Pipeline error: %(error)s", error=str(e)))
        return redirect(url_for("index"))


def get_latest_pipeline_run():
    """Get the most recent pipeline run results"""
    db_run = db.session.scalar(
        sa.select(PipelineRun).order_by(PipelineRun.timestamp.desc())
    )

    frontend_logger.info(
        _(
            "Retrieved latest pipeline run from database: %(run_id)s",
            run_id=db_run.id if db_run else "None",
        ),
    )

    project_root = Path(__file__).resolve().parent.parent.parent
    etl_dir = project_root / "src" / "etl"
    output_dirs = [d for d in etl_dir.glob("output_*") if d.is_dir()]
    if not output_dirs:
        frontend_logger.info(
            _("No CLI output directories found in %(dir)s"),
            {"dir": str(etl_dir)},
        )
        return db_run

    latest_dir = sorted(
        output_dirs,
        key=lambda d: datetime.strptime(d.name.replace("output_", ""), "%m%d%yT%H%M%S"),
        reverse=True,
    )[0]
    frontend_logger.info(
        _("Found latest CLI output directory: %(latest_dir)s"),
        {"latest_dir": str(latest_dir)},
    )

    # Parse CLI timestamp and ensure it's timezone-aware
    cli_timestamp = datetime.strptime(
        latest_dir.name.replace("output_", ""), "%m%d%yT%H%M%S"
    ).replace(tzinfo=timezone.utc)

    if not db_run:
        db_timestamp = None
    else:
        if db_run.timestamp.tzinfo is None:
            db_timestamp = db_run.timestamp.replace(tzinfo=timezone.utc)
        else:
            db_timestamp = db_run.timestamp
    if not db_timestamp or cli_timestamp > db_timestamp:
        frontend_logger.info(_("Found more recent CLI results, loading into database"))
        results_file = latest_dir / "results" / "final_results.csv"
        if results_file.exists():
            try:
                load_pipeline_results_into_db(results_file)
                run = PipelineRun(
                    timestamp=cli_timestamp,
                    output_dir=str(latest_dir),
                    pipeline_name=_("Gene Annotation Pipeline"),
                    pipeline_type="CLI",
                    researcher_id=current_user.id,
                    status=_("completed"),
                )
                db.session.add(run)
                db.session.commit()
                frontend_logger.info(_("Successfully loaded CLI results into database"))
                return run
            except Exception as e:
                frontend_logger.error(_("Failed to load CLI results: %(e)s", e=str(e)))
    else:
        frontend_logger.info(_("Using more recent run pulled from database."))
    return db_run


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = Researcher(
            researcher_name=form.researcher_name.data, email=form.email.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(_("Congratulations, you are now a registered researcher!"))
        return redirect(url_for("login"))
    return render_template("register.html", title="Register", form=form)


@app.route("/add_annotation", methods=["GET", "POST"])
def add_annotation():
    """Manual entry form for gene annotations"""
    form = GeneAnnotationForm()
    if form.validate_on_submit():
        annotation = db.session.scalar(
            sa.select(GeneAnnotation)
            .where(GeneAnnotation.gene_stable_id == form.gene_stable_id)
            .where(GeneAnnotation.hgnc_id == form.hgnc_id.data)
        )
        if annotation is None:
            annotation = GeneAnnotation(
                gene_stable_id=form.gene_stable_id.data,
                hgnc_id=form.hgnc_id.data,
                panther_id=form.panther_id.data,
                tigrfam_id=form.tigrfam.data,
                wikigene_name=form.wikigene_name.data,
                gene_description=form.gene_description.data,
            )
            db.session.add(annotation)
            flash(_("New gene annotation added!"))
        else:
            # Only update if values have changed
            changed = False
            if annotation.panther_id != form.panther_id.data:
                annotation.panther_id = form.panther_id.data
                changed = True
            if annotation.tigrfam_id != form.tigrfam_id.data:
                annotation.tigrfam_id = form.tigrfam_id.data
                changed = True
            if annotation.wikigene_name != form.wikigene_name.data:
                annotation.wikigene_name = form.wikigene_name.data
                changed = True
            if annotation.gene_description != form.gene_description.data:
                annotation.gene_description = form.gene_description.data
                changed = True

            if changed:
                flash(_("Gene annotation updated!"))
            else:
                flash(_("No changes to update"))
        db.session.commit()
        return redirect(url_for("index"))
    return render_template("gene_annotation.html", title="Gene Annotation", form=form)


@app.route("/researcher/<researcher_name>")
@login_required
def researcher(researcher_name):
    researcher = db.first_or_404(
        sa.select(Researcher).where(Researcher.researcher_name == researcher_name)
    )
    page = request.args.get("page", 1, type=int)
    posts_query = researcher.posts.select().order_by(Post.timestamp.desc())
    posts = db.paginate(
        posts_query, page=page, per_page=app.config["POSTS_PER_PAGE"], error_out=False
    )
    posts_next_url = (
        url_for(
            "researcher",
            researcher_name=researcher.researcher_name,
            page=posts.next_num,
        )
        if posts.has_next
        else None
    )
    posts_prev_url = (
        url_for(
            "researcher",
            researcher_name=researcher.researcher_name,
            page=posts.prev_num,
        )
        if posts.has_prev
        else None
    )
    runs_query = (
        sa.select(PipelineRun)
        .where(PipelineRun.researcher_id == researcher.id)
        .order_by(PipelineRun.timestamp.desc())
    )
    runs = db.paginate(
        runs_query, page=page, per_page=app.config["RUNS_PER_PAGE"], error_out=False
    )
    next_url = (
        url_for(
            "researcher",
            researcher_name=researcher.researcher_name,
            page=runs.next_num,
        )
        if runs.has_next
        else None
    )
    prev_url = (
        url_for(
            "researcher",
            researcher_name=researcher.researcher_name,
            page=runs.prev_num,
        )
        if runs.has_prev
        else None
    )
    form = EmptyForm()
    return render_template(
        "researcher.html",
        researcher=researcher,
        posts=posts.items,
        posts_next_url=posts_next_url,
        posts_prev_url=posts_prev_url,
        runs=runs.items,
        next_url=next_url,
        prev_url=prev_url,
        form=form,
    )


@app.route("/pipeline_run/<int:run_id>")
@login_required
def pipeline_run_results(run_id):
    run = db.session.get(PipelineRun, run_id)
    if run is None:
        return render_template(
            "no_results.html",
            title=_("No Results Found"),
            message=_(
                "This pipeline run was not found. Would you like to execute a new run?"
            ),
            run_id=run_id,
        )

    page = request.args.get("page", 1, type=int)

    # Query PipelineResult directly
    results = db.paginate(
        sa.select(PipelineResult)
        .where(PipelineResult.run_id == run_id)
        .order_by(PipelineResult.gene_stable_id),
        page=page,
        per_page=app.config["GENES_PER_PAGE"],
        error_out=False,
    )

    return render_template(
        "pipeline_results.html",
        run=run,
        results=results.items,
        next_url=(
            url_for("pipeline_run_results", run_id=run_id, page=results.next_num)
            if results.has_next
            else None
        ),
        prev_url=(
            url_for("pipeline_run_results", run_id=run_id, page=results.prev_num)
            if results.has_prev
            else None
        ),
    )


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit()
    g.locale = str(get_locale())


@app.route("/follow/<researcher_name>", methods=["POST"])
@login_required
def follow(researcher_name):
    form = EmptyForm()
    if form.validate_on_submit():
        researcher = db.session.scalar(
            sa.select(Researcher).where(Researcher.researcher_name == researcher_name)
        )
        if researcher is None:
            flash(
                _(
                    "Researcher %{researcher_name}s not found.",
                    researcher_name=researcher_name,
                )
            )
            return redirect(url_for("index"))
        if researcher == current_user:
            flash(_("You cannot follow yourself!"))
            return redirect(url_for("researcher", researcher_name=researcher_name))
        current_user.follow(researcher_name)
        db.session.commit()
        flash(
            _(
                "You are following %(researcher_name)s!",
                researcher_name=researcher_name,
            )
        )
        return redirect(url_for("researcher", researcher_name=researcher_name))
    else:
        return redirect(url_for("index"))


@app.route("/unfollow/<researcher_name>", methods=["POST"])
@login_required
def unfollow(researcher_name):
    form = EmptyForm()
    if form.validate_on_submit():
        researcher = db.session.scalar(
            sa.select(Researcher).where(Researcher.researcher_name == researcher_name)
        )
        if researcher is None:
            flash(
                _(
                    "Researcher %(researcher_name)s is not found.",
                    researcher_name=researcher_name,
                )
            )
            return redirect(url_for("index"))
        if researcher == current_user:
            flash(_("You cannot unfollow yourself!"))
            return redirect(url_for("researcher", researcher_name=researcher_name))
        current_user.unfollow(researcher)
        db.session.commit()
        flash(
            _(
                "You are not following %(researcher_name)s",
                researcher_name=researcher_name,
            )
        )
        return redirect(url_for("researcher", researcher_name=researcher_name))
    else:
        return redirect(url_for("index"))


@app.route("/reset_password_request", methods=["GET", "POST"])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        researcher = db.session.scalar(
            sa.select(Researcher).where(Researcher.email == form.email.data)
        )
        if researcher:
            send_password_reset_email(researcher)
        flash(_("Check your email for the instructions to reset your password"))
        return redirect(url_for("login"))
    return render_template(
        "reset_password_request.html", title="Reset Password", form=form
    )


@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    researcher = Researcher.verify_reset_password(token)
    if not researcher:
        return redirect(url_for("index"))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        researcher.set_password(form.password.data)
        db.session.commit()
        flash(_("Your password has been reset"))
        return redirect(url_for("login"))
    return render_template("reset_password.html", form=form)
