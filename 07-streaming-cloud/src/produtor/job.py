"""Produtor (Lambda): lê os CSVs de reclamações no S3 raw e publica uma mensagem
por linha no SQS.

Aceita três formas de invocação:
  - notificação do S3 (ObjectCreated), que já traz a chave no evento
  - manual, com {"key": "Reclamacoes/2021_tri_01.csv"}
  - manual, com {} — varre todo o prefixo configurado
"""

import csv
import io
import json
from urllib.parse import unquote_plus

import boto3

from utils import load_config_from_env, setup_logger

logger = setup_logger()

# o CSV do BACEN vem em ISO-8859-1 e com um ";" sobrando no fim do cabeçalho,
# que viraria uma coluna fantasma. Renomeamos por posição e ignoramos o excedente.
ENCODING = "iso-8859-1"
DELIMITER = ";"
LOTE_SQS = 10  # limite do send_message_batch

CANONICAL_COLS = [
    "ano",
    "trimestre",
    "categoria",
    "tipo",
    "cnpj_if",
    "instituicao_financeira",
    "indice",
    "qtd_reclamacoes_reguladas_procedentes",
    "qtd_reclamacoes_reguladas_outras",
    "qtd_reclamacoes_nao_reguladas",
    "qtd_total_reclamacoes",
    "qtd_total_clientes_ccs_e_scr",
    "qtd_clientes_ccs",
    "qtd_clientes_scr",
]

s3_client = boto3.client("s3")
sqs_client = boto3.client("sqs")


def _keys_do_evento(event: dict, raw_bucket: str, raw_prefix: str) -> list[str]:
    if "Records" in event:
        return [
            unquote_plus(registro["s3"]["object"]["key"])
            for registro in event["Records"]
            if registro.get("s3")
        ]

    if event.get("key"):
        return [event["key"]]

    paginator = s3_client.get_paginator("list_objects_v2")
    return [
        obj["Key"]
        for page in paginator.paginate(Bucket=raw_bucket, Prefix=raw_prefix)
        for obj in page.get("Contents", [])
        if obj["Key"].endswith(".csv")
    ]


def _linhas_do_csv(raw_bucket: str, key: str) -> list[dict]:
    corpo = s3_client.get_object(Bucket=raw_bucket, Key=key)["Body"].read()
    leitor = csv.reader(io.StringIO(corpo.decode(ENCODING)), delimiter=DELIMITER)
    next(leitor, None)

    linhas = []
    for campos in leitor:
        if not any(campo.strip() for campo in campos):
            continue
        registro = dict(zip(CANONICAL_COLS, campos))
        registro["origem_arquivo"] = key.rsplit("/", 1)[-1]
        linhas.append(registro)
    return linhas


def _publica(linhas: list[dict], queue_url: str) -> int:
    enviadas = 0
    for inicio in range(0, len(linhas), LOTE_SQS):
        lote = linhas[inicio : inicio + LOTE_SQS]
        entradas = [
            {"Id": str(i), "MessageBody": json.dumps(linha, ensure_ascii=False)}
            for i, linha in enumerate(lote)
        ]
        resposta = sqs_client.send_message_batch(QueueUrl=queue_url, Entries=entradas)

        for falha in resposta.get("Failed", []):
            logger.error(f"Falha ao publicar mensagem: {falha}")
        enviadas += len(resposta.get("Successful", []))
    return enviadas


class ProdutorJob:
    def run(event, **config) -> dict:
        raw_bucket = config["raw_bucket"]
        raw_prefix = config.get("raw_prefix", "Reclamacoes/")
        queue_url = config["queue_url"]
        limite = event.get("limit")

        total = 0
        for key in _keys_do_evento(event, raw_bucket, raw_prefix):
            if "nao_ha_dados" in key:
                logger.info(f"Ignorando arquivo sem dados: {key}")
                continue

            linhas = _linhas_do_csv(raw_bucket, key)
            if limite:
                linhas = linhas[:limite]

            enviadas = _publica(linhas, queue_url)
            logger.info(f"{key}: {enviadas}/{len(linhas)} mensagens publicadas")
            total += enviadas

        logger.info(f"Total publicado na fila: {total}")
        return {"mensagens_publicadas": total}


def lambda_handler(event, context):
    return ProdutorJob.run(event or {}, **load_config_from_env())
