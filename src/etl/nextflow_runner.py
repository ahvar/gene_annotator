#!/usr/bin/env python3
"""
ETL Gene Annotation Pipeline
"""
import logging
from pathlib import Path
import typer
import boto3
from rich import print as rprint
from typing import List
from typing_extensions import Annotated, Optional
from utils.logging_utils import LoggingUtils, LogFileCreationError
from utils.pipeline_utils import (
    validate_outputdir,
    validate_style,
    set_error_and_exit,
    init_log_and_results_dir,
    get_logger,
    GeneReader,
)
from src.utils.references import (
    GA_LOGGER_NAME,
    __version__,
    __Application__,
    gene_stable_id_col,
    hgnc_id_col,
)

cli = typer.Typer()

gene_etl_logger = logging.getLogger(GA_LOGGER_NAME)


class NextflowRunner:
    def __init__(self) -> None:
        pass

    def set_nfx_log(self) -> None:
        pass

    def set_nfx_workdir(self) -> None:
        pass

    def build_nxf_cmd(self) -> str:
        pass


@cli.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def summarize(
    ctx: typer.Context,
    style: Annotated[
        Optional[str],
        typer.Option(
            None,
            "-s",
            "--style",
            callback=validate_style,
            help="Summarize available data sources in JSON or TXT style report",
        ),
    ],
    outputdir: Annotated[
        Optional[Path],
        typer.Option(
            None,
            "-o",
            "--output-directory",
            exists=True,
            file_okay=True,
            dir_okay=False,
            writable=True,
            callback=validate_outputdir,
            help="The ETL pipeline output directory",
        ),
    ],
    debug: bool = typer.Option(
        False,
        "-b",
        "--debug",
        help="Set log level to debug",
    ),
):
    """
    Describe the datasets that are available
    """
    try:
        if debug:
            log_level = logging.DEBUG
        else:
            log_level = logging.INFO
        init_log_and_results_dir(etl_output_dir=outputdir)
        app_log = get_logger(etl_output_dir=outputdir, log_level=log_level)
        app_log.logApplicationStart()
        s3 = boto3.client("s3")
        bucket = "genomics-data-repository"
        response = s3.list_objects_v2(Bucket=bucket)
        if style == "json":
            rprint(response)
        else:
            for obj in response["Contents"]:
                rprint(f"Key: {obj['Key']} Size: {obj['Size']}")

    except LogFileCreationError as lfe:
        set_error_and_exit(f"Unable to create log file: {lfe.filespec}")
    except Exception as err:
        set_error_and_exit(f"Unable to initiate Application: {err}")
    finally:
        gene_etl_logger.logApplicationFinish()


@cli.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def annotate(
    ctx: typer.Context,
    style: Annotated[
        Optional[str],
        typer.Option(
            None,
            "-s",
            "--style",
            callback=validate_style,
            help="Summarize available data sources in JSON or TXT style report",
        ),
    ],
    outputdir: Annotated[
        Optional[Path],
        typer.Option(
            None,
            "-o",
            "--output-directory",
            exists=True,
            file_okay=True,
            dir_okay=False,
            writable=True,
            callback=validate_outputdir,
            help="The ETL pipeline output directory",
        ),
    ],
    debug: bool = typer.Option(
        False,
        "-b",
        "--debug",
        help="Set log level to debug",
    ),
):

    try:
        if debug:
            log_level = logging.DEBUG
        else:
            log_level = logging.INFO

        init_log_and_results_dir(etl_output_dir=outputdir)
        app_log = get_logger(etl_output_dir=outputdir, log_level=log_level)
        app_log.logApplicationStart()

        gene_reader = GeneReader(outputdir.parent / "data")
        gene_reader.find_and_load_gene_data()
        gene_reader.log_duplicates()
        gene_reader.remove_duplicates()
        gene_reader.log_unique_records()
        gene_reader.write_gene_type_count(outputdir / "results")
        gene_reader.determine_if_hgnc_id_exists()
        gene_reader.parse_panther_id_suffix()
        gene_reader.merge_gene_and_annotations(
            col_one=gene_stable_id_col, col_two=hgnc_id_col
        )
        gene_reader.exclude_tigrfram_and_write(outputdir / "results")
        gene_reader.write_gene_and_annotations_final(outputdir / "results")

    except LogFileCreationError as lfe:
        set_error_and_exit(f"Unable to create log file: {lfe.filespec}")
    except Exception as err:
        set_error_and_exit(f"Unable to initiate Application: {err}")
    finally:
        app_log.logApplicationFinish()


if __name__ == "__main__":
    cli()
