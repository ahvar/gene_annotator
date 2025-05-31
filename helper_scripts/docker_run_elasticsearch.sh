docker run --name elasticsearch -d --rm -p 9200:9200 \
    -e discovery.type=single-node -e xpack.security.enabled=false \
    --network gene-annotator-network \
    -t docker.elastic.co/elasticsearch/elasticsearch:8.11.1