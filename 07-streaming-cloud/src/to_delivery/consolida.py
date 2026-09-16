"""Junta os JSON enriquecidos do delivery num CSV único, sem partição.

Não faz parte do que o enunciado pede (lá a entrega é a mensagem gravada no S3),
mas 918 objetos minúsculos não se leem — este job produz o artefato consolidado,
equivalente à tabela final das outras atividades.

Roda depois que a fila esvazia, porque o consumo é assíncrono:
    python src/main.py --consolidar
"""

import csv
import io
import json
from concurrent.futures import ThreadPoolExecutor

import boto3

from to_delivery.job import PREFIXO
from utils import setup_logger

logger = setup_logger()

ARQUIVO_CSV = "reclamacoes_enriquecidas.csv"

COLUNAS = [
    "ano",
    "trimestre",
    "categoria",
    "tipo",
    "instituicao_financeira",
    "cnpj_if",
    "cnpj_norm",
    "nome_norm",
    "banco_encontrado",
    "origem_do_match",
    "segmento",
    "nome_banco",
    "indice",
    "qtd_total_reclamacoes",
    "qtd_reclamacoes_reguladas_procedentes",
    "qtd_reclamacoes_reguladas_outras",
    "qtd_reclamacoes_nao_reguladas",
    "qtd_total_clientes_ccs_e_scr",
    "qtd_clientes_ccs",
    "qtd_clientes_scr",
    "origem_arquivo",
    "processado_em",
]


class ConsolidaJob:
    def run(**config) -> None:
        bucket = config["delivery_bucket"]
        s3_client = boto3.client("s3")

        paginator = s3_client.get_paginator("list_objects_v2")
        chaves = [
            obj["Key"]
            for page in paginator.paginate(Bucket=bucket, Prefix=PREFIXO)
            for obj in page.get("Contents", [])
            if obj["Key"].endswith(".json")
        ]
        logger.info(f"{len(chaves)} objetos no delivery")

        def baixa(key: str) -> dict:
            corpo = s3_client.get_object(Bucket=bucket, Key=key)["Body"].read()
            return json.loads(corpo)

        # em paralelo: baixar 918 objetos de ~500 bytes um a um é I/O puro
        with ThreadPoolExecutor(max_workers=16) as pool:
            registros = list(pool.map(baixa, chaves))

        registros.sort(
            key=lambda r: (
                r.get("ano") or 0,
                r.get("trimestre") or 0,
                r.get("nome_norm") or "",
            )
        )

        buffer = io.StringIO()
        escritor = csv.DictWriter(buffer, fieldnames=COLUNAS, extrasaction="ignore")
        escritor.writeheader()
        escritor.writerows(registros)
        conteudo = buffer.getvalue()

        s3_client.put_object(
            Bucket=bucket,
            Key=ARQUIVO_CSV,
            Body=conteudo.encode("utf-8"),
            ContentType="text/csv",
        )
        logger.info(f"CSV consolidado: s3://{bucket}/{ARQUIVO_CSV} ({len(registros)} linhas)")

        caminho_local = config.get("csv_local_path")
        if caminho_local:
            with open(caminho_local, "w", encoding="utf-8") as arquivo:
                arquivo.write(conteudo)
            logger.info(f"Cópia local: {caminho_local}")
