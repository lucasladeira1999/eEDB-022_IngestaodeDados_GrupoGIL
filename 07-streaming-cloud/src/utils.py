import logging
import os
import re

ACRONYMS_PATH = os.path.join(os.path.dirname(__file__), "acronyms.yaml")

# carregado na primeira chamada e reaproveitado (inclusive entre invocações
# quentes da Lambda, que mantêm o módulo em memória)
_acronyms = None

# mesmas chaves do config.yaml, mas lidas do ambiente: é assim que a config chega
# nas Lambdas (o zip não leva o config.yaml junto).
ENV_TO_CONFIG = {
    "RAW_BUCKET": "raw_bucket",
    "TRUSTED_BUCKET": "trusted_bucket",
    "DELIVERY_BUCKET": "delivery_bucket",
    "RAW_PREFIX": "raw_prefix",
    "QUEUE_URL": "queue_url",
    "DB_HOST": "db_host",
    "DB_PORT": "db_port",
    "DB_NAME": "db_name",
    "DB_USER": "db_user",
    "DB_PASSWORD": "db_password",
}


def setup_logger() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(filename)s - %(levelname)s - %(message)s",
    )
    logging.getLogger().handlers[0].formatter.default_msec_format = "%s.%03d"
    return logging.getLogger()


def load_config(config_path: str) -> dict:
    # import local: PyYAML não existe no runtime da Lambda, e lá a config vem do
    # ambiente (load_config_from_env), não do arquivo.
    import yaml

    with open(config_path, "r") as config_file:
        return yaml.safe_load(config_file)


def slug(valor: str) -> str:
    """Texto seguro para compor chave de S3 (sem espaço nem pontuação)."""
    limpo = re.sub(r"[^A-Za-z0-9]+", "_", (valor or "").strip())
    return limpo.strip("_").upper() or "SEM_NOME"


def load_acronyms(path: str = ACRONYMS_PATH) -> dict:
    import yaml

    with open(path, "r") as arquivo:
        return yaml.safe_load(arquivo) or {}


def resolve_acronym(nome: str, path: str = ACRONYMS_PATH) -> str:
    """Traduz sigla/apelido para o nome canônico do banco ("BB" -> "BANCO DO BRASIL").

    O de-para mora em acronyms.yaml; aqui fica só a conversão. Devolve o próprio
    nome quando não há entrada, então pode ser aplicado sem medo dos dois lados.
    """
    global _acronyms
    if _acronyms is None:
        _acronyms = load_acronyms(path)
    return _acronyms.get(nome, nome)


def load_config_from_env() -> dict:
    return {
        chave: os.environ[env]
        for env, chave in ENV_TO_CONFIG.items()
        if os.environ.get(env)
    }
