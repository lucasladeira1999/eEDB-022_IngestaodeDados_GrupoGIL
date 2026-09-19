"""Consumidor: job PySpark Structured Streaming.

A cada janela lê o que chegou no Kafka, trata (camada trusted), faz UMA consulta ao
Postgres para buscar o cadastro de bancos e junta (camada delivery). Ambas gravadas
em Parquet no disco local.

Diferença para a atividade 07: lá o enriquecimento era uma consulta por mensagem;
aqui é uma consulta por janela e um JOIN do lote inteiro, como o enunciado pede.
"""

import os

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructField, StructType
from rapidfuzz import fuzz, process

from utils import (
    CADASTRO_SCHEMA,
    CADASTRO_TABELA,
    KAFKA_BOOTSTRAP,
    KAFKA_TOPIC,
    camada,
    jdbc_properties,
    jdbc_url,
    normalize_cnpj,
    normalize_text,
    resolve_acronym,
    schema,
    setup_logger,
)

logger = setup_logger()

JANELA_SEGUNDOS = os.environ.get("JANELA_SEGUNDOS", "10")
FUZZY_SCORE_CUTOFF = int(os.environ.get("FUZZY_SCORE_CUTOFF", "80"))

# tudo chega como texto do CSV; a conversão de tipo é trabalho da camada trusted
COLUNAS_MENSAGEM = schema("reclamacoes", "colunas_origem") + schema("reclamacoes", "metadados")
SCHEMA = StructType([StructField(coluna, StringType()) for coluna in COLUNAS_MENSAGEM])

normalize_text_udf = F.udf(normalize_text, StringType())
normalize_cnpj_udf = F.udf(normalize_cnpj, StringType())
resolve_acronym_udf = F.udf(resolve_acronym, StringType())


def _trata(df: DataFrame) -> DataFrame:
    df = (
        df.withColumn("nome_norm", normalize_text_udf("instituicao_financeira"))
        .withColumn("cnpj_norm", normalize_cnpj_udf("cnpj_if"))
        # o trimestre vem como "1º"
        .withColumn("ano", F.regexp_replace("ano", r"\D", "").cast("int"))
        .withColumn("trimestre", F.regexp_replace("trimestre", r"\D", "").cast("int"))
    )

    # índice no formato brasileiro: "14.015,05" -> 14015.05
    indice = F.regexp_replace("indice", r"\s", "")
    indice = F.regexp_replace(indice, r"\.", "")
    indice = F.regexp_replace(indice, ",", ".")
    df = df.withColumn("indice", indice.cast("double"))

    for coluna in schema("reclamacoes", "quantidades"):
        df = df.withColumn(coluna, F.regexp_replace(coluna, r"\D", "").cast("long"))

    # CNPJ vazio vira nulo: o cadastro tem banco com CNPJ "0", que normaliza pra
    # vazio e casaria com toda reclamação sem CNPJ
    df = df.withColumn("cnpj_norm", F.when(F.col("cnpj_norm") != "", F.col("cnpj_norm")))
    return df.withColumn("nome_resolvido", resolve_acronym_udf("nome_norm"))


def _le_cadastro(spark: SparkSession) -> DataFrame:
    """A solicitação ao banco SQL: uma por janela, não por mensagem."""
    return spark.read.jdbc(
        url=jdbc_url(),
        table=f"{CADASTRO_SCHEMA}.{CADASTRO_TABELA}",
        properties=jdbc_properties(),
    )


def _junta_por(janela: DataFrame, bancos: DataFrame, chave: str, sufixo: str) -> DataFrame:
    lado = (
        bancos.filter(F.col(chave).isNotNull() & (F.col(chave) != ""))
        .select(
            F.col(chave),
            F.col("segmento").alias(f"seg_{sufixo}"),
            F.col("nome").alias(f"nome_{sufixo}"),
        )
        .dropDuplicates([chave])
    )
    return janela.join(lado, on=chave, how="left")


def _fuzzy(janela: DataFrame, bancos: DataFrame) -> DataFrame:
    """Último recurso: nome parecido, para o que não casou por chave nenhuma."""
    sem_match = [
        linha["nome_norm"]
        for linha in janela.filter(F.col("segmento").isNull())
        .select("nome_norm")
        .distinct()
        .collect()
        if linha["nome_norm"]
    ]
    if not sem_match:
        return janela

    # sem pop: várias reclamações (trimestres diferentes) apontam para o mesmo banco
    candidatos = {
        linha["nome_resolvido"]: (linha["segmento"], linha["nome"])
        for linha in bancos.select("nome_resolvido", "segmento", "nome").collect()
        if linha["nome_resolvido"]
    }

    pares = []
    for nome in sem_match:
        alvo = candidatos.get(resolve_acronym(nome))
        if alvo is None:
            melhor = process.extractOne(
                resolve_acronym(nome),
                list(candidatos),
                scorer=fuzz.WRatio,
                score_cutoff=FUZZY_SCORE_CUTOFF,
            )
            if melhor:
                alvo = candidatos[melhor[0]]
        if alvo:
            pares.append((nome, alvo[0], alvo[1]))

    if not pares:
        return janela

    mapa = janela.sparkSession.createDataFrame(
        pares, "nome_norm string, seg_fuzzy string, nome_fuzzy string"
    )
    return (
        janela.join(mapa, on="nome_norm", how="left")
        .withColumn(
            "origem_do_match",
            F.when(
                F.col("segmento").isNull() & F.col("seg_fuzzy").isNotNull(), F.lit("fuzzy")
            ).otherwise(F.col("origem_do_match")),
        )
        .withColumn("segmento", F.coalesce("segmento", "seg_fuzzy"))
        .withColumn("nome_banco", F.coalesce("nome_banco", "nome_fuzzy"))
        .drop("seg_fuzzy", "nome_fuzzy")
    )


def _enriquece(janela: DataFrame, bancos: DataFrame) -> DataFrame:
    df = _junta_por(janela, bancos, "cnpj_norm", "cnpj")
    df = _junta_por(df, bancos, "nome_norm", "nome")
    df = _junta_por(df, bancos, "nome_resolvido", "acr")

    df = (
        df.withColumn(
            "origem_do_match",
            F.when(F.col("seg_cnpj").isNotNull(), F.lit("cnpj"))
            .when(F.col("seg_nome").isNotNull(), F.lit("nome"))
            .when(F.col("seg_acr").isNotNull(), F.lit("acronimo"))
            .otherwise(F.lit("nenhum")),
        )
        .withColumn("segmento", F.coalesce("seg_cnpj", "seg_nome", "seg_acr"))
        .withColumn("nome_banco", F.coalesce("nome_cnpj", "nome_nome", "nome_acr"))
        .drop("seg_cnpj", "seg_nome", "seg_acr", "nome_cnpj", "nome_nome", "nome_acr")
    )

    df = _fuzzy(df, bancos)
    return df.withColumn("banco_encontrado", F.col("segmento").isNotNull())


def _grava(df: DataFrame, destino: str) -> None:
    # overwrite dinâmico (configurado na sessão): reprocessar uma janela
    # sobrescreve só as partições ano/trimestre que ela contém
    df.coalesce(1).write.mode("overwrite").partitionBy("ano", "trimestre").parquet(destino)


def processa_janela(janela: DataFrame, batch_id: int) -> None:
    if janela.isEmpty():
        return

    janela.persist()
    try:
        total = janela.count()
        _grava(janela, camada("trusted", "reclamacoes"))

        bancos = _le_cadastro(janela.sparkSession)
        enriquecido = _enriquece(janela, bancos)
        _grava(enriquecido, camada("delivery", "reclamacoes_enriquecidas"))

        logger.info(f"janela {batch_id}: {total} mensagens tratadas e enriquecidas")
    finally:
        janela.unpersist()


def main() -> None:
    spark = (
        SparkSession.builder.appName("reclamacoes-streaming")
        # o padrão (200) é dimensionado para volumes bem maiores que uma janela daqui
        .config("spark.sql.shuffle.partitions", "4")
        # overwrite dinâmico: substitui só as partições ano/trimestre presentes no
        # lote, não o diretório inteiro — é o que permite reprocessar uma janela
        # sem apagar as demais
        .config("spark.sql.sources.partitionOverwriteMode", "dynamic")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    logger.info(f"Lendo de {KAFKA_BOOTSTRAP}, tópico {KAFKA_TOPIC}")
    bruto = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
        .option("subscribe", KAFKA_TOPIC)
        .option("startingOffsets", "earliest")
        .load()
    )

    mensagens = bruto.select(
        F.from_json(F.col("value").cast("string"), SCHEMA).alias("m")
    ).select("m.*")

    consulta = (
        _trata(mensagens)
        .writeStream.foreachBatch(processa_janela)
        .option("checkpointLocation", camada("checkpoint"))
        .trigger(processingTime=f"{JANELA_SEGUNDOS} seconds")
        .start()
    )
    consulta.awaitTermination()


if __name__ == "__main__":
    main()
