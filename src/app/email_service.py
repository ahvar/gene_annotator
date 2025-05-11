from threading import Thread

# from flask import render_template
from flask_mail import Message
from flask_babel import _
from src.app import app, mail


def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)


def send_email(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    Thread(target=send_async_email, args=(app, msg)).start()


def send_password_reset_email(researcher):
    from flask import render_template

    token = researcher.get_reset_password_token()
    send_email(
        _("[Gene Annotator] Reset Your Password"),
        sender=app.config["ADMINS"][0],
        recipients=[researcher.email],
        text_body=render_template(
            "email/reset_password.txt", researcher=researcher, token=token
        ),
        html_body=render_template(
            "email/reset_password.html", researcher=researcher, token=token
        ),
    )
