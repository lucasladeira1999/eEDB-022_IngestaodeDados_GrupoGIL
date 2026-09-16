"""Carrega o cadastro de bancos do S3 raw para a tabela do RDS.

É a fonte que o consumidor consulta pra enriquecer cada reclamação, então roda
uma vez (local, via main.py) antes de ligar o streaming.
"""

import csv
import io

import boto3
import pg8000.native

from sql_schema import (
    BANCOS_COLUMNS,
    BANCOS_INDEXES,
    BANCOS_TABLE,
    create_index_sql,
    create_table_sql,
)
from to_trusted.etl.normalize import normalize_cnpj, normalize_text
from utils import resolve_acronym, setup_logger

logger = setup_logger()

BANCOS_KEY = "Bancos/EnquadramentoInicia_v2.tsv"
ENCODING = "utf-8"


def _linhas_do_s3(raw_bucket: str) -> list[dict]:
    corpo = boto3.client("s3").get_object(Bucket=raw_bucket, Key=BANCOS_KEY)["Body"].read()
    leitor = csv.reader(io.StringIO(corpo.decode(ENCODING)), delimiter="\t")
    next(leitor, None)

    linhas = []
    for campos in leitor:
        if len(campos) < 3:
            continue
        segmento, cnpj, nome = campos[0], campos[1], campos[2]
        nome_norm = normalize_text(nome)
        linhas.append(
            {
                "segmento": segmento,
                "cnpj": cnpj,
                "nome": nome,
                "cnpj_norm": normalize_cnpj(cnpj),
                "nome_norm": nome_norm,
                # guardado já resolvido pra que a consulta compare sigla com sigla:
                # a reclamação é resolvida na hora, os dois lados chegam iguais
                "nome_resolvido": resolve_acronym(nome_norm),
            }
        )
    return linhas


def _deduplica(linhas: list[dict]) -> list[dict]:
    """Mesma regra da atividade 2: CNPJ manda; nome só decide quem não tem CNPJ."""
    vistos_cnpj, vistos_nome, resultado = set(), set(), []
    for linha in linhas:
        chave_cnpj, chave_nome = linha["cnpj_norm"], linha["nome_norm"]
        if chave_cnpj:
            if chave_cnpj in vistos_cnpj:
                continue
            vistos_cnpj.add(chave_cnpj)
        else:
            if chave_nome in vistos_nome:
                continue
            vistos_nome.add(chave_nome)
        resultado.append(linha)
    return resultado


class ToRdsJob:
    def run(**config) -> None:
        logger.info("Running ToRdsJob")

        linhas = _deduplica(_linhas_do_s3(config["raw_bucket"]))
        logger.info(f"{len(linhas)} bancos prontos para carga")

        buffer = io.StringIO()
        escritor = csv.writer(buffer)
        for linha in linhas:
            escritor.writerow([linha[coluna] for coluna in BANCOS_COLUMNS])
        buffer.seek(0)

        conn = pg8000.native.Connection(
            host=config["db_host"],
            port=int(config.get("db_port", 5432)),
            database=config["db_name"],
            user=config["db_user"],
            password=config["db_password"],
        )
        try:
            conn.run(create_table_sql(BANCOS_TABLE, BANCOS_COLUMNS))
            for coluna in BANCOS_INDEXES:
                conn.run(create_index_sql(BANCOS_TABLE, coluna))
            conn.run(f"TRUNCATE TABLE {BANCOS_TABLE}")

            colunas = ", ".join(BANCOS_COLUMNS)
            # COPY em vez de INSERT linha a linha: é uma viagem de rede só
            conn.run(
                f"COPY {BANCOS_TABLE} ({colunas}) FROM STDIN WITH (FORMAT CSV)",
                stream=buffer,
            )
            logger.info(f"{len(linhas)} bancos carregados na tabela {BANCOS_TABLE}")
        finally:
            conn.close()
