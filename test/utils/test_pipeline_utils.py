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

    def setUp(self):
        self.ctx = Context()

    @patch("pathlib.Path")
    def test_validate_etl_output_dir(self, MockPath):
        """
        Test the validate etl output directory function
        """
        mock_instance = Mock()
        MockPath.return_value = mock_instance

        mock_instance.exists.return_value = False

        ctx = typer.Context(command=None)
        output_dir = validate_etl_output_dir(ctx, MockPath("/path/to/nowhere"))

        mock_instance.mkdir.assert_called_once()
        self.assertTrue("etl" in output_dir.parts)
