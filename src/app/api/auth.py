import sqlalchemy as sa
from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth
from src.app import db
from src.app.models.researcher import Researcher
from src.app.api.errors import error_response

basic_auth = HTTPBasicAuth()
token_auth = HTTPTokenAuth()


@token_auth.verify_token
def verify_token(token):
    """
    Verify the authenticity of a provided authentication token.
    Args:
        token (str or None): The authentication token to verify. Can be None.
    Returns:
        Researcher or None: Returns a Researcher object if the token is valid,
                           otherwise returns None if the token is invalid or None.
    """

    return Researcher.check_token(token) if token else None


@token_auth.error_handler
def token_auth_error(status):
    return error_response(status)


@basic_auth.verify_password
def verify_password(researcher_name, password):
    """
    Verify a researcher's password credentials.
    Args:
        researcher_name (str): The unique name of the researcher to authenticate.
        password (str): The plain text password to verify against the stored hash.
    Returns:
        Researcher or None: Returns the Researcher object if authentication succeeds,
                           None if the researcher is not found or password is incorrect.
    Raises:
        May raise database-related exceptions if the query fails.
    """

    researcher = db.session.scalar(
        sa.select(Researcher).where(Researcher.researcher_name == researcher_name)
    )
    if researcher and researcher.check_password(password):
        return researcher


@basic_auth.error_handler
def basic_auth_error(status):
    return error_response(status)
