"""Roda as etapas locais do pipeline.

    local   to_raw       dados/ -> data/raw/
    local   to_postgres  cadastro de bancos -> tabela no Postgres
    local   produtor     data/raw/ -> Kafka
    Docker  consumidor   Kafka -> trusted + delivery  (sobe separado, fica rodando)

O consumidor não entra aqui porque é um job de streaming: ele precisa estar de pé
antes, esperando a fila. Suba com `docker compose --profile job up consumidor`.

Depois que a fila esvaziar, `--consolidar` achata as janelas num arquivo por camada.
"""

import sys

from consolida.job import ConsolidaJob
from produtor.job import ProdutorJob
from to_postgres.job import ToPostgresJob
from to_raw.job import ToRawJob
from utils import setup_logger

logger = setup_logger()


def main() -> None:
    if "--consolidar" in sys.argv:
        ConsolidaJob.run()
        return

    limite = None
    if "--limite" in sys.argv:
        limite = int(sys.argv[sys.argv.index("--limite") + 1])
        logger.info(f"Publicando no máximo {limite} mensagens por arquivo")

    ToRawJob.run()
    ToPostgresJob.run()
    ProdutorJob.run(limite)


if __name__ == "__main__":
    main()
