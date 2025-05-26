from flask import Blueprint

bp = Blueprint("errors", __name__)

from src.app.errors import handlers
