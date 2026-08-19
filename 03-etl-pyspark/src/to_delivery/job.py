from __future__ import annotations
import os
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from rapidfuzz import fuzz, process
from to_delivery.acronyms import resolve_acronym
from utils import read_parquet, write_parquet, write_table, setup_logger

logger = setup_logger()

TRUSTED_SCHEMA = os.environ.get("TRUSTED_SCHEMA", "trusted")
DELIVERY_SCHEMA = os.environ.get("DELIVERY_SCHEMA", "delivery")
DELIVERY_TABLE = os.environ.get("DELIVERY_TABLE", "bancos_indicadores")

FUZZY_SCORE_CUTOFF_RECLAMACOES = int(os.environ.get("FUZZY_SCORE_CUTOFF_RECLAMACOES", "80"))
FUZZY_SCORE_CUTOFF_EMPREGADOS = int(os.environ.get("FUZZY_SCORE_CUTOFF_EMPREGADOS", "90"))

FINAL_COLUMNS = [
    "segmento", "cnpj", "nome", "cnpj_norm", "nome_norm", "qtd_total_reclamacoes", "qtd_procedentes", "indice_medio", "trimestres_com_reclamacao", "nota_geral", "nota_cultura", "nota_diversidade", "nota_qualidade_vida", "nota_lideranca", "nota_remuneracao", "nota_carreira", "pct_recomendam", "pct_perspectiva"
]

RATING_MAP = {
    "geral": "nota_geral",
    "cultura_e_valores": "nota_cultura",
    "diversidade_e_inclusao": "nota_diversidade",
    "qualidade_de_vida": "nota_qualidade_vida",
    "alta_lideranca": "nota_lideranca",
    "remuneracao_e_beneficios": "nota_remuneracao",
    "oportunidades_de_carreira": "nota_carreira",
    "recomendam_pct": "pct_recomendam",
    "perspectiva_pct": "pct_perspectiva",
}


def _dedup_por_cnpj(df: DataFrame) -> DataFrame:
    tem_cnpj = (F.col("cnpj_norm").isNotNull()) & (F.col("cnpj_norm") != "")
    com_cnpj = df.filter(tem_cnpj).dropDuplicates(["cnpj_norm"])
    sem_cnpj = df.filter(~tem_cnpj).dropDuplicates(["nome_norm"])
    return com_cnpj.unionByName(sem_cnpj)


def _agrega_reclamacoes(reclamacoes: DataFrame, coluna_chave: str, prefixo: str) -> DataFrame:
    return (
        reclamacoes
        .filter(F.col(coluna_chave).isNotNull() & (F.col(coluna_chave) != ""))
        .groupBy(coluna_chave)
        .agg(
            F.sum("qtd_total_reclamacoes").alias(f"{prefixo}_qtd_total"),
            F.sum("qtd_reclamacoes_reguladas_procedentes").alias(f"{prefixo}_qtd_procedentes"),
            F.avg("indice").alias(f"{prefixo}_indice_medio"),
            F.count(F.lit(1)).alias(f"{prefixo}_trimestres"),
        )
    )


def _fuzzy_lookup(spark, nomes_sem_match: list[str], nomes_candidatos: list[str], score_cutoff: int) -> DataFrame:
    schema = "nome_norm string, nome_norm_candidato string"
    if not nomes_sem_match or not nomes_candidatos:
        return spark.createDataFrame([], schema=schema)

    candidatos_disponiveis = {resolve_acronym(nome): nome for nome in nomes_candidatos}
    linhas = []
    for nome in nomes_sem_match:
        resolvido = resolve_acronym(nome)
        candidato = candidatos_disponiveis.pop(resolvido, None)
        if candidato is None:
            melhor = process.extractOne(
                resolvido,
                list(candidatos_disponiveis.keys()),
                scorer=fuzz.WRatio,
                score_cutoff=score_cutoff,
            )
            if melhor:
                candidato = candidatos_disponiveis.pop(melhor[0])
        if candidato is not None:
            linhas.append((nome, candidato))

    return spark.createDataFrame(linhas, schema=schema)


def _completa_com_fuzzy(spark, df: DataFrame, coluna_indicador: str, candidatos: DataFrame, colunas_metricas: list[str], score_cutoff: int) -> DataFrame:
    sem_match = [
        linha["nome_norm"]
        for linha in df.filter(F.col(coluna_indicador).isNull()).select("nome_norm").collect()
    ]
    if not sem_match:
        return df

    candidatos_nomes = [linha["nome_norm"] for linha in candidatos.select("nome_norm").collect()]
    mapa = _fuzzy_lookup(spark, sem_match, candidatos_nomes, score_cutoff)
    if not mapa.take(1):
        return df

    candidatos_renomeado = candidatos.withColumnRenamed("nome_norm", "nome_norm_candidato")
    for coluna in colunas_metricas:
        candidatos_renomeado = candidatos_renomeado.withColumnRenamed(coluna, f"fuzzy_{coluna}")

    fuzzy_metricas = (
        mapa.join(candidatos_renomeado, on="nome_norm_candidato", how="inner")
        .drop("nome_norm_candidato")
    )

    df = df.join(fuzzy_metricas, on="nome_norm", how="left")
    for coluna in colunas_metricas:
        df = df.withColumn(coluna, F.coalesce(F.col(coluna), F.col(f"fuzzy_{coluna}")))
        df = df.drop(f"fuzzy_{coluna}")
    return df


def run(spark) -> None:
    bancos = _dedup_por_cnpj(read_parquet(spark, TRUSTED_SCHEMA, "bancos"))
    reclamacoes = read_parquet(spark, TRUSTED_SCHEMA, "reclamacoes")
    empregados = _dedup_por_cnpj(read_parquet(spark, TRUSTED_SCHEMA, "empregados"))

    por_cnpj = _agrega_reclamacoes(reclamacoes, "cnpj_norm", "c")
    por_nome = _agrega_reclamacoes(reclamacoes, "nome_norm", "n")

    df = bancos.join(por_cnpj, on="cnpj_norm", how="left")
    df = df.join(por_nome, on="nome_norm", how="left")

    df = (
        df
        .withColumn("qtd_total_reclamacoes", F.coalesce("c_qtd_total", "n_qtd_total"))
        .withColumn("qtd_procedentes", F.coalesce("c_qtd_procedentes", "n_qtd_procedentes"))
        .withColumn("indice_medio", F.coalesce("c_indice_medio", "n_indice_medio"))
        .withColumn("trimestres_com_reclamacao", F.coalesce("c_trimestres", "n_trimestres"))
    )

    por_nome_final = (
        por_nome
        .withColumnRenamed("n_qtd_total", "qtd_total_reclamacoes")
        .withColumnRenamed("n_qtd_procedentes", "qtd_procedentes")
        .withColumnRenamed("n_indice_medio", "indice_medio")
        .withColumnRenamed("n_trimestres", "trimestres_com_reclamacao")
    )
    df = _completa_com_fuzzy(
        spark, df, "qtd_total_reclamacoes", por_nome_final,
        ["qtd_total_reclamacoes", "qtd_procedentes", "indice_medio", "trimestres_com_reclamacao"],
        score_cutoff=FUZZY_SCORE_CUTOFF_RECLAMACOES,
    )

    empregados_selecionado = empregados.select("nome_norm", *RATING_MAP.keys())
    df = df.join(empregados_selecionado, on="nome_norm", how="left")

    df = _completa_com_fuzzy(
        spark, df, "geral", empregados_selecionado, list(RATING_MAP.keys()),
        score_cutoff=FUZZY_SCORE_CUTOFF_EMPREGADOS,
    )

    for origem, destino in RATING_MAP.items():
        df = df.withColumnRenamed(origem, destino)

    banco_final = df.select(*FINAL_COLUMNS)

    logger.info("Saving delivery data as Parquet")
    write_parquet(banco_final, DELIVERY_SCHEMA, DELIVERY_TABLE)

    logger.info(f"Saving {DELIVERY_SCHEMA}.{DELIVERY_TABLE} as the final table in Postgres")
    write_table(banco_final, DELIVERY_SCHEMA, DELIVERY_TABLE)
