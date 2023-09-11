"""
Utility functions for ETL pipeline
"""

import typer
import logging
import sys
from pathlib import Path
from datetime import datetime

__version__ = "1.0.0"
__copyright__ = (
    "Copyright \xa9 2023 Bristol Myers Squibb | "
    "Informatics and Predictive Sciences. All rights reserved.".encode(
        "utf-8", "ignore"
    )
)
__Application__ = "ETL_PIPELINE"
ETL_LOGGER_NAME = __Application__ + "__" + __version__

etl_logger = logging.getLogger(ETL_LOGGER_NAME)


def get_formatted_date() -> datetime:
    """
    Returns a string representation of today's date
    @return date: "YYYY-MM-DD"
    """
    today = datetime.today()
    return today.strftime("%Y-%m-%d")


def validate_etl_output_dir(ctx: typer.Context, etl_output_dir: Path) -> Path:
    """
    A user has the option to pass ETL pipeline an output dir, otherwise,
    sets default

    :param ctx:               the typer context object
    :param etl_output_dir:    the output directory for ETL Pipeline
    """
    timestamp = datetime.utcnow().strftime("%m%d%yT%H%M%S")
    if etl_output_dir and etl_output_dir.exists():
        user_specified_output_dir = etl_output_dir / f"output_{timestamp}"
        return user_specified_output_dir
    if etl_output_dir and not etl_output_dir.exists():
        etl_logger.error(f"The output directory for GATE: {etl_output_dir}")
        raise typer.BadParameter(f"GATE output directory: {etl_output_dir}")
    if not etl_output_dir:
        etl_logger.debug("Creating default output directory and logfile....")
        etl_logger.debug(f"../etl/output_<timestamp>/")
        current_file_path = Path(__file__).resolve()
        project_root = current_file_path.parent.parent
        etl_output_dir = project_root / "etl" / f"output_{timestamp}"
        etl_output_dir.mkdir()
    return etl_output_dir


def set_error_and_exit(error):
    """
    Reports the specified error and terminates the program..
    Parameters
    ----------
        error : str
            The error message to report.
    """
    sys.stderr.write(f"Error: {error} \n")
