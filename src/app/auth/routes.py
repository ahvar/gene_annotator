import logging
from flask import render_template, redirect, url_for, flash, request
from urllib.parse import urlsplit
from flask_login import login_user, logout_user, current_user
from flask_babel import _
import sqlalchemy as sa
from src.app import db
from src.app.auth import bp
from src.app.auth.forms import (
    LoginForm,
    RegistrationForm,
    ResetPasswordForm,
    ResetPasswordRequestForm,
)
from src.app.models.researcher import Researcher
from src.app.auth.email_service import send_password_reset_email
from src.utils.references import GENE_ANNOTATOR_FRONTEND

frontend_logger = logging.getLogger(GENE_ANNOTATOR_FRONTEND)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(Researcher).where(
                Researcher.researcher_name == form.researcher_name.data
            )
        )
        if user is None or not user.check_password(form.password.data):
            flash(_("Invalid username or password"))
            return redirect(url_for("auth.login"))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get("next", "main.index")
        if next_page:
            parsed_url = urlsplit(next_page)
            if parsed_url.netloc != "" or parsed_url.scheme:
                frontend_logger.warning(
                    _(
                        "Blocked redirect to external URL: %(next_page)s",
                        next_page=next_page,
                    )
                )
                next_page = "main.index"
            else:
                next_page = next_page.lstrip("/") or "main.index"
        return redirect(url_for(next_page))
    return render_template("auth/login.html", title="Sign In", form=form)


@bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("main.index"))


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = Researcher(
            researcher_name=form.researcher_name.data, email=form.email.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(_("Congratulations, you are now a registered researcher!"))
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html", title=_("Register"), form=form)


@bp.route("/reset_password_request", methods=["GET", "POST"])
def reset_password_request():
    """Request a password reset.

    Displays a form to enter email address for password reset.
    Sends a password reset email with a time-limited token if the email
    is associated with a researcher account.

    For security reasons, shows the same success message whether the
    email exists or not to prevent user enumeration.

    Returns:
        GET: Rendered password reset request form
        POST: Redirect to login page after form submission
    """
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        researcher = db.session.scalar(
            sa.select(Researcher).where(Researcher.email == form.email.data)
        )
        if researcher:
            send_password_reset_email(researcher)
        flash(_("Check your email for the instructions to reset your password"))
        return redirect(url_for("auth.login"))
    return render_template(
        "auth/reset_password_request.html", title=_("Reset Password"), form=form
    )


@bp.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """Reset password using a valid token.

    Validates the password reset token and allows setting a new password
    if the token is valid and not expired.

    Args:
        token (str): Password reset token from the email link

    Returns:
        GET: Rendered password reset form if token is valid
        POST: Redirect to login page after successful password change
        If token is invalid: Redirect to index page
    """
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    researcher = Researcher.verify_reset_password_token(token)
    if not researcher:
        return redirect(url_for("main.index"))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        researcher.set_password(form.password.data)
        db.session.commit()
        flash(_("Your password has been reset"))
        return redirect(url_for("auth.login"))
    return render_template("auth/reset_password.html", form=form)
