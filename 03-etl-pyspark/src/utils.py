import logging
import yaml
import os
from pyspark.sql import DataFrame, SparkSession

def setup_logger() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(filename)s - %(levelname)s - %(message)s",
    )
    logging.getLogger().handlers[0].formatter.default_msec_format = "%s.%03d"
    return logging.getLogger()


def load_config(config_path: str) -> dict:
    with open(config_path, "r") as config_file:
        return yaml.safe_load(config_file)


def get_spark_session(app_name: str):
    return SparkSession.builder.appName(app_name).getOrCreate()


def _jdbc_url() -> str:
    host = os.environ["PG_HOST"]
    port = os.environ.get("PG_PORT", "5432")
    database = os.environ["PG_DB"]
    return f"jdbc:postgresql://{host}:{port}/{database}"


def _jdbc_properties() -> dict:
    return {
        "user": os.environ["PG_USER"],
        "password": os.environ["PG_PASSWORD"],
        "driver": "org.postgresql.Driver",
    }


def read_table(spark, schema: str, table: str) -> DataFrame:
    return spark.read.jdbc(url=_jdbc_url(), table=f"{schema}.{table}", properties=_jdbc_properties())


def write_table(df: DataFrame, schema: str, table: str) -> None:
    df.write.jdbc(
        url=_jdbc_url(),
        table=f"{schema}.{table}",
        mode="overwrite",
        properties=_jdbc_properties(),
    )