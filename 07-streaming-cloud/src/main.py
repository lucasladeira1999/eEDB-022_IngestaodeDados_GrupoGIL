"""Roda as etapas locais e dispara o streaming.

O que é local (aqui) e o que é Lambda (na AWS):
  local   -> to_raw  : sobe os arquivos de dados/ para o bucket raw
  local   -> to_rds  : carrega o cadastro de bancos na tabela do RDS
  Lambda  -> produtor: lê o raw e publica na fila (disparado no fim deste script)
  Lambda  -> consumidor: consome a fila, roda trusted e delivery
"""

import json
import os
import sys

import boto3

from to_delivery.consolida import ConsolidaJob
from to_raw.job import ToRawJob
from to_rds.job import ToRdsJob
from utils import load_config, setup_logger

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

logger = setup_logger()


def disparar_produtor(**config) -> None:
    nome = config["produtor_function_name"]
    logger.info(f"Invocando a Lambda produtora: {nome}")

    resposta = boto3.client("lambda").invoke(
        FunctionName=nome,
        InvocationType="RequestResponse",
        Payload=json.dumps({}).encode("utf-8"),
    )
    logger.info(f"Resposta do produtor: {resposta['Payload'].read().decode('utf-8')}")


def main():
    config = load_config(CONFIG_PATH)
    config["dados_path"] = os.path.join(PROJECT_ROOT, config["dados_path"])

    logger.info(f"Loaded config: {config}")

    # o consumo da fila é assíncrono, então a consolidação é um passo à parte:
    # roda depois que a fila esvaziar, não junto com o disparo do produtor
    if "--consolidar" in sys.argv:
        ConsolidaJob.run(**config)
        return

    ToRawJob.run(**config)
    ToRdsJob.run(**config)
    disparar_produtor(**config)


if __name__ == "__main__":
    main()
