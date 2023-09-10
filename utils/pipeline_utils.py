"""
Utility functions for GATE pipeline.py
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
__Application__ = "GATE"
GATE_LOGGER_NAME = __Application__ + "__" + __version__ + "_" + "gate"

gate_logger = logging.getLogger(GATE_LOGGER_NAME)


def get_formatted_date() -> datetime:
    """
    Returns a string representation of today's date
    @return date: "YYYY-MM-DD"
    """
    today = datetime.today()
    return today.strftime("%Y-%m-%d")


def validate_gate_output_dir(ctx: typer.Context, gate_output_dir: Path) -> Path:
    """
    A user has the option to pass GATE a log dir path

    :param ctx:               the typer context object
    :param gate_output_dir:   the output directory
    """
    timestamp = datetime.datetime.utcnow().strftime("%Y_%m_%dT%H_%M_%SZ")
    if gate_output_dir and gate_output_dir.exists():
        user_specified_output_dir = gate_output_dir / f"output_{timestamp}"
        return user_specified_output_dir
    if gate_output_dir and not gate_output_dir.exists():
        gate_logger.error(f"The output directory for GATE: {gate_output_dir}")
        raise typer.BadParameter(f"GATE output directory: {gate_output_dir}")
    if not gate_output_dir:
        gate_logger.debug("Creating default output directory and logfile....")
        gate_logger.debug(f"../etl/output_<timestamp>/")
        current_file_path = Path(__file__).resolve()
        project_root = current_file_path.parent
        gate_output_dir = project_root / "etl" / f"output_{timestamp}"
        gate_output_dir.mkdir()
    return gate_output_dir


def set_error_and_exit(error):
    """
    Reports the specified error and terminates the program..
    Parameters
    ----------
        error : str
            The error message to report.
    """
    sys.stderr.write(f"Error: {error} \n")
