import boto3
import pandas as pd
import redshift_connector
from utils import setup_logger

logger = setup_logger()

DTYPE_TO_REDSHIFT = {
    "int64": "BIGINT",
    "int32": "INTEGER",
    "float64": "DOUBLE PRECISION",
    "float32": "REAL",
    "bool": "BOOLEAN",
    "datetime64[ns]": "TIMESTAMP",
}


def build_create_table_sql(table_name: str, df: pd.DataFrame) -> str:
    columns = ", ".join(
        f'"{col}" {DTYPE_TO_REDSHIFT.get(str(dtype), "VARCHAR(65535)")}'
        for col, dtype in df.dtypes.items()
    )
    create_sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({columns})'
    print(f"Generated CREATE TABLE SQL: {create_sql}")
    return create_sql


class ToRedshiftJob:
    def run(**config) -> None:
        logger.info(f"Running ToRedshiftJob with config: {config}")
        s3_client = boto3.client("s3")
        delivery_bucket = config["delivery_bucket"]

        conn = redshift_connector.connect(
            host=config["redshift_host"],
            port=config.get("redshift_port", 5439),
            database=config["redshift_database"],
            user=config["redshift_user"],
            password=config["redshift_password"],
        )
        conn.autocommit = True
        cursor = conn.cursor()

        try:
            paginator = s3_client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=delivery_bucket):
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    if not key.endswith(".parquet"):
                        continue

                    table_name = key.rsplit("/", 1)[-1][: -len(".parquet")]
                    logger.info(f"Loading {key} into Redshift table {table_name}")

                    df = pd.read_parquet(f"s3://{delivery_bucket}/{key}")

                    create_table_sql = build_create_table_sql(table_name, df)
                    logger.info(f"Ensuring table exists: {create_table_sql}")
                    cursor.execute(create_table_sql)

                    copy_sql = (
                        f'COPY "{table_name}" '
                        f"FROM 's3://{delivery_bucket}/{key}' "
                        f"IAM_ROLE '{config['redshift_iam_role']}' "
                        "FORMAT AS PARQUET"
                    )
                    logger.info(f"Inserting {len(df)} records into {table_name}")
                    cursor.execute(copy_sql)
        finally:
            cursor.close()
            conn.close()
