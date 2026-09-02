# Orquestra o pipeline da Atividade 4 (ingestao Python + transformacao dbt/DuckDB)

from datetime import datetime
from airflow import DAG
from airflow.operators.bash import BashOperator

DBT_PROJECT_DIR = '/opt/dbt_project'
DBT_VENV = '/home/airflow/.venv-dbt/bin'
SODA_VENV = '/home/airflow/.venv-soda/bin'
OPENMETADATA_VENV = '/home/airflow/.venv-openmetadata/bin'

DBT_CMD = (
    f"cd {DBT_PROJECT_DIR} && {DBT_VENV}/dbt {{cmd}} --project-dir {DBT_PROJECT_DIR} "
    f"--profiles-dir {DBT_PROJECT_DIR} --no-partial-parse"
)

SODA_CONFIG_DIR = '/opt/airflow/soda'
OPENMETADATA_CONFIG_DIR = '/opt/airflow/openmetadata'

default_args = {
    'owner': 'grupo-gil',
    'retries': 0,
}

with DAG(
    dag_id='atividade4_pipeline',
    description='Ingestao (Python) + transformacao (dbt/DuckDB) + qualidade (Soda) + metadados (OpenMetadata)',
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=['atividade5', 'dbt', 'duckdb'],
) as dag:

    ingest_raw = BashOperator(
    task_id='ingest_raw',
    bash_command=(
        f"cd {DBT_PROJECT_DIR} && "
        f"{DBT_VENV}/python scripts/ingest_raw.py"
        ),
    )

    dbt_seed = BashOperator(task_id='dbt_seed', bash_command=DBT_CMD.format(cmd='seed'))
    dbt_run = BashOperator(task_id='dbt_run', bash_command=DBT_CMD.format(cmd='run'))
    dbt_test = BashOperator(task_id='dbt_test', bash_command=DBT_CMD.format(cmd='test'))
    dbt_docs_generate = BashOperator(
        task_id='dbt_docs_generate',
        bash_command=DBT_CMD.format(cmd='docs generate'),
    )

    soda_scan = BashOperator(
        task_id='soda_scan',
        bash_command=(
            f"{SODA_VENV}/soda scan -d duckdb_atividade4 "
            f"-c {SODA_CONFIG_DIR}/configuration.yml "
            f"{SODA_CONFIG_DIR}/checks.yml"
        ),
    )

    openmetadata_create_service = BashOperator(
        task_id='openmetadata_create_service',
        bash_command=f"{OPENMETADATA_VENV}/python {OPENMETADATA_CONFIG_DIR}/create_service.py",
    )
    openmetadata_ingest_dbt = BashOperator(
        task_id='openmetadata_ingest_dbt',
        bash_command=f"{OPENMETADATA_VENV}/metadata ingest -c {OPENMETADATA_CONFIG_DIR}/ingest_dbt.yaml",
    )

    (
        ingest_raw
        >> dbt_seed
        >> dbt_run
        >> dbt_test
        >> dbt_docs_generate
        >> soda_scan
        >> openmetadata_create_service
        >> openmetadata_ingest_dbt
    )
