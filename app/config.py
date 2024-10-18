"""
NOTE:
    ------------------------
    Separation of concerns:
    ------------------------
    Author of Mega Flask Tutorial recommends storing configuration variables in
    a Python class. 
    
    ----------------------------
    Cross-Site Request Forgery:
    ----------------------------
    The Flask-WTF extension uses SECRET_KEY variable to protect web forms against a nasty attack called
    Cross-Site Request Forgery ("seasurf"). The value of the secret key is set as an expression with two
    terms, joined by the or operator. The first term looks for the value of an environment variable, also
    called SECRET_KEY. The second term, is just a hardcoded string.
"""

import os
from pathlib import Path

basedir = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "you-will-never-guess"
