import sqlalchemy as sa
import sqlalchemy.orm as so
from src.app import create_app, db
from src.app.models.researcher import Researcher, Post, Message, Notification
from src.app.models.gene import Gene, GeneAnnotation
from src.app.models.pipeline_run import PipelineRun, PipelineResult

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return {
        "sa": sa,
        "so": so,
        "db": db,
        "Researcher": Researcher,
        "Post": Post,
        "Message": Message,
        "Notification": Notification,
        "Gene": Gene,
        "Gene_Annotation": GeneAnnotation,
        "Pipeline_Run": PipelineRun,
        "PipelineResult": PipelineResult,
    }
