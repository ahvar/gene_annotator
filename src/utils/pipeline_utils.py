"""
Utility functions for ETL pipeline
"""

import typer
import logging
import sys
import os
from pathlib import Path
from datetime import datetime, time
import pandas as pd
from utils.logging_utils import LoggingUtils, LogFileCreationError
from utils.pipeline_exceptions import GeneAnnotationException, GeneDataException
from utils.references import (
    genes_file_name,
    gene_type_count_out_file,
    gene_annotations_file_name,
    gene_type_col,
    panther_id_col,
    pid_suffix_col,
    hgnc_id_col,
    hgnc_id_exists_col,
    count_col,
    excluded_tigrfam_file_name,
    tigrfam_id_col,
    excluded_tigrfam_vals,
    final_results_file_name,
    summary_styles,
    GENE_ANNOTATOR_CLI,
    GENE_ANNOTATOR_FRONTEND,
    __Application__,
    __version__,
)

gene_annotator_cli_logger = logging.getLogger(GENE_ANNOTATOR_CLI)
gene_annotator_frontend_logger = logging.getLogger(GENE_ANNOTATOR_FRONTEND)


def validate_outputdir(ctx: typer.Context, etl_output_dir: Path) -> Path:
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
        gene_annotator_cli_logger.error(
            f"The output directory for GATE: {etl_output_dir}"
        )
        raise typer.BadParameter(f"GATE output directory: {etl_output_dir}")
    if not etl_output_dir:
        gene_annotator_cli_logger.debug(
            "Creating default output directory and logfile...."
        )
        gene_annotator_cli_logger.debug("../etl/output_<timestamp>/")
        current_file_path = Path(__file__).resolve()
        project_root = current_file_path.parent.parent
        etl_output_dir = project_root / "etl" / f"output_{timestamp}" / "results"
        etl_output_dir.mkdir(parents=True)
    return etl_output_dir


def validate_inputdir(ctx: typer.Context, etl_input_dir: Path) -> Path:
    """
    A user has the option to pass ETL pipeline an input directory

    :param ctx:               the typer context object
    :param etl_input_dir:    the input directory for ETL Pipeline
    """
    if not etl_input_dir or not etl_input_dir.exists() or not etl_input_dir.is_dir():
        raise typer.BadParameter(
            f"Input directory '{etl_input_dir}' does not exist or is not a directory"
        )
    if not os.access(etl_input_dir, os.R_OK):
        raise typer.BadParameter(f"Cannot read from input directory '{etl_input_dir}' ")
    if not any(etl_input_dir.iterdir()):
        raise typer.BadParameter(f"Input directory '{etl_input_dir}' is empty")
    return etl_input_dir


def validate_style(ctx: typer.Context, style: str) -> str:
    """
    Validate the style of the summary report
    :param ctx:   the typer context object
    :param style: the style of the summary report
    :return style: the style of the summary report
    """
    if style == None:
        return summary_styles[0]
    if style.lower() not in summary_styles:
        gene_annotator_cli_logger.debug(f"Available summary styles: {summary_styles}")
        return summary_styles[0]
    return style


def init_cli_logging(log_level: str) -> LoggingUtils:
    """
    Initiate app log

    :params     log_level: the log level
    :returns LoggingUtils: logging utility for consistent log formats
    """
    try:
        timestamp = datetime.now().strftime("%m%d%yT%H%M%S")
        log_dir = Path("/opt/eon/log") / __Application__ / timestamp
        log_file = log_dir / "app.log"
        log_dir.mkdir(exist_ok=True, parents=True)

        logging_utils = LoggingUtils(
            application_name=GENE_ANNOTATOR_CLI,
            log_file=log_file,
            file_level=log_level,
            console_level=logging.ERROR,
        )
        return logging_utils
    except LogFileCreationError as lfe:
        set_error_and_exit(f"Unable to create log file: {lfe.filespec}")


def _make_logfile_parent_dir_and_get_path() -> Path:
    try:
        logfile_parent = (
            Path("/opt/eon/log")
            / __Application__
            / __version__.replace(".", "_")
            / datetime.now().strftime("%Y%m%d%H%M%S")
        )
        logfile_parent.mkdir(exist_ok=True, parents=True)
        return logfile_parent
    except LogFileCreationError as lfe:
        set_error_and_exit(f"Unable to create logfile parent dir: {lfe.filespec}")


def init_frontend_logger(log_level: str) -> LoggingUtils:
    try:
        logfile_parent = _make_logfile_parent_dir_and_get_path()
        log_file = logfile_parent / f"{GENE_ANNOTATOR_FRONTEND}.log"

        logging_utils = LoggingUtils(
            application_name=GENE_ANNOTATOR_FRONTEND,
            log_file=log_file,
            file_level=log_level,
            console_level=logging.ERROR,
        )
        return logging_utils
    except LogFileCreationError as lfe:
        set_error_and_exit(f"Unable to create log file: {lfe.filespec}")


def init_log_and_results_dir(etl_output_dir: Path) -> None:
    """
    Create the results and log output directories

    :params etl_output_dir: the etl output directory
    """
    for subdir in ["logs", "results"]:
        path = etl_output_dir / subdir
        path.mkdir()


def get_logger(etl_output_dir, log_level) -> LoggingUtils:
    """
    Construct and return a custom logger

    :params etl_output_dir: the etl output directory
    :params      log_level: the log level
    :return   LoggingUtils: a custom logger
    """
    logging_file = "pipeline.log"
    log_dir = etl_output_dir / "logs"
    app_log = LoggingUtils(
        application_name=f"{__Application__} {__version__}",
        log_file=log_dir / logging_file,
        file_level=log_level,
        console_level=logging.ERROR,
    )
    return app_log


def set_error_and_exit(error):
    """
    Reports the specified error and terminates the program..
    Parameters
    ----------
        error : str
            The error message to report.
    """
    sys.stderr.write(f"Error: {error} \n")


class GeneReader:
    """
    Provides functions for:
     - reading gene type and annotation data
     - identifying duplicate entries in datasets
     - counting unique genes
    """

    def __init__(self, input_dir: Path):
        """
        Construct GeneReader
        :params data_dir: the input directory
        """
        gene_annotator_cli_logger.debug(f"Constructing {self.__class__.__name__}...")
        self._input_dir = input_dir
        self._genes = pd.DataFrame()
        self._gene_annotations = pd.DataFrame()
        self._duplicate_genes = pd.DataFrame()
        self._duplicate_annotations = pd.DataFrame()
        self._results = pd.DataFrame()
        self._merged_genes_and_annotation_data = pd.DataFrame()
        gene_annotator_cli_logger.debug("Construction successful")

    def find_and_load_gene_data(self) -> None:
        """
        Gene and annotations data is expected to exist in data_dir

        :params       data_type: a the data type to read from the directory
        :raise FileNotFoundError: if the directory is invalid
        """
        gene_annotator_cli_logger.info(
            f"{self.__class__.__name__} is preparing to load gene and annotation data..."
        )
        if not self._input_dir.exists() or not self._input_dir.is_dir():
            raise FileNotFoundError(
                f"The directory {self._input_dir} in {self.__class__.__name__} does not exist or is not a directory."
            )
        self._check_that_dataset_exists(genes_file_name)
        self._check_that_dataset_exists(gene_annotations_file_name)
        gene_annotator_cli_logger.debug(
            f"{self.__class__.__name__} is reading gene and annotation data..."
        )
        self._gene_annotations = pd.read_csv(
            self._input_dir / gene_annotations_file_name, delimiter="\t"
        )
        self._genes = pd.read_csv(self._input_dir / genes_file_name)

    def _check_that_dataset_exists(self, data_set_file_name: str) -> None:
        """
        Checks that the dataset file exists
        :params     data_set_file_name: the filename with genes or annotations dataset
        :raise GeneAnnotationException: if an error finding the gene annotations dataset
        :raise       GeneDataException: if an error finding the gene dataset
        :rasie   FileNotFoundException: if error finding any file or if path is not a file
        """
        gene_annotator_cli_logger.info(
            f"{self.__class__.__name__} is checking that {data_set_file_name} datasets exist..."
        )
        try:
            data_file = list(self._input_dir.glob(f"*{data_set_file_name}"))[0]
            if data_file:
                if not data_file.exists() or not data_file.is_file():
                    if data_set_file_name.endswith(".tsv"):
                        raise GeneAnnotationException(
                            f"The directory {self._input_dir} in {self.__class__.__name__} does not have {gene_annotations_file_name}"
                        )
                    if data_set_file_name.endswith(".csv"):
                        raise GeneDataException(
                            f"The directory {self._input_dir} in {self.__class__.__name__} does not have {genes_file_name}"
                        )

                    raise FileNotFoundError(
                        f"The file {data_file} that was passed to {self.__class__.__name__} does not exist or is not a file."
                    )
        except IndexError as ie:
            raise FileNotFoundError(
                f"{self.__class__.__name__} did not find {data_set_file_name}"
            ) from ie

    def log_duplicates(self) -> None:
        """
        Log the number of duplicate records in genes and annotations
        """
        gene_annotator_cli_logger.info(
            f"{self.__class__.__name__} is finding duplicates..."
        )
        self._duplicate_genes = self._genes[self._genes.duplicated()]
        self._duplicate_annotations = self._gene_annotations[
            self._gene_annotations.duplicated()
        ]
        gene_annotator_cli_logger.info(
            f"DUPLICATE_RECORD_COUNT: {genes_file_name} - {len(self._duplicate_genes)}"
        )
        gene_annotator_cli_logger.info(
            f"DUPLICATE_RECORD_COUNT: {gene_annotations_file_name} - {len(self._duplicate_annotations)}"
        )

    def remove_duplicates(self) -> None:
        """
        Remove duplicate genes and annotations
        """
        gene_annotator_cli_logger.info(
            f"{self.__class__.__name__} is removing duplicates..."
        )
        self._genes = self._genes.drop_duplicates()
        self._gene_annotations = self._gene_annotations.drop_duplicates()

    def log_unique_records(self) -> None:
        """
        Log number of unique genes and annotations
        """
        gene_annotator_cli_logger.info(
            f"{self.__class__.__name__} logging unique records..."
        )
        gene_annotator_cli_logger.info(
            f"UNIQUE_RECORD_COUNT: {genes_file_name} - {len(self._genes)}"
        )
        gene_annotator_cli_logger.info(
            f"UNIQUE_RECORD_COUNT: {gene_annotations_file_name} - {len(self._gene_annotations)}"
        )

    def write_gene_type_count(self, results_dir: Path) -> None:
        """
        Writes the gene_type count to an output file: gene_type_count.csv
        :params results_dir: the results output directory
        """
        gene_annotator_cli_logger.info(
            f"{self.__class__.__name__} writing gene type count..."
        )
        gene_type_counts = self._genes[gene_type_col].value_counts().reset_index()
        gene_type_counts.columns = [gene_type_col, count_col]
        gene_type_counts.to_csv(results_dir / gene_type_count_out_file, index=False)

    def determine_if_hgnc_id_exists(self) -> None:
        """
        Creates a new column called "hgnc_id_exists" with True | False
        depending on whether "hgnc_id" column exists for that record

        Note:
         did not know that '~' was bitwise negation operator in Python and
         here with a Pandas series of boolean values it inverts the values
         so is True for rows where "hgnc_id" exists and False where it doesn't
        """
        self._genes[hgnc_id_exists_col] = ~self._genes[hgnc_id_col].isna()

    def parse_panther_id_suffix(self) -> None:
        """
        create a new column with the suffix sub-string from the
        column named: panther_id
        """
        self._gene_annotations[pid_suffix_col] = (
            self._gene_annotations[panther_id_col].str.split(":").str[-1]
        )

    def merge_gene_and_annotations(self, col_one: str, col_two: str) -> None:
        """
        Merge on two columns

        Note:
         'inner' joins returns only the rows for which there are matching keys in both DataFrames
        :params col_one: a column header
        :params col_two: another column header
        """
        self._merged_genes_and_annotation_data = pd.merge(
            self._genes, self._gene_annotations, how="inner", on=[col_one, col_two]
        )

    def exclude_tigrfram_and_write(self, results_dir: Path) -> None:
        """
        Exclude rows where the tigrfram_id is null or in ('TIGR00658', 'TIGR00936') and
        output those to file
        :params results_dir: the results dir
        """
        excluded_tigrfam = self._merged_genes_and_annotation_data[
            (self._merged_genes_and_annotation_data[tigrfam_id_col].isnull())
            | self._merged_genes_and_annotation_data[tigrfam_id_col].isin(
                excluded_tigrfam_vals
            )
        ]
        excluded_tigrfam.to_csv(results_dir / excluded_tigrfam_file_name)

    def write_gene_and_annotations_final(self, results_dir: Path) -> None:
        """
        Write the merged gene and annotation data to file
        Note:
         used the ~ operator again to negate the combined condition.
         This selects only those rows from genes_and_annotations that
         don't meet the conditions specified.
        """
        gene_annotator_cli_logger.info(
            f"{self.__class__.__name__} logging final records..."
        )
        final_result = self._merged_genes_and_annotation_data[
            ~(
                (self._merged_genes_and_annotation_data[tigrfam_id_col].isnull())
                | (
                    self._merged_genes_and_annotation_data[tigrfam_id_col].isin(
                        excluded_tigrfam_vals
                    )
                )
            )
        ]
        gene_annotator_cli_logger.info(f"FINAL_RECORD_COUNT: {len(final_result)}")
        final_result.to_csv(results_dir / final_results_file_name)

    @property
    def input_dir(self) -> Path:
        """
        Returns the data directory
        :return data_dir: the data directory
        """
        return self._input_dir

    @input_dir.setter
    def input_dir(self, data_dir: Path) -> None:
        """
        Sets the data directory
        :params data_dir: the data directory
        """
        self._input_dir = data_dir

    @property
    def genes(self) -> pd.DataFrame:
        """
        Returns gene dataset
        :return genes: gene dataset
        """
        return self._genes

    @property
    def gene_annotations(self) -> pd.DataFrame:
        """
        Returns the gene annotations dataset
        :return gene_annotations: gene annotations
        """
        return self._gene_annotations
