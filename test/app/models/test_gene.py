import unittest
import sqlalchemy as sa
from src.app import create_app, db
from test.app.test_config import TestConfig
from src.app.models.gene import Gene, GeneAnnotation


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
