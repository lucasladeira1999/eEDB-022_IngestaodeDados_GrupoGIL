import logging
import os
import re
import unicodedata

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("LOCAL_DATA_DIR", os.path.join(BASE_DIR, "data"))
DADOS_DIR = os.environ.get("DADOS_DIR", os.path.join(os.path.dirname(BASE_DIR), "dados"))

KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP", "localhost:9092")
KAFKA_TOPIC = os.environ.get("KAFKA_TOPIC", "reclamacoes")

CADASTRO_SCHEMA = os.environ.get("CADASTRO_SCHEMA", "cadastro")
CADASTRO_TABELA = os.environ.get("CADASTRO_TABELA", "bancos")


SRC_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMAS_PATH = os.path.join(SRC_DIR, "schemas.yaml")
ACRONYMS_PATH = os.path.join(SRC_DIR, "acronyms.yaml")

# carregados na primeira chamada e reaproveitados
_yamls: dict[str, dict] = {}

SUFIXOS = ["- PRUDENCIAL", "(conglomerado)", "S.A.", "LTDA", "S/A"]


def _le_yaml(caminho: str) -> dict:
    if caminho not in _yamls:
        import yaml

        with open(caminho, encoding="utf-8") as arquivo:
            _yamls[caminho] = yaml.safe_load(arquivo) or {}
    return _yamls[caminho]


def schema(*chaves: str):
    """Lê uma definição de coluna do schemas.yaml: schema("cadastro", "colunas").

    Nenhuma lista de coluna mora no código — quem precisa declarar estrutura de
    dado edita o YAML, não o Python.
    """
    valor = _le_yaml(SCHEMAS_PATH)
    for chave in chaves:
        valor = valor[chave]
    return valor


def resolve_acronym(nome: str) -> str:
    """Traduz sigla/apelido para o nome canônico ("BB" -> "BANCO DO BRASIL").

    O de-para mora em acronyms.yaml; aqui fica só a conversão. Devolve o próprio
    nome quando não há entrada, então pode ser aplicado dos dois lados sem medo.
    """
    return _le_yaml(ACRONYMS_PATH).get(nome, nome)


def normalize_text(valor: str) -> str:
    """Chave de nome: maiúsculas, sem sufixo societário, sem acento, só alfanumérico.

    O acento é transliterado e não apagado: apagar faria ECONÔMICA virar ECONMICA
    de um lado e ECONOMICA do outro, e os dois não casariam.
    """
    if not isinstance(valor, str):
        valor = str(valor) if valor is not None else ""
    valor = valor.strip().upper()
    for sufixo in SUFIXOS:
        valor = valor.replace(sufixo.upper(), "")
    valor = unicodedata.normalize("NFKD", valor)
    valor = valor.encode("ASCII", "ignore").decode("ASCII")
    valor = re.sub(r"[^A-Z0-9 ]", "", valor)
    return re.sub(r"\s+", " ", valor).strip()


def normalize_cnpj(valor: str) -> str:
    """Só dígitos, sem zero à esquerda: o cadastro grava 360305 e as reclamações 00360305."""
    if not isinstance(valor, str):
        valor = str(valor) if valor is not None else ""
    return re.sub(r"\D", "", valor).lstrip("0")


def setup_logger() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(filename)s - %(levelname)s - %(message)s",
    )
    logging.getLogger().handlers[0].formatter.default_msec_format = "%s.%03d"
    return logging.getLogger()


def camada(nome: str, *partes: str) -> str:
    """Caminho de uma camada em disco: camada("trusted", "reclamacoes")."""
    return os.path.join(DATA_DIR, nome, *partes)


def postgres_config() -> dict:
    return {
        "host": os.environ.get("PG_HOST", "localhost"),
        "port": int(os.environ.get("PG_PORT", "5432")),
        "database": os.environ.get("PG_DB", "postgres"),
        "user": os.environ.get("PG_USER", "etl"),
        "password": os.environ.get("PG_PASSWORD", "etl"),
    }


def jdbc_url() -> str:
    cfg = postgres_config()
    return f"jdbc:postgresql://{cfg['host']}:{cfg['port']}/{cfg['database']}"


def jdbc_properties() -> dict:
    cfg = postgres_config()
    return {
        "user": cfg["user"],
        "password": cfg["password"],
        "driver": "org.postgresql.Driver",
    }
