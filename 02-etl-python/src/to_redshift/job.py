import boto3
import pandas as pd
import redshift_connector

from sql_schema import create_table_sql
from utils import setup_logger

logger = setup_logger()


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

                    ddl = create_table_sql(table_name, df)
                    logger.info(f"Ensuring table exists: {ddl}")
                    cursor.execute(ddl)

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
