#!/usr/bin/env python
from datetime import datetime, timezone, timedelta
import unittest
from unittest.mock import patch, MagicMock
import sqlalchemy as sa
from src.app import create_app, db
from src.app.models.researcher import Researcher, Post
from src.app.models.gene import Gene, GeneAnnotation
from src.app.models.pipeline_run import PipelineResult, PipelineRun
from src.app.auth.email_service import send_password_reset_email
from src.config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SECRET_KEY = "test-secret-key"
    WTF_CSRF_ENABLED = False

    # Email settings (set to non-functional values for testing)
    MAIL_SERVER = "localhost"
    MAIL_PORT = 25
    MAIL_USE_TLS = False
    MAIL_USERNAME = None
    MAIL_PASSWORD = None

    # Translation service
    MS_TRANSLATOR_KEY = "dummy-key"

    # Disable error emails during testing
    ADMINS = []

    # Set small page sizes to test pagination with fewer records
    POSTS_PER_PAGE = 3
    GENES_PER_PAGE = 5
    RUNS_PER_PAGE = 3


class MockElasticsearch:
    def index(self, *args, **kwargs):
        return True

    def search(self, *args, **kwargs):
        return {"hits": {"total": {"value": 0}, "hits": []}}

    def delete(self, *args, **kwargs):
        return True

    @classmethod
    def reindex(cls):
        pass


def mock_reindex():
    pass


add_to_index_patch = patch("src.app.search.add_to_index", lambda *args, **kwrgs: None)
remove_from_index_patch = patch(
    "src.app.search.remove_from_index", lambda *args, **kwargs: None
)


class TestResearcherModel(unittest.TestCase):
    def setUp(self):
        add_to_index_patch.start()
        remove_from_index_patch.start()
        es_constructor = patch(
            "src.app.__init__.Elasticsearch", return_value=MockElasticsearch
        )
        self.mock_es = es_constructor.start()
        reindex_patcher = patch(
            "src.app.models.searchable.SearchableMixin.reindex", mock_reindex
        )
        self.mock_reindex = reindex_patcher.start()
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

        self.es_patcher.stop()
        self.reindex_patcher.stop()

    def test_password_hashing(self):
        r = Researcher(researcher_name="susan", email="susan@example.com")
        r.set_password("cat")
        self.assertFalse(r.check_password("dog"))
        self.assertTrue(r.check_password("cat"))

    def test_avatar(self):
        r = Researcher(researcher_name="john", email="john@example.com")
        self.assertEqual(
            r.avatar(128),
            (
                "https://www.gravatar.com/avatar/"
                "d4c74594d841139328695756648b6bd6"
                "?d=identicon&s=128"
            ),
        )

    def test_follow(self):
        r1 = Researcher(researcher_name="john", email="john@example.com")
        r2 = Researcher(researcher_name="susan", email="susan@example.com")
        db.session.add(r1)
        db.session.add(r2)
        db.session.commit()
        following = db.session.scalars(r1.following.select()).all()
        followers = db.session.scalars(r2.followers.select()).all()
        self.assertEqual(following, [])
        self.assertEqual(followers, [])

        r1.follow(r2)
        db.session.commit()
        self.assertTrue(r1.is_following(r2))
        self.assertEqual(r1.following_count(), 1)
        self.assertEqual(r2.followers_count(), 1)
        u1_following = db.session.scalars(r1.following.select()).all()
        u2_followers = db.session.scalars(r2.followers.select()).all()
        self.assertEqual(u1_following[0].researcher_name, "susan")
        self.assertEqual(u2_followers[0].researcher_name, "john")

        r1.unfollow(r2)
        db.session.commit()
        self.assertFalse(r1.is_following(r2))
        self.assertEqual(r1.following_count(), 0)
        self.assertEqual(r2.followers_count(), 0)

    def test_follow_posts(self):
        # create four users
        r1 = Researcher(researcher_name="john", email="john@example.com")
        r2 = Researcher(researcher_name="susan", email="susan@example.com")
        r3 = Researcher(researcher_name="mary", email="mary@example.com")
        r4 = Researcher(researcher_name="david", email="david@example.com")
        db.session.add_all([r1, r2, r3, r4])

        # create four posts
        now = datetime.now(timezone.utc)
        p1 = Post(
            body="post from john", author=r1, timestamp=now + timedelta(seconds=1)
        )
        p2 = Post(
            body="post from susan", author=r2, timestamp=now + timedelta(seconds=4)
        )
        p3 = Post(
            body="post from mary", author=r3, timestamp=now + timedelta(seconds=3)
        )
        p4 = Post(
            body="post from david", author=r4, timestamp=now + timedelta(seconds=2)
        )
        db.session.add_all([p1, p2, p3, p4])
        db.session.commit()

        # setup the followers
        r1.follow(r2)  # john follows susan
        r1.follow(r4)  # john follows david
        r2.follow(r3)  # susan follows mary
        r3.follow(r4)  # mary follows david
        db.session.commit()

        # check the following posts of each user
        f1 = db.session.scalars(r1.following_posts()).all()
        f2 = db.session.scalars(r2.following_posts()).all()
        f3 = db.session.scalars(r3.following_posts()).all()
        f4 = db.session.scalars(r4.following_posts()).all()
        self.assertEqual(f1, [p2, p4, p1])
        self.assertEqual(f2, [p2, p3])
        self.assertEqual(f3, [p3, p4])
        self.assertEqual(f4, [p4])


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
