import pandas as pd

VARCHAR_SIZES = {
    "nome": 500,
    "nome_norm": 255,
    "cnpj_norm": 20,
    "segmento": 10,
}

DTYPE_TO_SQL = {
    "int64": "BIGINT",
    "int32": "INTEGER",
    "Int64": "BIGINT",
    "Int32": "INTEGER",
    "float64": "DOUBLE PRECISION",
    "float32": "REAL",
    "bool": "BOOLEAN",
    "datetime64[ns]": "TIMESTAMP",
}


def create_table_sql(table_name: str, df: pd.DataFrame) -> str:
    columns = []
    for col, dtype in df.dtypes.items():
        if col in VARCHAR_SIZES:
            sql_type = f"VARCHAR({VARCHAR_SIZES[col]})"
        else:
            sql_type = DTYPE_TO_SQL.get(str(dtype), "VARCHAR(65535)")
        columns.append(f'"{col}" {sql_type}')
    return f'CREATE TABLE IF NOT EXISTS "{table_name}" ({", ".join(columns)})'
