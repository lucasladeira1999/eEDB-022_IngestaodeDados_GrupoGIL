"""Carrega o cadastro de bancos do raw para o Postgres.

É a tabela que o consumidor consulta a cada janela pra enriquecer as reclamações,
então roda uma vez antes de ligar o streaming.
"""

import csv
import io
import os

import pg8000.native

from utils import (
    CADASTRO_SCHEMA,
    CADASTRO_TABELA,
    camada,
    normalize_cnpj,
    normalize_text,
    postgres_config,
    resolve_acronym,
    schema,
    setup_logger,
)

logger = setup_logger()

ARQUIVO = "EnquadramentoInicia_v2.tsv"
ENCODING = "utf-8"



def _le_cadastro() -> list[dict]:
    caminho = os.path.join(camada("raw", "Bancos"), ARQUIVO)
    with open(caminho, encoding=ENCODING) as arquivo:
        leitor = csv.reader(arquivo, delimiter="\t")
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
                    # guardado já resolvido pra sigla comparar com sigla no join
                    "nome_resolvido": resolve_acronym(nome_norm),
                }
            )
    return linhas


def _deduplica(linhas: list[dict]) -> list[dict]:
    """CNPJ manda; nome só decide quem não tem CNPJ (mesma regra da atividade 2)."""
    vistos_cnpj, vistos_nome, resultado = set(), set(), []
    for linha in linhas:
        if linha["cnpj_norm"]:
            if linha["cnpj_norm"] in vistos_cnpj:
                continue
            vistos_cnpj.add(linha["cnpj_norm"])
        else:
            if linha["nome_norm"] in vistos_nome:
                continue
            vistos_nome.add(linha["nome_norm"])
        resultado.append(linha)
    return resultado


def _ddl() -> str:
    tamanhos = schema("cadastro", "varchar")
    colunas = ", ".join(
        f'"{c}" VARCHAR({tamanhos[c]})' for c in schema("cadastro", "colunas")
    )
    return f'CREATE TABLE IF NOT EXISTS {CADASTRO_SCHEMA}.{CADASTRO_TABELA} ({colunas})'


class ToPostgresJob:
    def run() -> None:
        logger.info("Running ToPostgresJob")

        linhas = _deduplica(_le_cadastro())
        logger.info(f"{len(linhas)} bancos prontos para carga")

        buffer = io.StringIO()
        escritor = csv.writer(buffer)
        for linha in linhas:
            escritor.writerow([linha[coluna] for coluna in schema("cadastro", "colunas")])
        buffer.seek(0)

        conn = pg8000.native.Connection(**postgres_config())
        try:
            conn.run(_ddl())
            for coluna in schema("cadastro", "indices"):
                conn.run(
                    f"CREATE INDEX IF NOT EXISTS idx_{CADASTRO_TABELA}_{coluna} "
                    f"ON {CADASTRO_SCHEMA}.{CADASTRO_TABELA} ({coluna})"
                )
            conn.run(f"TRUNCATE TABLE {CADASTRO_SCHEMA}.{CADASTRO_TABELA}")

            colunas = ", ".join(schema("cadastro", "colunas"))
            # COPY em vez de INSERT linha a linha: uma viagem de rede só
            conn.run(
                f"COPY {CADASTRO_SCHEMA}.{CADASTRO_TABELA} ({colunas}) "
                "FROM STDIN WITH (FORMAT CSV)",
                stream=buffer,
            )
            logger.info(f"{len(linhas)} bancos carregados em {CADASTRO_SCHEMA}.{CADASTRO_TABELA}")
        finally:
            conn.close()
