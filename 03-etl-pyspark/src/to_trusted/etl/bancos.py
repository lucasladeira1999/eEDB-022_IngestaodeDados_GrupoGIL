from pyspark.sql import DataFrame
from to_trusted.etl.base import BaseETL
from to_trusted.etl.normalize import normalize_cnpj_udf, normalize_text_udf


class BancosETL(BaseETL):
    name = "bancos"

    def clean_data(self, df: DataFrame) -> DataFrame:
        return df.withColumn("nome_norm", normalize_text_udf(df["nome"])).withColumn(
            "cnpj_norm", normalize_cnpj_udf(df["cnpj"])
        )