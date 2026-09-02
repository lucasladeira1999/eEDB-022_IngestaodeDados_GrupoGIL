FROM apache/airflow:2.10.5-python3.11

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

USER airflow
COPY requirements-dbt.txt /requirements-dbt.txt
COPY requirements-soda.txt /requirements-soda.txt
COPY requirements-openmetadata.txt /requirements-openmetadata.txt

# Cada ferramenta roda em um virtualenv próprio e isolado por conta das dependências de cada
RUN python -m venv /home/airflow/.venv-dbt \
    && /home/airflow/.venv-dbt/bin/pip install --no-cache-dir -r /requirements-dbt.txt

RUN python -m venv /home/airflow/.venv-soda \
    && /home/airflow/.venv-soda/bin/pip install --no-cache-dir -r /requirements-soda.txt

RUN python -m venv /home/airflow/.venv-openmetadata \
    && /home/airflow/.venv-openmetadata/bin/pip install --no-cache-dir -r /requirements-openmetadata.txt