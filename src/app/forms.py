from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    BooleanField,
    SubmitField,
    DateField,
    FloatField,
)
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo
import sqlalchemy as sa
from app import db
from src.app.models.researcher import Researcher


class LoginForm(FlaskForm):
    researcher_name = StringField("Researcher Name", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Sign In")


class GeneAnnotationForm(FlaskForm):
    gene_name = StringField("Gene Name", validators=[DataRequired()])
    gene_type = StringField("Gene Type", validators=[DataRequired()])
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

class EmptyForm(FlaskForm):
    submit = SubmitField("Submit")