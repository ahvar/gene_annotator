import unittest
import sqlalchemy as sa
from src.app import create_app, db
from test.app.test_config import TestConfig
from src.app.models.researcher import Researcher
from src.app.models.pipeline_run import PipelineRun, PipelineResult


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
