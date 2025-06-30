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

# Load initial data
echo "Loading initial gene data..."
flask load-data
if [ $? -ne 0 ]; then
    echo "Warning: Gene data loading failed, but continuing..."
fi

# Load test users
echo "Loading test users..."
flask load-test-users
if [ $? -ne 0 ]; then
    echo "Warning: Test user loading failed, but continuing..."
fi

# Wait for Elasticsearch to be ready before indexing
echo "Waiting for Elasticsearch to be ready..."
ES_READY=false
ES_RETRY_COUNT=0
ES_MAX_RETRIES=30
# Try both hostname and localhost to maximize chances of success
ES_URLS=("http://elasticsearch:9200" "http://localhost:9200")

while [ $ES_RETRY_COUNT -lt $ES_MAX_RETRIES ]; do
    for ES_URL in "${ES_URLS[@]}"; do
        if curl -s -f "${ES_URL}/_cluster/health" > /dev/null 2>&1; then
            echo "Successfully connected to Elasticsearch at ${ES_URL}"
            ES_READY=true
            # Export the working URL so the app uses the correct one
            export ELASTICSEARCH_URL="${ES_URL}"
            break 2
        fi
    done
    
    ES_RETRY_COUNT=$((ES_RETRY_COUNT+1))
    echo "Elasticsearch not ready yet, waiting... ($ES_RETRY_COUNT/$ES_MAX_RETRIES)"
    sleep 10
    
    if [ $ES_RETRY_COUNT -eq $ES_MAX_RETRIES ]; then
        echo "Elasticsearch is not available after maximum retries. Search functionality may be limited."
    fi
done

# Only index posts if Elasticsearch is ready
if [ "$ES_READY" = true ]; then
    echo "Indexing user posts..."
    flask create-search-indices
else
    echo "Skipping post indexing due to Elasticsearch connection failure."
fi

# Start the application
echo "Starting Gunicorn server..."
exec gunicorn -b :5000 --access-logfile - --error-logfile - src.gene_annotator_flask_shell_ctx:app