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
from utils.pipeline_utils import validate_gate_output_dir
from typer import Context


class TestPipelineUtils(unittest.TestCase):
    """
    Unit tests for pipeline utils
    """
    def setUp(self):
        self.ctx = Context()

    
    def test_validate_gate_output_dir(self, mock_path)
