#!/bin/bash
export PYTHONPATH=/opt/pipeline:$PYTHONPATH

# Inject the DB URL from the secret
export DATABASE_URL="mysql+pymysql://gene-annotator:${MYSQL_PASSWORD}@127.0.0.1:3306/gene_annotator"
export GENE_DATA_PATH=/opt/pipeline/src/etl/data
# Maximum number of retries
MAX_RETRIES=30
RETRY_COUNT=0

echo "Waiting for database to be ready..."

# Try running migrations with retries
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    flask db upgrade
    if [ $? -eq 0 ]; then
        echo "Database migrations completed successfully!"
        break
    fi
    
    RETRY_COUNT=$((RETRY_COUNT+1))
    echo "Database not ready, retrying in 5 seconds... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 5
    
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo "Failed to connect to database after $MAX_RETRIES attempts. Exiting."
        exit 1
    fi
done

# Check if data files exist
echo "Checking data file existence..."
if [ ! -d "$GENE_DATA_PATH" ]; then
    echo "ERROR: Data directory $GENE_DATA_PATH does not exist!"
    ls -la /opt/pipeline/src/etl/
    exit 1
fi

echo "Data directory contents:"
ls -la $GENE_DATA_PATH

# Preload gene and annotation data
echo "Checking if gene data needs to be loaded..."
python -c "
from src.app import create_app, db
import sqlalchemy as sa
from src.app.models.gene import Gene, GeneAnnotation
import pandas as pd
import os
from pathlib import Path
import sys
import traceback

try:
    # Create app context
    print('Creating Flask app...')
    app = create_app()
    
    with app.app_context():
        # Check if data already exists
        gene_count = db.session.scalar(sa.func.count(Gene.id))
        print(f'Current gene count: {gene_count}')
        
        if gene_count == 0:
            print('Gene table empty. Loading data directly...')
            
            # Get data directory
            data_dir = Path(os.environ.get('GENE_DATA_PATH', '/opt/pipeline/src/etl/data'))
            print(f'Data directory: {data_dir}')
            
            # Check for data files
            genes_file = data_dir / 'genes.csv'
            annotations_file = data_dir / 'gene_annotations.tsv'
            
            if not genes_file.exists() or not annotations_file.exists():
                files = list(data_dir.glob('*')) if data_dir.exists() else []
                print(f'Files in directory: {[f.name for f in files]}')
                raise FileNotFoundError(f'Missing required data files in {data_dir}')
            
            print(f'Loading genes from {genes_file}...')
            genes_df = pd.read_csv(genes_file)
            
            print(f'Loading annotations from {annotations_file}...')
            annotations_df = pd.read_csv(annotations_file, delimiter='\\t')
            
            # Load genes
            genes_added = 0
            for _, row in genes_df.iterrows():
                gene = Gene(
                    gene_stable_id=row['gene_stable_id'],
                    gene_type=row.get('gene_type'),
                    gene_name=row.get('gene_name'),
                    hgnc_name=row.get('hgnc_name'),
                    hgnc_id=row.get('hgnc_id'),
                    hgnc_id_exists=bool(row.get('hgnc_id'))
                )
                db.session.add(gene)
                genes_added += 1
                
                # Commit in batches to avoid memory issues
                if genes_added % 1000 == 0:
                    db.session.commit()
                    print(f'Loaded {genes_added} genes so far...')
            
            # Commit any remaining genes
            db.session.commit()
            
            # Load annotations
            annotations_added = 0
            for _, row in annotations_df.iterrows():
                annotation = GeneAnnotation(
                    gene_stable_id=row['gene_stable_id'],
                    hgnc_id=row.get('hgnc_id'),
                    panther_id=row.get('panther_id'),
                    tigrfam_id=row.get('tigrfam_id'),
                    wikigene_name=row.get('wikigene_name'),
                    gene_description=row.get('gene_description')
                )
                db.session.add(annotation)
                annotations_added += 1
                
                # Commit in batches
                if annotations_added % 1000 == 0:
                    db.session.commit()
                    print(f'Loaded {annotations_added} annotations so far...')
            
            # Final commit
            db.session.commit()
            
            print(f'Successfully loaded {genes_added} genes and {annotations_added} annotations')
        else:
            print(f'Gene table already contains {gene_count} records. Skipping data load.')
except Exception as e:
    print(f'ERROR: Failed to load gene data: {str(e)}')
    traceback.print_exc()
    sys.exit(1)
"

# Check if the Python script exited with an error
if [ $? -ne 0 ]; then
    echo "ERROR: Gene data loading failed. Exiting."
    exit 1
fi

# Start the application
echo "Starting Gunicorn server..."
exec gunicorn -b :5000 --access-logfile - --error-logfile - src.gene_annotator_flask_shell_ctx:app