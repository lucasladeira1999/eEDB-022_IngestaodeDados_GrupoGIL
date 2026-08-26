FROM python:3.12-slim

WORKDIR /app

# Install system utilities if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
RUN pip install --no-cache-dir \
    dbt-duckdb \
    duckdb \
    pandas \
    pyarrow \
    python-dotenv

# Copy project files
COPY . /app

# Ensure executable scripts
ENV PYTHONUNBUFFERED=1

CMD ["python", "scripts/run_pipeline.py"]
