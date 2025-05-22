import os
import logging
from logging.handlers import SMTPHandler
from flask import Flask
from flask import request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_moment import Moment
from flask_babel import Babel

from src.config import Config


def get_locale():
    return request.accept_languages.best_match(app.config["LANGUAGES"])


app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login = LoginManager(app)
login.login_view = "login"
mail = Mail(app)
moment = Moment(app)
babel = Babel(app, locale_selector=get_locale)
from src.app.errors import bp as errors_bp
from src.app.auth import bp as auth_bp
from src.app.main import bp as main_bp

app.register_blueprint(errors_bp)
app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(main_bp)
from src.utils.pipeline_utils import init_frontend_logger


app_logger = None

if not app.debug:
    if app.config["MAIL_SERVER"]:
        auth = None
        if app.config["MAIL_USERNAME"] or app.config["MAIL_PASSWORD"]:
            auth = (app.config["MAIL_USERNAME"], app.config["MAIL_PASSWORD"])
        secure = None
        if app.config["MAIL_USE_TLS"]:
            secure()
        mail_handler = SMTPHandler(
            mailhost=(app.config["MAIL_SERVER"], app.config["MAIL_PORT"]),
            fromaddr="no-reply@" + app.config["MAIL_SERVER"],
            toaddrs=app.config["ADMINS"],
            subject="Gene Annotator Failure",
            credentials=auth,
            secure=secure,
        )
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)
    app_logger = init_frontend_logger(logging.INFO)

from src.app import routes
from src.app.models import researcher, gene, pipeline_run_service, pipeline_run
