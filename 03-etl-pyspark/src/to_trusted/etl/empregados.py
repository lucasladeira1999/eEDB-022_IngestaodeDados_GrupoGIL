from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from to_trusted.etl.base import BaseETL
from to_trusted.etl.normalize import normalize_cnpj_udf, normalize_text_udf

RATING_COLS = [
    "geral",
    "cultura_e_valores",
    "diversidade_e_inclusao",
    "qualidade_de_vida",
    "alta_lideranca",
    "remuneracao_e_beneficios",
    "oportunidades_de_carreira",
    "recomendam_pct",
    "perspectiva_pct",
]


class EmpregadosETL(BaseETL):
    name = "empregados"

    def clean_data(self, df: DataFrame) -> DataFrame:
        df = df.withColumn("nome_norm", normalize_text_udf(df["nome"]))
        df = df.withColumn(
            "cnpj_norm",
            F.when(df["cnpj"].isNotNull(), normalize_cnpj_udf(df["cnpj"])).otherwise(F.lit("")),
        )
        for col in RATING_COLS:
            df = df.withColumn(col, F.col(col).cast("double"))
        return df