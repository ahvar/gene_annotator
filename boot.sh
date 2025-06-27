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
from src.app.main.routes import load_gene_and_annotation_data
import sys
import traceback

try:
    app = create_app()
    with app.app_context():
        gene_count = db.session.scalar(sa.func.count(Gene.id))
        if gene_count == 0:
            print('Gene table empty. Preloading gene and annotation data...')
            genes, annotations = load_gene_and_annotation_data()
            if genes == 0 or annotations == 0:
                print('ERROR: Failed to load data - zero records loaded')
                sys.exit(1)
            print(f'Preloaded {genes} genes and {annotations} annotations')
        else:
            print(f'Gene table already contains {gene_count} records. Skipping preload.')
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