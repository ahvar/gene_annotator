#!/usr/bin/env python3
"""
ETL Pipeline: Extact Transform Load
"""
import logging
from pathlib import Path
import typer
from typing_extensions import Annotated
from utils.logging_utils import LoggingUtils, LogFileCreationError
from utils.pipeline_utils import (
    validate_etl_output_dir,
    set_error_and_exit,
    init_log_and_results_dir,
    get_logger,
    GeneReader,
)
from utils.references import gene_stable_id_col, hgnc_id_col

cli = typer.Typer()

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


@cli.command(
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

        init_log_and_results_dir(etl_output_dir=etl_output_dir)
        app_log = get_logger(etl_output_dir=etl_output_dir, log_level=log_level)
        app_log.logApplicationStart()

        gene_reader = GeneReader(etl_output_dir.parent / "data")
        gene_reader.find_and_load_gene_data()
        gene_reader.log_duplicates()
        gene_reader.remove_duplicates()
        gene_reader.log_unique_records()
        gene_reader.write_gene_type_count(etl_output_dir / "results")
        gene_reader.determine_if_hgnc_id_exists()
        gene_reader.parse_panther_id_suffix()
        gene_reader.merge_gene_and_annotations(
            col_one=gene_stable_id_col, col_two=hgnc_id_col
        )
        gene_reader.exclude_tigrfram_and_write(etl_output_dir / "results")
        gene_reader.write_gene_and_annotations_final(etl_output_dir / "results")

    except LogFileCreationError as lfe:
        set_error_and_exit(f"Unable to create log file: {lfe.filespec}")
    except Exception as err:
        set_error_and_exit(f"Unable to initiate Application: {err}")
    finally:
        app_log.logApplicationFinish()


if __name__ == "__main__":
    cli()
