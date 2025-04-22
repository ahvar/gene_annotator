"""
TestCases for pipeline utility functions
"""

import unittest
from unittest.mock import patch, mock_open, MagicMock, Mock, call, PropertyMock
import pandas as pd
from io import StringIO
from datetime import datetime
from collections import namedtuple
from pandas.errors import EmptyDataError
from itertools import chain, repeat
from pathlib import Path
from src.utils.references import pid_suffix_col
from src.utils.pipeline_utils import (
    validate_outputdir,
    GeneReader,
    GeneDataException,
    GeneAnnotationException,
    gene_annotations_file_name,
    genes_file_name,
    pipeline_logger,
    _parse_timestamp,
    find_latest_output_dir
)
import typer
from typer import Context


class TestPipelineUtils(unittest.TestCase):
    """
    Unit tests for pipeline utils
    """

    def setUp(self):
        self.mock_dirs = [
            Path("output_042224T102030"),  # April 22, 2024 10:20:30
            Path("output_042223T102030"),  # April 22, 2023 10:20:30
            Path("output_042225T102030"),  # April 22, 2025 10:20:30
        ]

    def test_parse_timestamp(self):
        dir_path = dir_path = Path("output_042224T102030")
        expected = datetime(2024, 4, 22, 10, 20, 30)
        result = _parse_timestamp(dir_path)
        self.assertEqual(result, expected)

    def test_parse_invalid_timestap(self):
        dir_path = Path("invalid_directory")
        result = _parse_timestamp(dir_path)
        self.assertEqual(result, datetime.min)

    @patch("src.utils.pipeline_utils.Path")
    def test_find_latest_output_dir(self, mock_path_cls):
        """
        Ensure that all 'Path(...)' calls inside the function under test
        produce the same mock objects that we configure here.
        """
        mock_file_path = MagicMock(name="mock_file_path")
        mock_file_path.resolve.return_value = mock_file_path
        fake_root = MagicMock(name="fake_root")
        mock_file_path.parent = MagicMock(name="mock_file_path.parent")
        mock_file_path.parent.parent = fake_root
        mock_path_cls.return_value = mock_file_path
        mock_etl_dir = MagicMock(name="mock_etl_dir")
        
        fake_root.__truediv__.return_value = mock_etl_dir

        #
        # 4) Now build the "output_*" directories as mocks, all from the SAME mock_path_cls.
        #
        mock_dirs = []
        timestamps = ["042224T102030", "042223T102030", "042225T102030"]
        for ts in timestamps:
            dir_name = f"output_{ts}"
            dir_mock = MagicMock(name=f"MockDir-{dir_name}")
            dir_mock.name = dir_name
            dir_mock.is_dir.return_value = True
            mock_dirs.append(dir_mock)

        # If code does mock_etl_dir.glob("output_*"), return these
        mock_etl_dir.glob.return_value = mock_dirs

        #
        # 5) In the function, after picking the latest, it does `latest_dir / "results"`.
        #    That triggers `.__truediv__("results")` on whichever directory is chosen last.
        #    We'll let that produce a final mock to check.
        #
        # Let’s say each dir_mock.__truediv__("results") returns a new mock. We'll store
        # the one for "output_042225T102030" as the 'expected' so we can compare later.
        #
        dir_042225 = mock_dirs[2]
        results_path_for_042225 = MagicMock(name="results_of_042225")
        dir_042225.__truediv__.return_value = results_path_for_042225

        #
        # 6) Now call the function under test (with no argument),
        #    so it uses the code path that calls Path(__file__), etc.
        #
        result = find_latest_output_dir()

        #
        # 7) Check that we got the same mock we expected for the 'latest_dir / "results"'.
        #
        self.assertIs(result, results_path_for_042225)

    @patch('src.utils.pipeline_utils.Path')
    def test_find_latest_output_dir_empty(self, mock_path):
        """Test handling when no output directories exist"""
        mock_path.return_value.resolve.return_value.parent.parent = Path("/fake/root")
        mock_path.return_value.glob.return_value = []
        
        result = find_latest_output_dir()
        self.assertIsNone(result)

    @patch("src.utils.pipeline_utils.Path")
    @patch("typer.Context")
    def test_validate_etl_output_dir(self, mock_context, mock_path):
        """
        Test the validate etl output directory function
        """
        mock_instance = Mock()
        mock_path.return_value = mock_instance

        mock_instance.exists.return_value = False

        with self.assertRaises(typer.BadParameter):
            validate_outputdir(mock_context, mock_path("/path/to/nowhere"))

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
            validate_outputdir(Mock(), mock_path("/path/to/nonexistent"))


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

    @patch("src.utils.pipeline_utils.pd.read_csv")
    @patch("src.utils.pipeline_utils.Path.exists")
    @patch("src.utils.pipeline_utils.Path.is_dir")
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

    @patch("src.utils.pipeline_utils.Path.exists")
    @patch("src.utils.pipeline_utils.Path.is_dir")
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

    @patch("src.utils.pipeline_utils.Path.glob")
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

    @patch("src.utils.pipeline_utils.Path.glob")
    def test_check_that_dataset_exists_file_not_found(self, mock_glob):
        """
        Test dataset check when file doesn't exist
        :params mock_glob: mock object for Path.glob()
        """
        mock_glob.return_value = []

        with self.assertRaises(FileNotFoundError):
            self._gene_reader._check_that_dataset_exists("mock_dataset.csv")

    @patch("src.utils.pipeline_utils.Path.glob")
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

    @patch("src.utils.pipeline_utils.Path.glob")
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

        with patch.object(gene_etl_logger, "info") as mock_info:
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

        with patch.object(gene_etl_logger, "info") as mock_info:
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
