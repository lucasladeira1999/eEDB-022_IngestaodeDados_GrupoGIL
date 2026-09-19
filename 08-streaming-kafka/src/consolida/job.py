"""Junta o que o streaming gravou em arquivos únicos e legíveis.

O consumidor grava do jeito que o Spark grava: um diretório particionado por
ano/trimestre, com um arquivo por janela. É o certo para o streaming — escrita
paralela e partition pruning na leitura —, mas não é o que alguém abre pra olhar.

Este job achata isso em:
  - um .parquet único (mesmo formato das outras atividades)
  - um .csv (legível por qualquer pessoa do time)

Roda depois que a fila esvazia:  python src/main.py --consolidar
"""

import pandas as pd

from utils import camada, setup_logger

logger = setup_logger()

CAMADAS = {
    "trusted": ("trusted", "reclamacoes"),
    "delivery": ("delivery", "reclamacoes_enriquecidas"),
}


def _le_camada(camada_nome: str, dataset: str) -> pd.DataFrame:
    # o pandas lê o diretório inteiro e reconstrói ano/trimestre a partir do
    # nome das pastas (ano=2021/trimestre=1), que o Spark gravou como partição
    caminho = camada(camada_nome, dataset)
    df = pd.read_parquet(caminho)
    logger.info(f"{caminho}: {len(df)} linhas")
    return df


class ConsolidaJob:
    def run() -> None:
        logger.info("Running ConsolidaJob")

        for rotulo, (camada_nome, dataset) in CAMADAS.items():
            df = _le_camada(camada_nome, dataset)
            if df.empty:
                logger.warning(f"{rotulo} vazio — a fila já foi consumida?")
                continue

            df = df.sort_values(["ano", "trimestre", "nome_norm"], ignore_index=True)

            destino = camada(camada_nome, f"{dataset}.parquet")
            df.to_parquet(destino, index=False)
            logger.info(f"{destino} ({len(df)} linhas)")

        # só a camada final vira CSV: é a que o time abre
        camada_nome, dataset = CAMADAS["delivery"]
        df = pd.read_parquet(camada(camada_nome, f"{dataset}.parquet"))

        destino = camada(camada_nome, f"{dataset}.csv")
        # separador ";" e vírgula decimal: é o que o Excel em pt-BR abre sem perguntar
        df.to_csv(destino, index=False, sep=";", decimal=",", encoding="utf-8-sig")
        logger.info(f"{destino} ({len(df)} linhas)")
