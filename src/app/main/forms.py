from flask import request
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import ValidationError, DataRequired, Length
import sqlalchemy as sa
from flask_babel import _, lazy_gettext as _l
from src.app import db
from src.app.models.researcher import Researcher


class EditProfileForm(FlaskForm):
    researcher_name = StringField(_l("Researcher Name"), validators=[DataRequired()])
    about_me = TextAreaField(_l("About Me"), validators=[Length(min=0, max=140)])
    submit = SubmitField(_l("Submit"))

    def __init__(self, original_researcher_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_researcher_name = original_researcher_name

    def validate_username(self, researcher_name):
        if researcher_name.data != self.original_researcher_name:
            researcher = db.session.scalar(
                sa.select(Researcher).where(
                    Researcher.researcher_name == researcher_name.data
                )
            )
            if researcher is not None:
                raise ValidationError(_l("Please use a different researcher name."))


class PostForm(FlaskForm):
    post = TextAreaField(
        _l("Say something"), validators=[DataRequired(), Length(min=1, max=140)]
    )
    submit = SubmitField(_l("Submit"))


class EmptyForm(FlaskForm):
    submit = SubmitField(_l("Submit"))


class GeneAnnotationForm(FlaskForm):
    """Form for manually entering gene annotations"""

    gene_stable_id = StringField(_l("Gene Stable ID"), validators=[DataRequired()])
    hgnc_id = StringField(_l("HGNC ID"))
    panther_id = StringField(_l("Panther ID"))
    tigrfam_id = StringField(_l("Tigrfam ID"))
    wikigene_name = StringField(_l("Wikigene Name"))
    gene_description = TextAreaField(_l("Gene Description"))
    submit = SubmitField(_l("Search"))


class SearchForm(FlaskForm):
    q = StringField(_l("Search"), validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        if "formdata" not in kwargs:
            kwargs["formdata"] = request.args
        if "meta" not in kwargs:
            kwargs["meta"] = {"csrf": False}
        super(SearchForm, self).__init__(*args, **kwargs)
