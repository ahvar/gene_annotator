"""
NOTE:
    -------------------
    Decorator patterns:
    -------------------
    A common pattern with decorators is to use them to register functions as callbacks for certain
    events.

    -------------------
    Templates in Flask:
    -------------------
    Templates help achieve a separation between presentation and business logic. In Flask, templates
    are written as separate files, stored in a templates folder that is inside the application package.
    The render_template() function invokes the Jinja template engine that comes bundled with the Flask framework.
"""

from flask import render_template, flash, redirect, url_for, request
from urllib.parse import urlsplit
from flask_login import current_user, login_user, logout_user, login_required
from app import app
from app.forms import GeneAnnotationForm, RegistrationForm


@app.route("/")
@app.route("/index")
@login_required
def index():
    user = {"username": "Arthur"}
    pandl = [{"name": "Gene Annotator", "researcher": {"username": "John"}}]
    return render_template("index.html", title="Home")


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    NOTE:
    ----------
    GET method
    ----------
    When the browser sends the GET request to receive the web page with the form, this method
    is going to return False, so in that case the function skips the if statement and goes
    directly to render the template in the last line of the function.

    ------------
    POST method
    ------------
    When the browser sends the POST request as a result of the user pressing the submit button,
    form.validate_on_submit() is going to gather all the data, run all the validators attached to fields,
    and if everything is all right it will return True

    -----------------
    Logging users in
    -----------------
    The current_user variable comes from the Flask-Login, and can be used at any time during the handling
    of a request to obtain the user object that represents the client of that request.

    -------------------
    Redirecting
    -------------------
    If the user is not logged in and navigates to /index, @login_required will redirect to /login
    but will add a query string argument to build complete redirect URL: /login?next=/next
    This allows the application to redirect back to the original URL, attempted before login.
    An attacker could insert a URL to a malicious site in the next argument, so the app only redirects
    when the URL is relative: urlsplit() and check if netloc component is set or not

    """
    pandl_form = ProfitAndLossForm()
    trade_form = TradeForm()
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
