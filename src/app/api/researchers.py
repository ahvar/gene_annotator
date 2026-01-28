from src.app.api import bp
from src.app.api.errors import bad_request
from src.app.api.auth import token_auth
from src.app.models.researcher import Researcher
from src.app import db
import sqlalchemy as sa
from flask import request, url_for, abort


@bp.route("/researcher/<int:id>", methods=["GET"])
@token_auth.login_required
def get_researcher(id):
    """
    Retrieve a researcher by ID.
    Args:
        id: The unique identifier of the researcher to retrieve.
    Returns:
        dict: A dictionary representation of the researcher object.
    Raises:
        404: If no researcher with the given ID is found in the database.
    """

    return db.get_or_404(Researcher, id).to_dict()


@bp.route("/researchers", methods=["GET"])
@token_auth.login_required
def get_researchers():
    """
    Retrieve a paginated collection of researchers.
    This endpoint returns a paginated list of all researchers in the system.
    The pagination parameters can be controlled via query string parameters.
    Query Parameters:
        page (int, optional): Page number to retrieve. Defaults to 1.
        per_page (int, optional): Number of researchers per page. Defaults to 10.
                                 Maximum allowed is 100.
    Returns:
        dict: A dictionary containing the paginated collection of researchers,
              including metadata such as total count, current page, and pagination links.
    Example:
        GET /researchers?page=2&per_page=20
    """
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 10, type=int), 100)
    return Researcher.to_collection_dict(
        sa.select(Researcher), page, per_page, "src.api.get_researchers"
    )


@bp.route("/researchers/<int:id>/followers", methods=["GET"])
@token_auth.login_required
def get_followers(id):
    """
    Retrieve a paginated collection of followers for a specific researcher.
    Args:
        id (int): The unique identifier of the researcher whose followers to retrieve.
    Returns:
        dict: A paginated collection dictionary containing:
            - items: List of follower researcher objects
            - pagination metadata (current page, total pages, etc.)
    Query Parameters:
        page (int, optional): Page number to retrieve. Defaults to 1.
        per_page (int, optional): Number of items per page. Defaults to 10, max 100.
    Raises:
        404: If the researcher with the given ID is not found.
    """

    researcher = db.get_or_404(Researcher, id)
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 10, type=int), 100)
    return Researcher.to_collection_dict(
        researcher.followers.select(), page, per_page, "src.api.get_followers", id=id
    )


@bp.route("/researchers/<int:id>/following", methods=["GET"])
@token_auth.login_required
def get_following(id):
    """
    Retrieve a paginated collection of researchers that a specific researcher is following.
    Args:
        id (int): The unique identifier of the researcher whose following list to retrieve.
    Returns:
        dict: A paginated collection dictionary containing:
            - items: List of researcher objects that the specified researcher follows
            - pagination metadata (page, per_page, total, etc.)
            - navigation links for the collection
    Raises:
        404: If the researcher with the given id does not exist.
    Query Parameters:
        page (int, optional): Page number for pagination. Defaults to 1.
        per_page (int, optional): Number of items per page (max 100). Defaults to 10.
    """

    researcher = db.get_or_404(Researcher, id)
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 10, type=int), 100)
    return Researcher.to_collection_dict(
        researcher.following.select(), page, per_page, "src.api.get_following", id=id
    )


@bp.route("/researchers", methods=["POST"])
def create_researcher():
    """
    Create a new researcher in the database.
    This endpoint creates a new researcher account by validating the required fields,
    checking for duplicate researcher names and emails, and storing the researcher
    in the database.
    Expected JSON payload:
        - researcher_name (str): Unique name for the researcher
        - email (str): Unique email address for the researcher
        - password (str): Password for the researcher account
    Returns:
        tuple: A tuple containing:
            - dict: The created researcher's data as a dictionary
            - int: HTTP status code 201 (Created)
            - dict: Response headers with Location of the new resource
    Raises:
        BadRequest: If required fields are missing, researcher_name already exists,
                   or email already exists in the database
    """

    data = request.get_json()
    if "researcher_name" not in data or "email" not in data or "password" not in data:
        return bad_request("must include researcher_name, email, and password fields")
    if db.session.scalar(
        sa.select(Researcher).where(
            Researcher.researcher_name == data["researcher_name"]
        )
    ):
        return bad_request("please use a different researcher_name")
    if db.session.scalar(
        sa.select(Researcher).where(Researcher.email == data["email"])
    ):
        return bad_request("please use a different email")
    researcher = Researcher()
    researcher.from_dict(data, new_researcher=True)
    db.session.add(researcher)
    db.session.commit()
    return (
        researcher.to_dict(),
        201,
        {"Location": url_for("src.app.api.get_researcher", id=researcher.id)},
    )


@bp.route("/researcher/<int:id>", methods=["PUT"])
@token_auth.login_required
def update_researcher(id):
    """
    Update an existing researcher's information.
    This function updates a researcher's details based on the provided ID and JSON data.
    It performs validation to ensure that researcher names and email addresses remain unique
    across the system before applying updates.
    Args:
        id: The unique identifier of the researcher to update.
    Returns:
        dict: A dictionary representation of the updated researcher object.
    Raises:
        404: If no researcher is found with the given ID.
        400: If the new researcher name or email already exists for another researcher.
    Note:
        - If researcher_name is provided and differs from current name, checks for uniqueness
        - If email is provided and differs from current email, checks for uniqueness
        - Only updates fields that are provided in the request data
        - Commits changes to the database upon successful validation
    """
    if token_auth.current_user.id != id:
        abort(403)

    researcher = db.get_or_404(Researcher, id)
    data = request.get_json()
    if (
        "researcher_name" in data
        and data["researcher_name"] != researcher.researcher_name
        and db.session.scalar(
            sa.select(Researcher).where(
                Researcher.researcher_name == data["researcher_name"]
            )
        )
    ):
        return bad_request("please use a different researcher name")
    if (
        "email" in data
        and data["email"] != researcher.email
        and db.session.scalar(
            sa.select(Researcher).where(Researcher.email == data["email"])
        )
    ):
        return bad_request("please use a different email address")

    researcher.from_dict(data, new_researcher=False)
    db.session.commit()
    return researcher.to_dict()
