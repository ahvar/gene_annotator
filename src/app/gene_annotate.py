import sqlalchemy as sa
import sqlalchemy.orm as so
from app import app, db
from src.app.models.researcher import Researcher
from src.app.models.gene import Gene, GeneAnnotation


@app.shell_context_processor
def make_shell_context():
    return {"sa": sa, "so": so, "db": db, "Researcher": Researcher, "Gene": Gene, "Gene_Annotation": GeneAnnotation}
