"""
TestCases for pipeline utility functions
"""

import unittest
from unittest.mock import patch, mock_open, MagicMock, Mock, call, PropertyMock
import pandas as pd
from io import StringIO
from collections import namedtuple
from pandas.errors import EmptyDataError
from itertools import chain, repeat
from pathlib import Path
from utils.references import pid_suffix_col
from utils.pipeline_utils import (
    validate_etl_output_dir,
    GeneReader,
    GeneDataException,
    GeneAnnotationException,
    gene_annotations_file_name,
    genes_file_name,
    etl_logger,
)
import typer
from typer import Context


class TestPipelineUtils(unittest.TestCase):
    """
    Unit tests for pipeline utils
    """

    # def setUp(self):
    #    self.ctx = Context()

    @patch("pathlib.Path")
    @patch("typer.Context")
    def test_validate_etl_output_dir(self, mock_context, mock_path):
        """
        Test the validate etl output directory function
        """
        mock_instance = Mock()
        mock_path.return_value = mock_instance

        mock_instance.exists.return_value = False

        with self.assertRaises(typer.BadParameter):
            validate_etl_output_dir(mock_context, mock_path("/path/to/nowhere"))

        mock_instance.mkdir.assert_not_called()

    @patch("pathlib.Path")
    def test_validate_etl_output_dir_nonexistent(self, mock_path):
        """
        Test the validate_etl_output_directory function when the directory doesn't exist.
        """
        mock_instance = Mock()
        mock_instance.exists.return_value = False
        mock_path.return_value = mock_instance

        with self.assertRaises(typer.BadParameter):
            validate_etl_output_dir(Mock(), mock_path("/path/to/nonexistent"))


class TestGeneReader(unittest.TestCase):
    """
    TestCase for the GeneReader class
    """

    def setUp(self):
        """
        Set up objects or fake data useful for all unit tests
        """
        self._data_dir = Path("/mock/data/dir")
        self._gene_reader = GeneReader(self._data_dir)

    @patch("utils.pipeline_utils.pd.read_csv")
    @patch("utils.pipeline_utils.Path.exists")
    @patch("utils.pipeline_utils.Path.is_dir")
    def test_find_and_load_gene_data_valid_dir(
        self, mock_is_dir, mock_exists, mock_read_csv
    ):
        """
        Test finding and loading gene data from a valid data directory
        :params mock_read_csv: mock object for pandas read_csv function
        :params   mock_exists: mock object for Path.exists()
        :params   mock_is_dir: mock object for Path.is_dir()
        """
        mock_dataframe = pd.DataFrame()
        mock_read_csv.return_value = mock_dataframe

        with patch.object(
            self._gene_reader, "_check_that_dataset_exists", return_value=None
        ):
            self._gene_reader.find_and_load_gene_data()

    @patch("utils.pipeline_utils.Path.exists")
    @patch("utils.pipeline_utils.Path.is_dir")
    def test_find_and_load_gene_data_invalid_dir(self, mock_is_dir, mock_exists):
        """
        Test finding and loading data from an invalid data directory
        :params mock_is_dir: mock object for Path.is_dir()
        :params mock_exists: mock object for Path.exists()
        """
        mock_exists.return_value = False
        mock_is_dir.return_value = False

        with self.assertRaises(FileNotFoundError):
            self._gene_reader.find_and_load_gene_data()

    @patch("utils.pipeline_utils.Path.glob")
    def test_check_that_dataset_exists_file_exists(self, mock_glob):
        """
        Test dataset check when files exists
        :params mock_glob: mock object on Path.glob()
        """
        mock_file = MagicMock()
        mock_file.exists.return_value = True
        mock_file.is_file.return_value = True
        mock_glob.return_value = [mock_file]

        # This should not raise any exception
        self._gene_reader._check_that_dataset_exists("mock_dataset.csv")

    @patch("utils.pipeline_utils.Path.glob")
    def test_check_that_dataset_exists_file_not_found(self, mock_glob):
        """
        Test dataset check when file doesn't exist
        :params mock_glob: mock object for Path.glob()
        """
        mock_glob.return_value = []

        with self.assertRaises(FileNotFoundError):
            self._gene_reader._check_that_dataset_exists("mock_dataset.csv")

    @patch("utils.pipeline_utils.Path.glob")
    def test_check_that_dataset_exists_invalid_annotation_file(self, mock_glob):
        """
        Test dataset check when dataset file for annotations is invalid
        :params mock_glob: mock object for Path.glob()
        """
        mock_file = MagicMock()
        mock_file.exists.return_value = False
        mock_file.is_file.return_value = False
        mock_glob.return_value = [mock_file]

        with self.assertRaises(GeneAnnotationException):
            self._gene_reader._check_that_dataset_exists("mock_dataset.tsv")

    @patch("utils.pipeline_utils.Path.glob")
    def test_check_that_dataset_exists_invalid_gene_file(self, mock_glob):
        """
        Test dataset when dataset file for genes is invalid
        :params mock_glob: mock object for Path.glob()
        """
        mock_file = MagicMock()
        mock_file.exists.return_value = False
        mock_file.is_file.return_value = False
        mock_glob.return_value = [mock_file]

        with self.assertRaises(GeneDataException):
            self._gene_reader._check_that_dataset_exists("mock_dataset.csv")

    def test_log_duplicates(self):
        """
        Test logging of duplicates in genes and annotations data
        """
        genes_data = pd.DataFrame({"gene": ["gene1", "gene2", "gene1"]})
        annotations_data = pd.DataFrame({"annotation": ["anno1", "anno2", "anno2"]})

        self._gene_reader._genes = genes_data
        self._gene_reader._gene_annotations = annotations_data

        with patch.object(etl_logger, "info") as mock_info:
            self._gene_reader.log_duplicates()

            assert len(self._gene_reader._duplicate_genes) == 1
            assert len(self._gene_reader._duplicate_annotations) == 1
            mock_info.assert_called()

    def test_remove_duplicates(self):
        """
        Test removal of duplicates in genes and annotations data
        """
        genes_data = pd.DataFrame({"gene": ["gene1", "gene2", "gene1"]})
        annotations_data = pd.DataFrame({"annotation": ["anno1", "anno2", "anno2"]})

        self._gene_reader._genes = genes_data
        self._gene_reader._gene_annotations = annotations_data

        self._gene_reader.remove_duplicates()

        assert len(self._gene_reader._genes) == 2
        assert len(self._gene_reader._gene_annotations) == 2

    def test_log_unique_records(self):
        """
        Test logging of unique records in genes and annotations data
        """
        genes_data = pd.DataFrame({"gene": ["gene1", "gene2", "gene3"]})
        annotations_data = pd.DataFrame({"annotation": ["anno1", "anno2", "anno3"]})

        self._gene_reader._genes = genes_data
        self._gene_reader._gene_annotations = annotations_data

        with patch.object(etl_logger, "info") as mock_info:
            self._gene_reader.log_unique_records()
            mock_info.assert_called()

    def test_determine_if_hgnc_id_exists(self):
        """
        Test creation of the 'hgnc_id_exists' column
        """
        genes_data = pd.DataFrame({"hgnc_id": [1, None, 3]})
        self._gene_reader._genes = genes_data

        self._gene_reader.determine_if_hgnc_id_exists()

        assert self._gene_reader._genes["hgnc_id_exists"].tolist() == [
            True,
            False,
            True,
        ]

    def test_parse_panther_id_suffix(self):
        """
        Test creation of the panther id suffix column
        """
        annotations_data = pd.DataFrame(
            {"panther_id": ["PANTHER:001", "PANTHER:002", None]}
        )
        self._gene_reader._gene_annotations = annotations_data

        self._gene_reader.parse_panther_id_suffix()

        assert self._gene_reader._gene_annotations[pid_suffix_col].tolist() == [
            "001",
            "002",
            None,
        ]
