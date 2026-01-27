from werkzeug.http import HTTP_STATUS_CODES
from werkzeug.exceptions import HTTPException
from src.app.api import bp


def error_response(status_code, message=None):
    """
    Generate a standardized error response payload.
    Args:
        status_code (int): HTTP status code for the error
        message (str, optional): Additional error message. Defaults to None.
    Returns:
        tuple: A tuple containing:
            - dict: Error payload with 'error' key and optional 'message' key
            - int: The HTTP status code
    Example:
        >>> error_response(404, "Resource not found")
        ({'error': 'Not Found', 'message': 'Resource not found'}, 404)
    """

    payload = {"error": HTTP_STATUS_CODES.get(status_code, "Unknown error")}
    if message:
        payload["message"] = message
    return payload, status_code


def bad_request(message):
    return error_response(400, message)


@bp.errorhandler(HTTPException)
def handle_exception(e):
    return error_response(e.code)
