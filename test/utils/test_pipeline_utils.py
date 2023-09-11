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
from utils.pipeline_utils import validate_etl_output_dir
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
