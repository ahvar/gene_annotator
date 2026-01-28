from flask import Blueprint

bp = Blueprint("api", __name__)

from src.app.api import researchers, errors, tokens
