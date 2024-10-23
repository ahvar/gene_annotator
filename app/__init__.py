"""
--------------------------
Defining a starting point:
-------------------------- 
The __name__ variable is a Python predefined variable, which is set to the name of the module
in which it is used. It is a starting point for Flask to know where to look for templates, static
files, and so on. 

-----------------------------------------
The "app" package vs. the "app" variable:
-----------------------------------------
The app package is defined by the app directory and the __init__.py file, and
is used to import the app variable. The app variable is an instance of the Flask class.

------------------
The bottom import:
------------------
The routes module is imported at the bottom and not at the top of the script as it is always done.
The bottom import is a workaround to circular imports, a common problem in Flask applications.

--------------
Configurations:
--------------
The pattern used for importing configurations is similar to the Flask class. The module is lowercase
and the imported class uppercase. 

-----------------------------
Database and migration engine:
-----------------------------
There is a database object and a database migration engine instance. Alembic is the migration
framework used by Flask-Migrate
"""

from flask import Flask
from app.config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login = LoginManager(app)
login.login_view = "login"
from app import routes, models
from app.models import user
