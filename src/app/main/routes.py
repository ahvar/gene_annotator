import logging
import traceback
import os
from pathlib import Path
from datetime import datetime, timezone
from flask import render_template, flash, redirect, url_for, request, g, current_app
from flask_login import current_user, login_required
from flask_babel import _, get_locale
import sqlalchemy as sa
import pandas as pd
from langdetect import detect, LangDetectException
from src.app import db
from src.app.main.forms import (
    EditProfileForm,
    EmptyForm,
    PostForm,
    GeneAnnotationForm,
    SearchForm,
)
from src.app.models.researcher import Researcher, Post
from src.app.models.gene import Gene, GeneAnnotation
from src.app.models.pipeline_run import PipelineRun, PipelineResult
from src.app.models.pipeline_run_service import (
    load_pipeline_results_into_db,
    process_pipeline_run,
)
from src.app.translate import translate
from src.app.main import bp
from src.utils.pipeline_utils import GeneReader
from src.utils.references import (
    GENE_ANNOTATOR_FRONTEND,
    gene_stable_id_col,
    gene_type_col,
    gene_name_col,
    hgnc_id_col,
    hgnc_name,
    panther_id_col,
    tigrfam_id_col,
)

frontend_logger = logging.getLogger(GENE_ANNOTATOR_FRONTEND)


@bp.route("/find_more_researchers")
@login_required
def find_more_researchers():
    """Page for finding more researchers to follow"""
    page = request.args.get("page", 1, type=int)
    researchers = db.paginate(
        sa.select(Researcher).order_by(Researcher.researcher_name),
        page=page,
        per_page=current_app.config.get("RESEARCHERS_PER_PAGE", 10),
        error_out=False,
    )

    form = EmptyForm()  # For follow/unfollow actions

    return render_template(
        "find_more_researchers.html",
        title=_("Find More Researchers"),
        researchers=researchers.items,
        next_url=(
            url_for("main.find_more_researchers", page=researchers.next_num)
            if researchers.has_next
            else None
        ),
        prev_url=(
            url_for("main.find_more_researchers", page=researchers.prev_num)
            if researchers.has_prev
            else None
        ),
        form=form,
    )


@bp.route("/microblog", methods=["GET", "POST"])
@login_required
def microblog():
    """Research community microblog page where researchers can post and see activity"""
    post_form = PostForm()
    if post_form.validate_on_submit():
        post = Post(body=post_form.post.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash(_("Your post is now live!"))
        return redirect(url_for("main.microblog"))

    # Set up page and pagination for posts
    page = request.args.get("page", 1, type=int)
    posts = db.paginate(
        current_user.following_posts(),
        page=page,
        per_page=current_app.config["POSTS_PER_PAGE"],
        error_out=False,
    )

    posts_next_url = (
        url_for("main.microblog", page=posts.next_num) if posts.has_next else None
    )
    posts_prev_url = (
        url_for("main.microblog", page=posts.prev_num) if posts.has_prev else None
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


@bp.route("/run_pipeline", methods=["POST"])
@login_required
def run_pipeline():
    """Execute pipeline steps and store results in database"""
    try:
        run = process_pipeline_run()

        if run and run.status == _("complete"):
            flash(_("Pipeline run complete! Viewing Results."))
            return redirect(url_for("main.pipeline_run_results", run_id=run.id))
        else:
            flash(_("Pipeline run failed"))
            frontend_logger.error(_("Pipeline run failure."))
            return redirect(url_for("main.index"))

    except Exception as e:
        flash(_("Pipeline error: %(error)s", error=str(e)))
        return redirect(url_for("main.index"))


@bp.route("/add_annotation", methods=["GET", "POST"])
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
        return redirect(url_for("main.index"))
    return render_template(
        "gene_annotation.html", title=_("Gene Annotation"), form=form
    )


@bp.route("/pipeline_run/<int:run_id>")
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
        per_page=current_app.config["GENES_PER_PAGE"],
        error_out=False,
    )

    return render_template(
        "pipeline_results.html",
        run=run,
        results=results.items,
        next_url=(
            url_for("main.pipeline_run_results", run_id=run_id, page=results.next_num)
            if results.has_next
            else None
        ),
        prev_url=(
            url_for("main.pipeline_run_results", run_id=run_id, page=results.prev_num)
            if results.has_prev
            else None
        ),
    )


@bp.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit()
    g.locale = str(get_locale())


@bp.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit()
        g.search_form = SearchForm()
    g.locale = str(get_locale())


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
        per_page=current_app.config[per_page_config],
        error_out=False,
    )


def get_paginated_genes(page):
    """Get paginated genes"""
    return get_pagination(Gene, page)


def get_paginated_annotations(page):
    """Get paginated annotations"""
    return get_pagination(GeneAnnotation, page)


@bp.route("/", methods=["GET", "POST"])
@bp.route("/index", methods=["GET", "POST"])
@login_required
def index():
    """Home page with pipeline controls and datasets"""
    latest_run = get_latest_pipeline_run()
    form = EmptyForm()
    return render_template(
        "index.html",
        title=_("Home"),
        form=form,
        latest_run=latest_run,
    )


@bp.route("/explore/genes")
@login_required
def explore_genes():
    """Display paginated gene dataset for exploration.

    Presents a paginated view of all genes in the database with navigation
    controls. This page allows researchers to browse through the gene dataset,
    providing reference information about genes including their
    stable IDs, types, and HGNC identifiers.

    URL Parameters:
        page (int, optional): The page number to display (defaults to 1)

    Returns:
        Rendered HTML template with:
        - List of genes for the current page
        - Pagination controls
        - Information about gene data structure

    Requires authentication via @login_required decorator.
    """
    # Check if we need to load gene data
    gene_count = db.session.scalar(sa.func.count(Gene.id))
    if gene_count == 0:
        # No genes in database - load initial data
        frontend_logger.info(_("No genes found in database."))

    page = request.args.get("page", 1, type=int)
    genes = get_paginated_genes(page)
    return render_template(
        "explore_genes.html",
        title=_("Explore Genes Dataset"),
        genes=genes.items,
        next_url=(
            url_for("main.explore_genes", page=genes.next_num)
            if genes.has_next
            else None
        ),
        prev_url=(
            url_for("main.explore_genes", page=genes.prev_num)
            if genes.has_prev
            else None
        ),
    )


@bp.route("/explore/annotations")
@login_required
def explore_annotations():
    """Display paginated gene annotations dataset for exploration.

    Presents a paginated view of all gene annotations in the database with
    navigation controls. This page allows researchers to browse additional
    functional annotations for genes from reference databases,
    including Panther, TIGRFam, and Wikigene.

    URL Parameters:
        page (int, optional): The page number to display (defaults to 1)

    Returns:
        Rendered HTML template with:
        - List of gene annotations for the current page
        - Pagination controls
        - Information about annotation data structure

    Requires authentication via @login_required decorator.
    """
    # Check if we need to load annotation data
    annotation_count = db.session.scalar(sa.func.count(GeneAnnotation.id))

    if annotation_count == 0:
        # No annotations in database - load initial data
        frontend_logger.info(_("No annotations found in database"))
    page = request.args.get("page", 1, type=int)
    annotations = get_paginated_annotations(page)
    return render_template(
        "explore_annotations.html",
        title=_("Explore Gene Annotations Dataset"),
        annotations=annotations.items,
        next_url=(
            url_for("main.explore_annotations", page=annotations.next_num)
            if annotations.has_next
            else None
        ),
        prev_url=(
            url_for("main.explore_annotations", page=annotations.prev_num)
            if annotations.has_prev
            else None
        ),
    )


def load_gene_and_annotation_data():
    """Load both gene and annotation data from files into database"""
    # project_root = Path(__file__).resolve().parent.parent.parent.parent

    data_dir = Path(__file__).resolve().parent.parent.parent / "etl" / "data"
    frontend_logger.info(f"Loading data from {data_dir}")
    gene_reader = GeneReader(input_dir=data_dir)
    gene_reader.find_and_load_gene_data()
    gene_reader.remove_duplicates()

    # Load genes
    # Load genes
    for _, row in gene_reader.genes.iterrows():
        # Convert NaN values to None before database insertion
        gene = Gene(
            gene_stable_id=row[gene_stable_id_col],
            gene_type=(
                None if pd.isna(row.get(gene_type_col)) else row.get(gene_type_col)
            ),
            gene_name=(
                None if pd.isna(row.get(gene_name_col)) else row.get(gene_name_col)
            ),
            hgnc_name=None if pd.isna(row.get(hgnc_name)) else row.get(hgnc_name),
            hgnc_id=None if pd.isna(row.get(hgnc_id_col)) else row.get(hgnc_id_col),
            hgnc_id_exists=bool(row.get(hgnc_id_col))
            and not pd.isna(row.get(hgnc_id_col)),
        )
        db.session.add(gene)

    # Load annotations
    for _, row in gene_reader.gene_annotations.iterrows():
        annotation = GeneAnnotation(
            gene_stable_id=row[gene_stable_id_col],
            hgnc_id=None if pd.isna(row.get(hgnc_id_col)) else row.get(hgnc_id_col),
            panther_id=(
                None if pd.isna(row.get(panther_id_col)) else row.get(panther_id_col)
            ),
            tigrfam_id=(
                None if pd.isna(row.get(tigrfam_id_col)) else row.get(tigrfam_id_col)
            ),
            wikigene_name=(
                None if pd.isna(row.get("wikigene_name")) else row.get("wikigene_name")
            ),
            gene_description=(
                None
                if pd.isna(row.get("gene_description"))
                else row.get("gene_description")
            ),
        )
        db.session.add(annotation)

    db.session.commit()
    frontend_logger.info(
        f"Loaded {gene_reader.genes.shape[0]} genes and "
        f"{gene_reader.gene_annotations.shape[0]} annotations"
    )

    return gene_reader.genes.shape[0], gene_reader.gene_annotations.shape[0]


@bp.route("/diagnose")
@login_required
def diagnose():
    """Diagnostic endpoint to troubleshoot data loading issues"""
    results = {
        "environment": {},
        "file_system": {},
        "database": {},
    }

    try:
        # Environment variables
        results["environment"] = {
            "PYTHONPATH": os.environ.get("PYTHONPATH", "not set"),
            "FLASK_APP": os.environ.get("FLASK_APP", "not set"),
            "working_dir": os.getcwd(),
            "FLASK_ENV": os.environ.get("FLASK_ENV", "not set"),
            "DATABASE_URL": os.environ.get("DATABASE_URL", "not set").replace(
                os.environ.get("MYSQL_PASSWORD", ""), "[REDACTED]"
            ),
            "CONTAINER_ENV": "Yes" if os.path.exists("/.dockerenv") else "No",
        }

        # File system checks
        data_path = Path(__file__).resolve().parent.parent.parent / "etl" / "data"
        gene_file = data_path / "genes.csv"
        anno_file = data_path / "gene_annotation.tsv"  # Note: singular, not plural

        results["file_system"] = {
            "data_path_exists": data_path.exists(),
            "data_path_is_dir": data_path.is_dir() if data_path.exists() else False,
            "genes_csv_exists": gene_file.exists(),
            "gene_annotation_tsv_exists": anno_file.exists(),
            "data_dir_contents": (
                str([f.name for f in data_path.glob("*")])
                if data_path.exists()
                else "N/A"
            ),
            "genes_csv_size": gene_file.stat().st_size if gene_file.exists() else 0,
            "annotations_tsv_size": (
                anno_file.stat().st_size if anno_file.exists() else 0
            ),
            "abs_data_path": str(data_path.absolute()),
            "project_root": str(Path(__file__).resolve().parent.parent.parent.parent),
            "data_parent_dir_exists": Path(__file__)
            .resolve()
            .parent.parent.parent.exists(),
            "etl_dir_exists": Path(__file__)
            .resolve()
            .parent.parent.parent.joinpath("etl")
            .exists(),
            "data_path_readable": os.access(str(data_path), os.R_OK),
            "parent_dir_writable": os.access(str(data_path.parent), os.W_OK),
        }

        # Database checks
        results["database"] = {
            "gene_count": db.session.scalar(sa.func.count(Gene.id)),
            "annotation_count": db.session.scalar(sa.func.count(GeneAnnotation.id)),
            "researcher_count": db.session.scalar(sa.func.count(Researcher.id)),
            "post_count": db.session.scalar(sa.func.count(Post.id)),
        }

    except Exception as e:
        results["error"] = str(e)
        results["traceback"] = traceback.format_exc()

    return render_template("diagnose.html", results=results)


@bp.route("/researcher/<researcher_name>")
@login_required
def researcher(researcher_name):
    """Display a researcher's profile page with posts and pipeline runs.

    This route shows detailed information about a specific researcher, including
    their profile information, posts they've written, and pipeline runs they've
    executed. The page includes pagination controls for both posts and runs.
    If the current user is not the profile owner, follow/unfollow controls are
    displayed.

    URL Parameters:
        researcher_name (str): Username of the researcher to display
        page (int, optional): The page number to display for posts and runs (defaults to 1)

    Returns:
        Rendered HTML template with:
        - Researcher profile information (avatar, name, bio, statistics)
        - Paginated list of the researcher's posts
        - Paginated list of the researcher's pipeline runs
        - Follow/unfollow form if viewing another researcher's profile
        - Pagination controls for both posts and runs

    Raises:
        404: If the researcher is not found (handled by db.first_or_404)

    Requires authentication via @login_required decorator.
    """

    researcher = db.first_or_404(
        sa.select(Researcher).where(Researcher.researcher_name == researcher_name)
    )
    page = request.args.get("page", 1, type=int)
    posts_query = researcher.posts.select().order_by(Post.timestamp.desc())
    posts = db.paginate(
        posts_query,
        page=page,
        per_page=current_app.config["POSTS_PER_PAGE"],
        error_out=False,
    )
    posts_next_url = (
        url_for(
            "main.researcher",
            researcher_name=researcher.researcher_name,
            page=posts.next_num,
        )
        if posts.has_next
        else None
    )
    posts_prev_url = (
        url_for(
            "main.researcher",
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
        runs_query,
        page=page,
        per_page=current_app.config["RUNS_PER_PAGE"],
        error_out=False,
    )
    next_url = (
        url_for(
            "main.researcher",
            researcher_name=researcher.researcher_name,
            page=runs.next_num,
        )
        if runs.has_next
        else None
    )
    prev_url = (
        url_for(
            "main.researcher",
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


@bp.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.researcher_name)
    if form.validate_on_submit():
        current_user.researcher_name = form.researcher_name.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash(_("Your changes have been saved"))
        return redirect(url_for("main.edit_profile"))
    elif request.method == "GET":
        form.researcher_name.data = current_user.researcher_name
        form.about_me.data = current_user.about_me
    return render_template("edit_profile.html", title=_("Edit Profile"), form=form)


@bp.route("/follow/<researcher_name>", methods=["POST"])
@login_required
def follow(researcher_name):
    """Follow a researcher.

    Adds the current user to the followers list of the specified researcher.
    Requires authentication and form validation to prevent CSRF attacks.

    Args:
        researcher_name (str): Username of the researcher to follow

    Returns:
        A redirect to either:
        - The researcher's profile page on success
        - The index page if researcher is not found or form validation fails

    Raises:
        No explicit exceptions, but implicit 404 if researcher not found,
        handled by the redirect response
    """
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
            return redirect(url_for("main.index"))
        if researcher == current_user:
            flash(_("You cannot follow yourself!"))
            return redirect(url_for("main.researcher", researcher_name=researcher_name))
        current_user.follow(researcher)
        db.session.commit()
        flash(
            _(
                "You are following %(researcher_name)s!",
                researcher_name=researcher_name,
            )
        )
        return redirect(url_for("main.researcher", researcher_name=researcher_name))
    else:
        return redirect(url_for("main.index"))


@bp.route("/unfollow/<researcher_name>", methods=["POST"])
@login_required
def unfollow(researcher_name):
    """Unfollow a researcher.

    Removes the current user from the followers list of the specified researcher.
    Requires authentication and form validation to prevent CSRF attacks.

    Args:
        researcher_name (str): Username of the researcher to unfollow

    Returns:
        A redirect to either:
        - The researcher's profile page on success
        - The index page if form validation fails

    Raises:
        404: Implicitly if researcher is not found (handled by redirect)
    """
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
            return redirect(url_for("main.index"))
        if researcher == current_user:
            flash(_("You cannot unfollow yourself!"))
            return redirect(url_for("main.researcher", researcher_name=researcher_name))
        current_user.unfollow(researcher)
        db.session.commit()
        flash(
            _(
                "You are not following %(researcher_name)s",
                researcher_name=researcher_name,
            )
        )
        return redirect(url_for("main.researcher", researcher_name=researcher_name))
    else:
        return redirect(url_for("main.index"))


@bp.route("/translate", methods=["POST"])
@login_required
def translate_next():
    """Translate text between languages.

    API endpoint that accepts JSON with source text, source language, and
    destination language. Uses the Azure Translator service to perform translation.

    Request body should be JSON with structure:
    {
        "text": "Text to translate",
        "source_language": "en",
        "dest_language": "es"
    }

    Returns:
        JSON response with the translated text:
        {
            "text": "Translated text here"
        }

    Requires authentication to prevent abuse of translation API quota.
    """
    data = request.get_json()
    return {
        "text": translate(data["text"], data["source_language"], data["dest_language"])
    }


@bp.route("/search")
@login_required
def search():
    if not g.search_form.validate():
        return redirect(url_for("main.index"))
    page = request.args.get("page", 1, type=int)
    posts, total = Post.search(
        g.search_form.q.data, page, current_app.config["POSTS_PER_PAGE"]
    )
    next_url = (
        url_for("main.search", q=g.search_form.q.data, page=page + 1)
        if total > page * current_app.config["POSTS_PER_PAGE"]
        else None
    )
    prev_url = (
        url_for("main.search", q=g.search_form.q.data, page=page - 1)
        if page > 1
        else None
    )
    return render_template(
        "search.html",
        title=_("Search"),
        posts=posts,
        next_url=next_url,
        prev_url=prev_url,
    )
