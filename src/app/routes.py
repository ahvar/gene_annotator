from datetime import datetime, UTC
from pathlib import Path
from flask import render_template, flash, redirect, url_for, request
from urllib.parse import urlsplit
from flask_login import current_user, login_user, logout_user, login_required
from app import app, db
from app.forms import GeneAnnotationForm, RegistrationForm, LoginForm, EmptyForm
from src.utils.pipeline_utils import validate_outputdir
from src.app.models.researcher import Researcher
from src.app.models.gene import Gene, GeneAnnotation
from src.app.models.pipeline_run import PipelineRun
from src.app.models.pipeline_run_service import process_pipeline_run
from src.utils.references import excluded_tigrfam_vals
import sqlalchemy as sa


@app.route("/")
@app.route("/index")
@login_required
def index():
    # Get genes page
    genes_page = request.args.get("page", 1, type=int)
    genes_query = sa.select(Gene).order_by(Gene.created_at.desc())
    genes = db.paginate(
        genes_query,
        page=genes_page,
        per_page=app.config["GENES_PER_PAGE"],
        error_out=False,
    )
    
    # Get annotations page
    annotations_page = request.args.get("annotations_page", 1, type=int)
    annotations_query = sa.select(GeneAnnotation).order_by(GeneAnnotation.created_at.desc())
    annotations = db.paginate(
        annotations_query,
        page=annotations_page,
        per_page=app.config["GENES_PER_PAGE"],
        error_out=False,
    )
    return render_template(
        "index.html",
        title="Gene Database",
        genes=genes.items,
        next_url=url_for("index", page=genes.next_num) if genes.has_next else None,
        prev_url=url_for("index", page=genes.prev_num) if genes.has_prev else None,
        annotations=annotations.items,
        annotations_next_url=url_for("index", annotations_page=annotations.next_num) if annotations.has_next else None,
        annotations_prev_url=url_for("index", annotations_page=annotations.prev_num) if annotations.has_prev else None
    )


@app.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(Researcher).where(Researcher.username == form.username.data)
        )
        if user is None or not user.check_password(form.password.data):
            flash("Invalid username or password")
            return redirect(url_for("login"))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get("next")
        if not next_page or urlsplit(next_page).netloc != "":
            next_page = url_for("index")
        # The argument to url_for() is the endpoint name, which is the name of the view function.
        return redirect(url_for(next_page))
    return render_template("login.html", title="Sign In", form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))

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
        user = Researcher(username=form.researcher_name.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Congratulations, you are now a registered researcher!")
        return redirect(url_for("login"))
    return render_template("register.html", title="Register", form=form)


@app.route("/gene_annotation", methods=["GET", "POST"])
def gene_annotation():
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
                gene_description=form.gene_description.data
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
    return render_template(
        "gene_annotation.html", title="Gene Annotation", form=form
    )

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
        runs_query,
        page=page,
        per_page=app.config["RUNS_PER_PAGE"],
        error_out=False
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
            run_id=run_id
        )
             
    page = request.args.get("page", 1, type=int)
    query = (
        sa.select(Gene, GeneAnnotation)
        .join(
            GeneAnnotation,
            sa.and_(
                Gene.gene_stable_id == GeneAnnotation.gene_stable_id,
                Gene.hgnc_id == GeneAnnotation.hgnc_id
            )
        )
        .where(Gene.created_at >= run.timestamp)
        .where(Gene.created_at <= run.loaded_at)
        .where(GeneAnnotation.tigrfam_id.isnot(None))
        .where(~GeneAnnotation.tigrfam_id.in_(excluded_tigrfam_vals))
        .order_by(Gene.gene_stable_id)
    )
    results = db.paginate(
        query,
        page=page,
        per_page=app.config["GENES_PER_PAGE"],
        error_out=False
    )
    
    return render_template(
        "pipeline_results.html",
        run=run,
        results=results.items,
        next_url=url_for("pipeline_run_results", run_id=run_id, page=results.next_num) if results.has_next else None,
        prev_url=url_for("pipeline_run_results", run_id=run_id, page=results.prev_num) if results.has_prev else None
    )
