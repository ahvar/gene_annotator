import logging
import typer
from rich import print as rprint
from src.utils.logging_utils import init_logging, set_error_and_exit
from src.utils.references import IB_API_LOGGER_NAME, __version__, __Application__

cliapp = typer.Typer()

logger = logging.getLogger(IB_API_LOGGER_NAME)


def version_callback(value: bool):
    if value:
        typer.echo(__version__)
        raise typer.Exit


@cliapp.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show software version",
    ),
):
    """
    Prints application information and exits if no subcommand is provided.
    """
    message = f"""
    [bold]------------------------------------------------------------------------------------------------[/bold]
    [bold blue]{__Application__.replace("_", " ").upper()} {__version__} [/bold blue]
    [bold yellow]Analyze and QC Genomic Data [/bold yellow]
    [bold]------------------------------------------------------------------------------------------------[/bold]

    [green]Usage:[/green]
    Available Data:
     - Datasets for mitochondrial genes
     - NIH Sequence Read Archive (SRA)
     - mock fastq files
    """
    if ctx.invoked_subcommand is None:
        rprint(message)
        raise typer.Exit()


if __name__ == "__main__":
    try:
        app_log = init_logging(logging.DEBUG)
        app_log.log_application_start()
        cliapp()
    except Exception as e:
        logger.error("An error occurred: %s", e)
        set_error_and_exit(e)
    finally:
        app_log.log_application_finish()
