import os
from pathlib import Path
from dotenv import load_dotenv

basedir = Path(__file__).resolve().parent.parent
envfile = basedir / ".env"
load_dotenv(str(envfile))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "you-will-never-guess"
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "sqlite:///" + str(
        basedir / "src" / "app" / "app.db"
    )
    ELASTICSEARCH_URL = os.environ.get("ELASTICSEARCH_URL")
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT") or 25)
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS") is not None
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MS_TRANSLATOR_KEY = os.environ.get("MS_TRANSLATOR_KEY")
    ADMINS = ["arthurvargasdev@gmail.com"]
    RUNS_PER_PAGE = 10
    GENES_PER_PAGE = 50
    POSTS_PER_PAGE = 10
    LANGUAGES = ["en", "es"]
