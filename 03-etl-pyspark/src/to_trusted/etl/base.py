from abc import ABC, abstractmethod
from pyspark.sql import DataFrame
from utils import read_table, setup_logger, write_parquet

logger = setup_logger()


class BaseETL(ABC):
    name: str

    def get_data(self, spark) -> DataFrame:
        logger.info(f"Loading raw data for {self.name}")
        return read_table(spark, "raw", self.name)

    @abstractmethod
    def clean_data(self, df: DataFrame) -> DataFrame:
        raise NotImplementedError

    def save_data(self, df: DataFrame) -> None:
        logger.info(f"Saving trusted data for {self.name} as Parquet")
        write_parquet(df, "trusted", self.name)

    def run(self, spark) -> None:
        df = self.get_data(spark)
        df = self.clean_data(df)
        self.save_data(df)