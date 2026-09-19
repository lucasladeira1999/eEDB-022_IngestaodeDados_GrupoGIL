"""Camada raw: copia os arquivos de origem para data/raw/, sem tocar no conteúdo.

Equivale ao to_raw das atividades anteriores, que subia pro S3 — aqui o destino é
disco local. Só as duas fontes que o pipeline usa: reclamações (o que vira mensagem)
e o cadastro de bancos (o que vira tabela de consulta).
"""

import os
import shutil

from utils import DADOS_DIR, camada, setup_logger

logger = setup_logger()

FONTES = ["Reclamacoes", "Bancos"]


class ToRawJob:
    def run() -> None:
        logger.info("Running ToRawJob")

        for fonte in FONTES:
            origem = os.path.join(DADOS_DIR, fonte)
            destino = camada("raw", fonte)

            os.makedirs(destino, exist_ok=True)
            arquivos = sorted(os.listdir(origem))
            for nome in arquivos:
                shutil.copy2(os.path.join(origem, nome), os.path.join(destino, nome))

            logger.info(f"{fonte}: {len(arquivos)} arquivos copiados para {destino}")
