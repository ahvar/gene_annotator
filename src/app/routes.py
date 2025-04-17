from flask import render_template, flash, redirect, url_for, request
from urllib.parse import urlsplit
from flask_login import current_user, login_user, logout_user, login_required
from app import app, db
from app.forms import GeneAnnotationForm, RegistrationForm, LoginForm
from src.app.models.researcher import User
import sqlalchemy as sa


@app.route("/")
@app.route("/index")
@login_required
def index():
    user = {"username": "Arthur"}
    pandl = [{"name": "Gene Annotator", "researcher": {"username": "John"}}]
    return render_template("index.html", title="Home")


@app.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data)
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


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Congratulations, you are now a registered user!")
        return redirect(url_for("login"))
    return render_template("register.html", title="Register", form=form)


@app.route("/gene_annotation", methods=["GET", "POST"])
def gene_annotation():
    form = GeneAnnotationForm()
    data = None
    if form.validate_on_submit():
        gene_name = form.gene_name.data
        gene_type = form.gene_type.data
        data = get_filtered_genes(gene_name, gene_type)
    return render_template(
        "gene_annotation.html", title="Gene Annotation", form=form, data=data
    )


def get_filtered_genes(gene_name, gene_type):
    if data is None:
        return []
