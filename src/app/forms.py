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


class LoginForm(FlaskForm):
    researcher_name = StringField("Researcher Name", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Sign In")


class GeneAnnotationForm(FlaskForm):
    """Form for manually entering gene annotations"""

    gene_stable_id = StringField("Gene Stable ID", validators=[DataRequired()])
    hgnc_id = StringField("HGNC ID")
    panther_id = StringField("Panther ID")
    tigrfam_id = StringField("Tigrfam ID")
    wikigene_name = StringField("Wikigene Name")
    gene_description = TextAreaField("Gene Description")
    submit = SubmitField("Search")


class RegistrationForm(FlaskForm):
    researcher_name = StringField("Researcher name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    password2 = PasswordField(
        "Repeat Password", validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Register")

    def validate_username(self, researcher_name):
        researcher = db.session.scalar(
            sa.select(Researcher).where(
                Researcher.researcher_name == researcher_name.data
            )
        )
        if researcher is not None:
            raise ValidationError("Please use a different researcher name")

    def validate_email(self, email):
        researcher = db.session.scalar(
            sa.select(Researcher).where(Researcher.email == email.data)
        )
        if researcher is not None:
            raise ValidationError("Please use a different email address")


class EditProfileForm(FlaskForm):
    researcher_name = StringField("Researcher Name", validators=[DataRequired()])
    about_me = TextAreaField("About Me", validators=[Length(min=0, max=140)])
    submit = SubmitField("Submit")

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
                raise ValidationError("Please use a different researcher name.")


class EmptyForm(FlaskForm):
    submit = SubmitField("Submit")
