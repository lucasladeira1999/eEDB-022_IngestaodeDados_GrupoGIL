from __future__ import annotations
import os
from utils import setup_logger, write_table
from pyspark.sql import DataFrame
from pyspark.sql import functions as F


logger = setup_logger()


DADOS_DIR = os.environ.get("DADOS_DIR", "/dados")
RAW_SCHEMA = os.environ.get("RAW_SCHEMA", "raw")


def _read_csv(spark, path: str, sep: str, encoding="UTF-8") -> DataFrame:
    df = (
        spark.read.option("header", True)
        .option("sep", sep)
        .option("encoding", encoding)
        .csv(path)
    )
    return df.select(*[c for c in df.columns if c != ""])


def _read_bancos(spark) -> DataFrame:
    return _read_csv(spark, f"{DADOS_DIR}/Bancos/EnquadramentoInicia_v2.tsv", sep="\t")


def _read_empregados(spark) -> DataFrame:
    # match_v2 tem Segmento no final, match_less_v2 tem CNPJ no lugar - unionByName com
    # allowMissingColumns preenche a coluna ausente de cada lado com null, sem renomear nada.
    emp_v2 = _read_csv(spark, f"{DADOS_DIR}/Empregados/glassdoor_consolidado_join_match_v2.csv", sep="|")
    emp_less = _read_csv(spark, f"{DADOS_DIR}/Empregados/glassdoor_consolidado_join_match_less_v2.csv", sep="|")
    return emp_v2.unionByName(emp_less, allowMissingColumns=True)


def _read_reclamacoes(spark) -> DataFrame:
    pasta = f"{DADOS_DIR}/Reclamacoes"
    arquivos = sorted(
        nome for nome in os.listdir(pasta)
        if nome.endswith(".csv") and "nao_ha_dados" not in nome
    )

    dfs = [
        _read_csv(spark, f"{pasta}/{nome}", sep=";", encoding="ISO-8859-1").withColumn(
            "origem_arquivo", F.lit(nome)
        )
        for nome in arquivos
    ]

    resultado = dfs[0]
    for df in dfs[1:]:
        resultado = resultado.unionByName(df)
    return resultado


def run(spark) -> None:
    write_table(_read_bancos(spark), RAW_SCHEMA, "bancos")
    write_table(_read_empregados(spark), RAW_SCHEMA, "empregados")
    write_table(_read_reclamacoes(spark), RAW_SCHEMA, "reclamacoes")
