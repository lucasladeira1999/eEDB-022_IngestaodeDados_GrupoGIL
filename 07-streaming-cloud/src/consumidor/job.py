"""Consumidor (Lambda ligada ao SQS): para cada mensagem da fila roda a camada
trusted (tratamento) e depois a delivery (enriquecimento no RDS + gravação no S3).
"""

import json

from to_delivery.job import ToDeliveryJob
from to_trusted.job import ToTrustedJob
from utils import load_config_from_env, setup_logger

logger = setup_logger()


class ConsumidorJob:
    def run(event, **config) -> dict:
        falhas = []

        for registro in event.get("Records", []):
            message_id = registro["messageId"]
            try:
                mensagem = json.loads(registro["body"])
                tratada = ToTrustedJob.run(mensagem, message_id, **config)
                ToDeliveryJob.run(tratada, message_id, **config)
            except Exception:
                # só a mensagem com problema volta pra fila; o resto do lote segue
                logger.exception(f"Falha ao processar a mensagem {message_id}")
                falhas.append({"itemIdentifier": message_id})

        return {"batchItemFailures": falhas}


def lambda_handler(event, context):
    return ConsumidorJob.run(event or {}, **load_config_from_env())
