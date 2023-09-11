#!/usr/bin/env python3
"""
ETL Pipeline: Extact Transform Load
"""
import logging
from pathlib import Path
import typer
from typing_extensions import Annotated
from utils.logging_utils import LoggingUtils, LogFileCreationError
from utils.pipeline_utils import validate_etl_output_dir, set_error_and_exit

app = typer.Typer()

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


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def main(
    ctx: typer.Context,
    etl_output_dir: Path = typer.Option(
        None,
        "-o",
        "--etl-output-directory",
        exists=True,
        file_okay=True,
        dir_okay=False,
        writable=True,
        callback=validate_etl_output_dir,
        help="The ETL pipeline output directory",
    ),
    debug: bool = typer.Option(
        False,
        "-b",
        "--debug",
        help="Set log level to debug",
    ),
):
    """
    ETL Pipeline v1.0.0:
    This application is designed to read gene annotation data, identify duplicate entries, and report gene counts.
    """

    try:
        if debug:
            log_level = logging.DEBUG
        else:
            log_level = logging.INFO

        # create the logs and results sub-directories
        logs_and_results = ["logs", "results"]
        for subdir in logs_and_results:
            path = etl_output_dir / subdir
            path.mkdir()

        logging_file = "pipeline.log"
        log_dir = etl_output_dir / "logs"
        app_log = LoggingUtils(
            applicationName=f"{__Application__} {__version__}",
            logFile=log_dir / logging_file,
            fileLevel=log_level,
            consoleLevel=logging.ERROR,
        )
        app_log.logApplicationStart()

    except LogFileCreationError as lfe:
        set_error_and_exit(f"Unable to create log file: {lfe.filespec}")
    except Exception as err:
        set_error_and_exit(f"Unable to initiate Application and Auditor logs: {err}")
    finally:
        app_log.logApplicationFinish()


if __name__ == "__main__":
    app()
