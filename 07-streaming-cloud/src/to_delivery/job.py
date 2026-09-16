"""Camada delivery: enriquece a reclamação já tratada com o cadastro do banco
(consulta no RDS) e grava a mensagem final no bucket delivery.
"""

import json
from datetime import datetime, timezone

import boto3
import pg8000.native

from sql_schema import BANCOS_TABLE
from utils import resolve_acronym, setup_logger, slug

logger = setup_logger()

PREFIXO = "reclamacoes_enriquecidas/"

# as três tentativas, em ordem de confiança: CNPJ é chave de verdade, nome exato
# vem depois e a sigla resolvida é o último recurso
BUSCA = f"SELECT segmento, nome FROM {BANCOS_TABLE} WHERE {{coluna}} = :chave LIMIT 1"
BUSCA_POR_CNPJ = BUSCA.format(coluna="cnpj_norm")
BUSCA_POR_NOME = BUSCA.format(coluna="nome_norm")
BUSCA_POR_RESOLVIDO = BUSCA.format(coluna="nome_resolvido")

s3_client = boto3.client("s3")

# metade das reclamações não traz CNPJ, então o nome normalizado é o plano B.
# A conexão fica no escopo do módulo pra sobreviver entre invocações quentes da
# Lambda — abrir conexão por mensagem seria o gargalo do pipeline.
_conn = None


def _conexao(**config) -> pg8000.native.Connection:
    global _conn
    if _conn is not None:
        try:
            _conn.run("SELECT 1")
            return _conn
        except Exception:
            logger.warning("Conexão com o RDS caiu, reconectando")
            _conn = None

    _conn = pg8000.native.Connection(
        host=config["db_host"],
        port=int(config.get("db_port", 5432)),
        database=config["db_name"],
        user=config["db_user"],
        password=config["db_password"],
        timeout=10,
    )
    return _conn


def _busca_banco(tratada: dict, **config) -> tuple[str, list]:
    conn = _conexao(**config)

    # cnpj_norm vazio não entra na consulta: o cadastro tem banco com CNPJ "0",
    # que normaliza pra vazio e casaria com toda reclamação sem CNPJ
    if tratada.get("cnpj_norm"):
        linhas = conn.run(BUSCA_POR_CNPJ, chave=tratada["cnpj_norm"])
        if linhas:
            return "cnpj", linhas[0]

    if tratada.get("nome_norm"):
        linhas = conn.run(BUSCA_POR_NOME, chave=tratada["nome_norm"])
        if linhas:
            return "nome", linhas[0]

        linhas = conn.run(
            BUSCA_POR_RESOLVIDO, chave=resolve_acronym(tratada["nome_norm"])
        )
        if linhas:
            return "acronimo", linhas[0]

    return "nenhum", []


class ToDeliveryJob:
    def run(tratada: dict, message_id: str, **config) -> dict:
        origem, linha = _busca_banco(tratada, **config)

        enriquecida = dict(tratada)
        enriquecida["banco_encontrado"] = bool(linha)
        enriquecida["origem_do_match"] = origem
        if linha:
            enriquecida["segmento"], enriquecida["nome_banco"] = linha[0], linha[1]
        enriquecida["processado_em"] = datetime.now(timezone.utc).isoformat()

        ano = enriquecida.get("ano") or "sem_ano"
        trimestre = enriquecida.get("trimestre") or "sem_trimestre"
        nome = slug(enriquecida.get("nome_norm"))
        key = f"{PREFIXO}ano={ano}/trimestre={trimestre}/{nome}.json"

        s3_client.put_object(
            Bucket=config["delivery_bucket"],
            Key=key,
            Body=json.dumps(enriquecida, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
        )
        logger.info(f"delivery ({origem}): s3://{config['delivery_bucket']}/{key}")
        return enriquecida
