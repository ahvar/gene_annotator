from flask_babel import lazy_gettext as _l
from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    BooleanField,
    SubmitField,
    TextAreaField,
    DateField,
    FloatField,
)
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo, Length
import sqlalchemy as sa
from src.app import db
from src.app.models.researcher import Researcher
from src.app.models.gene import Gene, GeneAnnotation


class GeneAnnotationForm(FlaskForm):
    """Form for manually entering gene annotations"""

    gene_stable_id = StringField(_l("Gene Stable ID"), validators=[DataRequired()])
    hgnc_id = StringField(_l("HGNC ID"))
    panther_id = StringField(_l("Panther ID"))
    tigrfam_id = StringField(_l("Tigrfam ID"))
    wikigene_name = StringField(_l("Wikigene Name"))
    gene_description = TextAreaField(_l("Gene Description"))
    submit = SubmitField(_l("Search"))
