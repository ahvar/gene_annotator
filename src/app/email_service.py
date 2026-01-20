from threading import Thread
from flask import current_app
from flask_mail import Message
from src.app import mail


def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)


def send_email(
    subject, sender, recipients, text_body, html_body, attachments=None, sync=False
):
    """
    When sending an email from a background task, like an export service, which is already
    asynchronous, we'll send them in the foreground. The attach method of Message accepts
    three arguments that define an attachment: filename, media type, actual file data. The
    filename is just the name the recipient will see, it does not need to be a real file.
    """
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    if attachments:
        for attachment in attachments:
            msg.attach(*attachment)
    if sync:
        mail.send(msg)
    else:
        Thread(
            target=send_async_email, args=(current_app._get_current_object(), msg)
        ).start()
