"""Produtor: lê os CSV de reclamações no disco e publica uma mensagem por linha no Kafka.

Script Python puro, sem Spark.
"""

import csv
import json
import os

from confluent_kafka import Producer

from utils import KAFKA_BOOTSTRAP, KAFKA_TOPIC, camada, schema, setup_logger

logger = setup_logger()

# o CSV do BACEN vem em ISO-8859-1 e com um ";" sobrando no fim do cabeçalho, que
# criaria uma coluna fantasma: renomeamos por posição e ignoramos o excedente
ENCODING = "iso-8859-1"
DELIMITER = ";"


def _linhas_do_csv(caminho: str) -> list[dict]:
    with open(caminho, encoding=ENCODING) as arquivo:
        leitor = csv.reader(arquivo, delimiter=DELIMITER)
        next(leitor, None)

        linhas = []
        for campos in leitor:
            if not any(campo.strip() for campo in campos):
                continue
            registro = dict(zip(schema("reclamacoes", "colunas_origem"), campos))
            registro["origem_arquivo"] = os.path.basename(caminho)
            linhas.append(registro)
    return linhas


def _reporta_falha(erro, mensagem):
    if erro is not None:
        logger.error(f"Falha ao publicar: {erro}")


class ProdutorJob:
    def run(limite: int | None = None) -> int:
        logger.info(f"Publicando em {KAFKA_BOOTSTRAP}, tópico {KAFKA_TOPIC}")
        producer = Producer({"bootstrap.servers": KAFKA_BOOTSTRAP})

        pasta = camada("raw", "Reclamacoes")
        arquivos = sorted(
            nome
            for nome in os.listdir(pasta)
            if nome.endswith(".csv") and "nao_ha_dados" not in nome
        )

        total = 0
        for nome in arquivos:
            linhas = _linhas_do_csv(os.path.join(pasta, nome))
            if limite:
                linhas = linhas[:limite]

            for linha in linhas:
                producer.produce(
                    KAFKA_TOPIC,
                    # a chave define a partição: reclamações do mesmo banco ficam juntas
                    key=(linha.get("instituicao_financeira") or "").encode("utf-8"),
                    value=json.dumps(linha, ensure_ascii=False).encode("utf-8"),
                    callback=_reporta_falha,
                )
                producer.poll(0)

            logger.info(f"{nome}: {len(linhas)} mensagens")
            total += len(linhas)

        pendentes = producer.flush(timeout=30)
        if pendentes:
            logger.error(f"{pendentes} mensagens não confirmadas pelo broker")

        logger.info(f"Total publicado: {total}")
        return total
