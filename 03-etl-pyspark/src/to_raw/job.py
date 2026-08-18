from __future__ import annotations
import os
from utils import setup_logger, write_table
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F


logger = setup_logger()


DADOS_DIR = os.environ.get("DADOS_DIR", "/dados")

BANCOS_COLS = ["segmento", "cnpj", "nome"]

EMPREGADOS_COLS_BASE = [
    "employer_name", "reviews_count", "culture_count", "salaries_count", "benefits_count", "employer_website", "employer_headquarters", "employer_founded", "employer_industry", "employer_revenue", "url", "geral", "cultura_e_valores", "diversidade_e_inclusao", "qualidade_de_vida", "alta_lideranca", "remuneracao_e_beneficios", "oportunidades_de_carreira", "recomendam_pct", "perspectiva_pct"
]

RECLAMACOES_COLS = [
    "ano", "trimestre", "categoria", "tipo", "cnpj_if", "instituicao_financeira", "indice", "qtd_reclamacoes_reguladas_procedentes", "qtd_reclamacoes_reguladas_outras", "qtd_reclamacoes_nao_reguladas", "qtd_total_reclamacoes", "qtd_total_clientes_ccs_e_scr", "qtd_clientes_ccs", "qtd_clientes_scr"
]


def _read_csv(spark, path: str, sep: str, encoding="UTF-8") -> DataFrame:
    return (
        spark.read.option("header", True)
        .option("sep", sep)
        .option("encoding", encoding)
        .csv(path)
    )


def _rename_by_position(df: DataFrame, canonical_cols: list[str]) -> DataFrame:
    # os headers reais dos CSVs variam/tem coluna fantasma no final (ex: ";" sobrando);
    # por isso pegamos so as N primeiras colunas, na ordem, e renomeamos.
    cols = df.columns[: len(canonical_cols)]
    return df.select(*cols).toDF(*canonical_cols)


def _read_bancos(spark) -> DataFrame:
    df = _read_csv(spark, f"{DADOS_DIR}/Bancos/EnquadramentoInicia_v2.tsv", sep="\t")
    return _rename_by_position(df, BANCOS_COLS)


def _read_empregados(spark) -> DataFrame:
    emp_v2 = _rename_by_position(
        _read_csv(spark, f"{DADOS_DIR}/Empregados/glassdoor_consolidado_join_match_v2.csv", sep="|"),
        EMPREGADOS_COLS_BASE + ["segmento", "nome", "match_percent"],
    ).withColumn("cnpj", F.lit(None).cast("string")).withColumn("origem", F.lit("match_v2"))

    emp_less = _rename_by_position(
        _read_csv(spark, f"{DADOS_DIR}/Empregados/glassdoor_consolidado_join_match_less_v2.csv", sep="|"),
        EMPREGADOS_COLS_BASE + ["cnpj", "nome", "match_percent"],
    ).withColumn("segmento", F.lit(None).cast("string")).withColumn("origem", F.lit("match_less"))

    return emp_v2.unionByName(emp_less)


def _read_reclamacoes(spark) -> DataFrame:
    pasta = f"{DADOS_DIR}/Reclamacoes"
    arquivos = sorted(
        nome for nome in os.listdir(pasta)
        if nome.endswith(".csv") and "nao_ha_dados" not in nome
    )

    dfs = []
    for nome_arquivo in arquivos:
        df = _rename_by_position(
            _read_csv(spark, f"{pasta}/{nome_arquivo}", sep=";", encoding="ISO-8859-1"),
            RECLAMACOES_COLS,
        ).withColumn("origem_arquivo", F.lit(nome_arquivo))
        dfs.append(df)

    resultado = dfs[0]
    for df in dfs[1:]:
        resultado = resultado.unionByName(df)
    return resultado


def run(spark) -> None:
    write_table(_read_bancos(spark), "raw", "bancos")
    write_table(_read_empregados(spark), "raw", "empregados")
    write_table(_read_reclamacoes(spark), "raw", "reclamacoes")