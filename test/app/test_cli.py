#!/usr/bin/env python
from pathlib import Path
from datetime import datetime, timezone, timedelta
import unittest
import logging
import sqlalchemy as sa
from unittest.mock import patch, MagicMock
import pytest
from src.app import create_app, db
from src.app.models.researcher import Researcher, Post
from src.app.models.gene import Gene, GeneAnnotation
from src.app.models.pipeline_run import PipelineResult, PipelineRun
from src.app.auth.email_service import send_password_reset_email
from src.app.cli import init_frontend_logger, GENE_ANNOTATOR_FRONTEND
from test.app.test_config import TestConfig


class TestCliLogging(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    @patch("src.app.cli._make_frontend_logfile")
    @patch("src.app.cli.LoggingUtils")
    def test_init_frontend_logger(self, mock_logging_utils, mock_make_logfile):
        """Test successful initialization of frontend logger"""
        # Import here to avoid circular imports
        # from src.app.cli import init_frontend_logger, GENE_ANNOTATOR_FRONTEND
        # import logging

        # Setup mocks
        mock_logfile_path = Path("/mocked/path/to/logfile.log")
        mock_make_logfile.return_value = mock_logfile_path
        mock_logger_instance = MagicMock()
        mock_logging_utils.return_value = mock_logger_instance

        # Call the function with logging.INFO
        result = init_frontend_logger(logging.INFO)

        # Check that mocks were called correctly
        mock_make_logfile.assert_called_once()
        mock_logging_utils.assert_called_once_with(
            application_name=GENE_ANNOTATOR_FRONTEND,
            log_file=mock_logfile_path,
            file_level=logging.INFO,
            console_level=logging.ERROR,
        )

        # Check the result is our mocked logger
        self.assertEqual(result, mock_logger_instance)

    @patch("src.app.cli._make_frontend_logfile")
    @patch("src.app.cli.LoggingUtils")
    def test_init_frontend_logger_with_exception(
        self, mock_logging_utils, mock_make_logfile
    ):
        """Test logger initialization with exception fallback"""
        # Import here to avoid circular imports
        # from src.app.cli import init_frontend_logger, GENE_ANNOTATOR_FRONTEND
        # import logging

        # Setup mock to raise an exception
        mock_make_logfile.side_effect = Exception("Test exception")
        mock_console_logger = MagicMock()
        mock_logging_utils.return_value = mock_console_logger

        # Call the function
        result = init_frontend_logger(logging.INFO)

        # Check that fallback was created
        mock_logging_utils.assert_called_once_with(
            application_name=GENE_ANNOTATOR_FRONTEND, console_level=logging.ERROR
        )

        # Check the result is our mocked console logger
        self.assertEqual(result, mock_console_logger)
