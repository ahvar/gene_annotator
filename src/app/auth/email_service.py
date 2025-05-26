from threading import Thread
from flask import render_template
from flask import current_app
from flask_mail import Message
from flask_babel import _
from src.app.email_service import send_email


def send_password_reset_email(researcher):

    token = researcher.get_reset_password_token()
    send_email(
        _("[Gene Annotator] Reset Your Password"),
        sender=current_app.config["ADMINS"][0],
        recipients=[researcher.email],
        text_body=render_template(
            "email/reset_password.txt", researcher=researcher, token=token
        ),
        html_body=render_template(
            "email/reset_password.html", researcher=researcher, token=token
        ),
    )
