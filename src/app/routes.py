import logging
from datetime import datetime, UTC, timezone
from pathlib import Path
from flask import render_template, flash, redirect, url_for, request
from urllib.parse import urlsplit
from flask_login import current_user, login_user, logout_user, login_required
from src.app import app, db
from src.app.forms import (
    GeneAnnotationForm,
    RegistrationForm,
    LoginForm,
    EmptyForm,
    EditProfileForm,
)
from src.app.models.researcher import Researcher
from src.app.models.gene import Gene, GeneAnnotation
from src.app.models.pipeline_run import PipelineRun
from src.app.models.pipeline_run_service import process_pipeline_run
from src.utils.references import excluded_tigrfam_vals, GENE_ANNOTATOR_FRONTEND
from src.utils.pipeline_utils import validate_outputdir
import sqlalchemy as sa

frontend_logger = logging.getLogger(GENE_ANNOTATOR_FRONTEND)


@app.route("/", methods=["GET", "POST"])
@app.route("/index", methods=["GET", "POST"])
@login_required
def index():
    """Home page with pipeline controls and datasets"""
    page = request.args.get("page", 1, type=int)

    genes = get_paginated_genes(page)
    annotations = get_paginated_annotations(page)

    return render_template(
        "index.html",
        title="Gene Database",
        genes=genes,
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
            flash("Invalid username or password")
            return redirect(url_for("login"))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get("next")
        if next_page:
            parsed_url = urlsplit(next_page)
            if parsed_url.netloc or parsed_url.scheme:
                # URL contains domain or protocol - potential security risk
                frontend_logger.warning(
                    f"Blocked redirect to external URL: {next_page}"
                )
                next_page = "index"
            elif not next_page.startswith("/"):
                next_page = f"/{next_page}"
        else:
            next_page = "index"

        # if not next_page or urlsplit(next_page).netloc != "":
        #    next_page = "index"
        # The argument to url_for() is the endpoint name, which is the name of the view function.
        return redirect(url_for(next_page.lstrip("/")))
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


# Replace existing functions with calls to generic helper
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
        flash("Your changes have been saved")
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


@app.route("/run_pipeline", methods=["POST"])
@login_required
def run_pipeline():
    """Execute pipeline steps and store results in database"""
    try:
        # Create timestamped output directory
        timestamp = datetime.now(UTC).strftime("%m%d%yT%H%M%S")
        output_dir = Path(f"output_{timestamp}")
        output_dir = validate_outputdir(None, output_dir)

        # Process pipeline and load results to DB
        run = process_pipeline_run(output_dir)

        flash("Pipeline run complete! Viewing Results.")
        return redirect(url_for("pipeline_run_results", run_id=run.id))

    except Exception as e:
        flash(f"Pipeline error: {str(e)}", "error")
        return redirect(url_for("index"))


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
        flash("Congratulations, you are now a registered researcher!")
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
            flash("New gene annotation added!")
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
                flash("Gene annotation updated!")
            else:
                flash("No changes to update")
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
            title="No Results Found",
            message="This pipeline run was not found. Would you like to execute a new run?",
            run_id=run_id,
        )

    page = request.args.get("page", 1, type=int)
    query = (
        sa.select(Gene, GeneAnnotation)
        .join(
            GeneAnnotation,
            sa.and_(
                Gene.gene_stable_id == GeneAnnotation.gene_stable_id,
                Gene.hgnc_id == GeneAnnotation.hgnc_id,
            ),
        )
        .where(Gene.created_at >= run.timestamp)
        .where(Gene.created_at <= run.loaded_at)
        .where(GeneAnnotation.tigrfam_id.isnot(None))
        .where(~GeneAnnotation.tigrfam_id.in_(excluded_tigrfam_vals))
        .order_by(Gene.gene_stable_id)
    )
    results = db.paginate(
        query, page=page, per_page=app.config["GENES_PER_PAGE"], error_out=False
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


@app.route("/follow/<researcher_name>", methods=["POST"])
@login_required
def follow(researcher_name):
    form = EmptyForm()
    if form.validate_on_submit():
        researcher = db.session.scalar(
            sa.select(Researcher).where(Researcher.researcher_name == researcher_name)
        )
        if researcher is None:
            flash(f"Researcher {researcher_name} not found.")
            return redirect(url_for("index"))
        if researcher == current_user:
            flash("You cannot follow yourself!")
            return redirect(url_for("researcher", researcher_name=researcher_name))
        current_user.follow(researcher_name)
        db.session.commit()
        flash(f"You are following {researcher_name}!")
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
            flash(f"Researcher {researcher_name} is not found.")
            return redirect(url_for("index"))
        if researcher == current_user:
            flash("You cannot unfollow yourself!")
            return redirect(url_for("researcher", researcher_name=researcher_name))
        current_user.unfollow(researcher)
        db.session.commit()
        flash(f"You are not following {researcher_name}")
        return redirect(url_for("researcher", researcher_name=researcher_name))
    else:
        return redirect(url_for("index"))
