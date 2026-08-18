from pyspark.sql import SparkSession
from to_trusted.etl.bancos import BancosETL
from to_trusted.etl.empregados import EmpregadosETL
from to_trusted.etl.reclamacoes import ReclamacoesETL
from utils import setup_logger

ETL_JOBS = [BancosETL, EmpregadosETL, ReclamacoesETL]
logger = setup_logger()


def run(spark: SparkSession) -> None:
    for etl_class in ETL_JOBS:
        logger.info(f"Running ETL job for {etl_class.name}")
        etl_class().run(spark)