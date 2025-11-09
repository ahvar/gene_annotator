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


class TestGeneModel(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_gene_creation(self):
        """Test basic gene creation and retrieval"""
        g = Gene(
            gene_stable_id="ENSG00000139618",
            gene_type="protein_coding",
            gene_name="BRCA2",
            hgnc_name="BRCA2",
            hgnc_id="HGNC:1101",
            hgnc_id_exists=True,
        )
        db.session.add(g)
        db.session.commit()

        # Retrieve the gene
        retrieved_gene = db.session.get(Gene, g.id)
        self.assertEqual(retrieved_gene.gene_stable_id, "ENSG00000139618")
        self.assertEqual(retrieved_gene.gene_name, "BRCA2")
        self.assertTrue(retrieved_gene.hgnc_id_exists)

    def test_gene_annotation_relationship(self):
        """Test relationship between Gene and GeneAnnotation"""
        g = Gene(
            gene_stable_id="ENSG00000139618",
            gene_type="protein_coding",
            gene_name="BRCA2",
        )
        db.session.add(g)

        # Create annotation linked to the gene
        ga = GeneAnnotation(
            gene_stable_id="ENSG00000139618",
            hgnc_id="HGNC:1101",
            panther_id="PTHR11289",
            tigrfam_id="TIGR00580",
            wikigene_name="BRCA2",
            gene_description="DNA repair associated",
        )
        db.session.add(ga)
        db.session.commit()

        # Check if we can retrieve the annotation with the gene stable ID
        annotations = db.session.scalars(
            sa.select(GeneAnnotation).where(
                GeneAnnotation.gene_stable_id == g.gene_stable_id
            )
        ).all()

        self.assertEqual(len(annotations), 1)
        self.assertEqual(annotations[0].hgnc_id, "HGNC:1101")
        self.assertEqual(annotations[0].wikigene_name, "BRCA2")


class TestPipelineRunModel(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Create a test researcher
        self.researcher = Researcher(
            researcher_name="researcher1", email="researcher1@example.com"
        )
        db.session.add(self.researcher)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_pipeline_run_creation(self):
        """Test creating a pipeline run and associated results"""
        # Create a pipeline run
        run = PipelineRun(
            pipeline_name="Gene ETL Pipeline",
            pipeline_type="TEST",
            output_dir="/some/output/dir",
            status="completed",
            researcher_id=self.researcher.id,
        )
        db.session.add(run)
        db.session.commit()

        # Add pipeline results
        result1 = PipelineResult(
            run_id=run.id,
            gene_stable_id="ENSG00000139618",
            gene_type="protein_coding",  # Add this line
            gene_name="BRCA2",
            hgnc_id="HGNC:1101",
            panther_id="PTHR11289",
            tigrfam_id="TIGR00580",
        )
        result2 = PipelineResult(
            run_id=run.id,
            gene_stable_id="ENSG00000141510",
            gene_type="protein_coding",  # Add this line
            gene_name="TP53",
            hgnc_id="HGNC:11998",
            panther_id="PTHR11447",
            tigrfam_id="TIGR00590",
        )
        db.session.add_all([result1, result2])
        db.session.commit()

        # Retrieve the run and check its results
        retrieved_run = db.session.get(PipelineRun, run.id)
        results = db.session.scalars(
            sa.select(PipelineResult).where(PipelineResult.run_id == run.id)
        ).all()

        self.assertEqual(retrieved_run.pipeline_name, "Gene ETL Pipeline")
        self.assertEqual(retrieved_run.status, "completed")
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].gene_name, "BRCA2")
        self.assertEqual(results[1].gene_name, "TP53")

    def test_pipeline_run_researcher_relationship(self):
        """Test relationship between PipelineRun and Researcher"""
        run = PipelineRun(
            pipeline_name="Gene ETL Pipeline",
            pipeline_type="TEST",  # Add this required field
            output_dir="/another/dir",  # Add this required field
            status="completed",
            researcher_id=self.researcher.id,
        )
        db.session.add(run)
        db.session.commit()

        # Retrieve the run and check its researcher
        retrieved_run = db.session.get(PipelineRun, run.id)
        self.assertEqual(retrieved_run.researcher.researcher_name, "researcher1")

        # Check if researcher can access their runs
        researcher_runs = db.session.scalars(
            sa.select(PipelineRun).where(
                PipelineRun.researcher_id == self.researcher.id
            )
        ).all()
        self.assertEqual(len(researcher_runs), 1)
        self.assertEqual(researcher_runs[0].id, run.id)


class TestPasswordResetTokens(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_password_reset_token(self):
        """Test generation and verification of password reset tokens"""
        r = Researcher(researcher_name="testuser", email="test@example.com")
        r.set_password("originalpassword")
        db.session.add(r)
        db.session.commit()

        token = r.get_reset_password_token()
        self.assertIsNotNone(token)

        verified_user = Researcher.verify_reset_password_token(token)
        self.assertEqual(verified_user.id, r.id)

        invalid_token = "invalid-token"
        self.assertIsNone(Researcher.verify_reset_password_token(invalid_token))


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


class TestUserLoading(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    @patch("builtins.open")
    @patch("json.load")
    def test_load_test_users(self, mock_json_load, mock_open):
        """Test loading of test users from JSON file"""
        from src.app.cli import load_test_users

        # Mock test user data
        test_users = [
            {
                "researcher_name": "test_user1",
                "email": "test1@example.com",
                "password": "password1",
                "about_me": "Test user 1",
                "posts": ["Post from test user 1"],
                "following": ["test_user2"],
            },
            {
                "researcher_name": "test_user2",
                "email": "test2@example.com",
                "password": "password2",
                "about_me": "Test user 2",
                "posts": ["Post from test user 2"],
                "following": [],
            },
        ]

        # Configure mocks
        mock_json_load.return_value = test_users
        mock_open.return_value.__enter__.return_value = "mocked_file"

        # Call the function to test
        load_test_users()

        # Verify users were created
        users = db.session.scalars(sa.select(Researcher)).all()
        self.assertEqual(len(users), 2)

        # Verify user details
        user1 = db.session.scalar(
            sa.select(Researcher).where(Researcher.researcher_name == "test_user1")
        )
        user2 = db.session.scalar(
            sa.select(Researcher).where(Researcher.researcher_name == "test_user2")
        )

        self.assertEqual(user1.email, "test1@example.com")
        self.assertEqual(user1.about_me, "Test user 1")
        self.assertTrue(user1.check_password("password1"))

        self.assertEqual(user2.email, "test2@example.com")
        self.assertEqual(user2.about_me, "Test user 2")
        self.assertTrue(user2.check_password("password2"))

        # Verify posts were created
        posts = db.session.scalars(sa.select(Post)).all()
        self.assertEqual(len(posts), 2)

        # Verify following relationship
        self.assertTrue(user1.is_following(user2))
        self.assertFalse(user2.is_following(user1))

        self.assertEqual(user1.following_count(), 1)
        self.assertEqual(user2.followers_count(), 1)

    @patch("builtins.open")
    @patch("builtins.print")
    def test_load_test_users_file_not_found(self, mock_print, mock_open):
        """Test handling of missing test_users.json file"""
        from src.app.cli import load_test_users

        # Simulate file not existing
        mock_open.side_effect = FileNotFoundError("File not found")

        # Call the function
        load_test_users()

        # Verify appropriate message was printed
        mock_print.assert_called_with(
            "Test users file not found: "
            + str(
                Path(__file__).resolve().parent.parent.parent.parent / "test_users.json"
            )
        )

        # Verify no users were added
        user_count = db.session.scalar(sa.func.count(Researcher.id))
        self.assertEqual(user_count, 0)

    def test_load_test_users_with_existing_data(self):
        """Test loading test users when database already has users"""
        from src.app.cli import load_test_users

        # Add a researcher before running load_test_users
        r = Researcher(researcher_name="existing_user", email="existing@example.com")
        r.set_password("existingpw")
        db.session.add(r)
        db.session.commit()

        # Now try to load test users
        with patch("builtins.print") as mock_print:
            load_test_users()

        # Verify it skipped loading
        mock_print.assert_called_with(
            "Database already contains 1 users. Skipping test user creation."
        )

        # Verify only our original user exists
        users = db.session.scalars(sa.select(Researcher)).all()
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].researcher_name, "existing_user")
