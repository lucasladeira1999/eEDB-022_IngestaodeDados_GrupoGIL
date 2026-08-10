from to_trusted.etl.bancos import BancosETL
from to_trusted.etl.empregados import EmpregadosETL
from to_trusted.etl.reclamacoes import ReclamacoesETL
from utils import setup_logger

ETL_JOBS = [BancosETL, EmpregadosETL, ReclamacoesETL]
logger = setup_logger()


class ToTrustedJob:
    def run(**config) -> None:
        for etl_class in ETL_JOBS:
            try:
                logger.info(f"Running ETL job for {etl_class.name}")
                etl_class().run(config["raw_bucket"], config["trusted_bucket"])
            except Exception as e:
                logger.error(
                    f"Error running ETL job for {etl_class.name}: {e.with_traceback()}"
                )
