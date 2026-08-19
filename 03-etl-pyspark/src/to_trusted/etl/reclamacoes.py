from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from to_trusted.etl.base import BaseETL
from to_trusted.etl.normalize import normalize_cnpj_udf, normalize_text_udf

QTY_COLS = [
    "qtd_reclamacoes_reguladas_procedentes",
    "qtd_reclamacoes_reguladas_outras",
    "qtd_reclamacoes_nao_reguladas",
    "qtd_total_reclamacoes",
    "qtd_total_clientes_ccs_e_scr",
    "qtd_clientes_ccs",
    "qtd_clientes_scr",
]


class ReclamacoesETL(BaseETL):
    name = "reclamacoes"

    def clean_data(self, df: DataFrame) -> DataFrame:
        df = df.withColumn("nome_norm", normalize_text_udf(df["instituicao_financeira"]))
        df = df.withColumn("cnpj_norm", normalize_cnpj_udf(df["cnpj_if"]))

        indice_limpo = F.regexp_replace(F.col("indice"), r"\s", "")
        indice_limpo = F.regexp_replace(indice_limpo, r"\.", "")
        indice_limpo = F.regexp_replace(indice_limpo, ",", ".")
        df = df.withColumn("indice", indice_limpo.cast("double"))

        for col in QTY_COLS:
            df = df.withColumn(col, F.col(col).cast("long"))
        return df