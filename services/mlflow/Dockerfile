FROM ghcr.io/mlflow/mlflow:v3.11.1

USER root

# Install dependencies needed for PostgreSQL and S3
RUN pip install --no-cache-dir psycopg2-binary boto3

# Switch back to the mlflow default user (if any, default image may run as root or non-root)
# We can just leave it as root or not depending on the base image. Let's just switch back to 1000 if it was non-root.
# Actually, pip install works as root, and then we just use the default entrypoint.
