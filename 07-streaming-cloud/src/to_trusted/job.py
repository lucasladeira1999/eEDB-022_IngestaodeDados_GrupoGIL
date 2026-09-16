"""Camada trusted: trata uma reclamação vinda da fila (normaliza chaves, converte
tipos) e grava o resultado no bucket trusted.

Mesmo tratamento da ReclamacoesETL da atividade 2, só que registro a registro.
"""

import json
import re

import boto3

from to_trusted.etl.normalize import normalize_cnpj, normalize_text
from utils import setup_logger, slug

logger = setup_logger()

QTY_COLS = [
    "qtd_reclamacoes_reguladas_procedentes",
    "qtd_reclamacoes_reguladas_outras",
    "qtd_reclamacoes_nao_reguladas",
    "qtd_total_reclamacoes",
    "qtd_total_clientes_ccs_e_scr",
    "qtd_clientes_ccs",
    "qtd_clientes_scr",
]

PREFIXO = "reclamacoes/"

s3_client = boto3.client("s3")


def _para_inteiro(valor: str | None) -> int | None:
    digitos = re.sub(r"\D", "", valor or "")
    return int(digitos) if digitos else None


def _para_decimal(valor: str | None) -> float | None:
    # vem no formato brasileiro ("1.234,56"): tira o separador de milhar e troca a vírgula
    limpo = re.sub(r"\s", "", valor or "").replace(".", "").replace(",", ".")
    try:
        return float(limpo) if limpo else None
    except ValueError:
        return None


def chave_s3(registro: dict) -> str:
    """Chave derivada do próprio registro, não do messageId do SQS.

    (ano, trimestre, nome_norm) identifica uma reclamação de forma única nas 918
    linhas da fonte, então reprocessar a mesma mensagem sobrescreve o objeto em vez
    de criar um novo — a gravação fica idempotente.
    """
    ano = registro.get("ano") or "sem_ano"
    trimestre = registro.get("trimestre") or "sem_trimestre"
    return f"{PREFIXO}ano={ano}/trimestre={trimestre}/{slug(registro.get('nome_norm'))}.json"


class ToTrustedJob:
    def run(mensagem: dict, message_id: str, **config) -> dict:
        tratada = dict(mensagem)
        tratada["cnpj_norm"] = normalize_cnpj(mensagem.get("cnpj_if"))
        tratada["nome_norm"] = normalize_text(mensagem.get("instituicao_financeira"))
        # o trimestre vem como "1º": vira 1, que também é o que entra na chave do S3
        tratada["ano"] = _para_inteiro(mensagem.get("ano"))
        tratada["trimestre"] = _para_inteiro(mensagem.get("trimestre"))
        tratada["indice"] = _para_decimal(mensagem.get("indice"))
        for coluna in QTY_COLS:
            tratada[coluna] = _para_inteiro(mensagem.get(coluna))

        key = chave_s3(tratada)
        s3_client.put_object(
            Bucket=config["trusted_bucket"],
            Key=key,
            Body=json.dumps(tratada, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
        )
        logger.info(f"trusted: s3://{config['trusted_bucket']}/{key}")
        return tratada
