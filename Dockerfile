FROM public.ecr.aws/docker/library/python:slim

# Set environment variables
ENV PYTHONPATH=/opt/pipeline:/opt/pipeline/src:/opt/pipeline/src/etl:/opt/pipeline/src/utils:/opt/pipeline/src/etl/data:/opt/pipeline/src/workflows:/opt/pipeline/src/modules:/opt/pipeline/test:/opt/pipeline/test/utils:/opt/pipeline/src/app:/opt/pipeline/src/app/models
ENV PATH=/opt/pipeline/:$PATH

# Set working directory in container
WORKDIR /opt/pipeline

# Copy the requirements file into the container
COPY ./requirements.txt /opt/pipeline

# Upgrade pip and install required packages
RUN pip install --upgrade pip && pip install -r requirements.txt
RUN pip install gunicorn pymysql cryptography

# Copy the entire project into the container
COPY ./src ./src/
COPY migrations/ ./migrations
COPY boot.sh .flaskenv ./
COPY gene_annotate /opt/pipeline/
COPY test/ ./test/
RUN chmod a+x boot.sh

# Make the pipeline script executable and create a symlink
RUN chmod +x ./boot.sh /opt/pipeline/gene_annotate && ln -s /opt/pipeline/gene_annotate /usr/local/bin/gene_annotate
ENV FLASK_APP=src.gene_annotator_flask_shell_ctx
RUN flask translate compile

EXPOSE 5000
ENTRYPOINT ["./boot.sh"]
