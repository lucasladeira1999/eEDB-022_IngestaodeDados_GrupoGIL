"""Fonte única do schema da tabela consultada no enriquecimento.

Mesma ideia do sql_schema.py da atividade 02: o tamanho de cada VARCHAR é
declarado em um lugar só. Aqui não há inferência por dtype porque a tabela é toda
texto — a normalização é que decide o conteúdo, e converter tipo no cadastro
comeria o zero à esquerda do CNPJ.
"""

BANCOS_TABLE = "bancos"

VARCHAR_SIZES = {
    "segmento": 10,
    "cnpj": 20,
    "nome": 500,
    "cnpj_norm": 20,
    "nome_norm": 255,
    "nome_resolvido": 255,
}

DEFAULT_VARCHAR = 65535

# a ordem desta lista vale para o CREATE TABLE e para o COPY: uma lista só evita
# que o DDL e a carga saiam de sincronia sem ninguém perceber
BANCOS_COLUMNS = [
    "segmento",
    "cnpj",
    "nome",
    "cnpj_norm",
    "nome_norm",
    "nome_resolvido",
]

# colunas consultadas pelo enriquecimento, cada uma com seu índice
BANCOS_INDEXES = ["cnpj_norm", "nome_norm", "nome_resolvido"]


def create_table_sql(table_name: str, columns: list[str]) -> str:
    definicoes = [
        f'"{coluna}" VARCHAR({VARCHAR_SIZES.get(coluna, DEFAULT_VARCHAR)})'
        for coluna in columns
    ]
    return f'CREATE TABLE IF NOT EXISTS "{table_name}" ({", ".join(definicoes)})'


def create_index_sql(table_name: str, column: str) -> str:
    return (
        f'CREATE INDEX IF NOT EXISTS idx_{table_name}_{column} '
        f'ON "{table_name}" ("{column}")'
    )
