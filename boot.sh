#!/bin/bash
export PYTHONPATH=/opt/pipeline:$PYTHONPATH

# Inject the DB URL from the secret
#export DATABASE_URL="mysql+pymysql://gene-annotator:${MYSQL_PASSWORD}@mysql/gene_annotator"
export DATABASE_URL="mysql+pymysql://gene-annotator:${MYSQL_PASSWORD}@127.0.0.1:3306/gene_annotator"
# Maximum number of retries
MAX_RETRIES=30
RETRY_COUNT=0

echo "DATABASE_URL: $DATABASE_URL"
echo "MYSQL_PASSWORD set: $(if [ -n "$MYSQL_PASSWORD" ]; then echo "YES"; else echo "NO"; fi)"
echo "Attempting to connect to MySQL..."

echo "Waiting for database to be ready..."

# Try running migrations with retries
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    flask db upgrade
    if [ $? -eq 0 ]; then
        echo "Database migrations completed successfully!"
        echo "Loading initial gene data..."
        flask load-data
        echo "Loading test users..."
        flask load-test-users
        echo "Indexing user posts..."
        flask create-search-indices
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

# Start the application
echo "Starting Gunicorn server..."
exec gunicorn -b :5000 --access-logfile - --error-logfile - src.gene_annotator_flask_shell_ctx:app