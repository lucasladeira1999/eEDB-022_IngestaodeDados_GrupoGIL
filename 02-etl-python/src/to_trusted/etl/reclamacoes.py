import pandas as pd

from to_trusted.etl.base import BaseETL
from to_trusted.etl.normalize import normalize_cnpj, normalize_text


class ReclamacoesETL(BaseETL):
    name = "reclamacoes"
    prefix = "Reclamacoes/"
    extension = ".csv"
    sep = ";"
    dtype = str

    QTY_COLS = [
        "Quantidade de reclamações reguladas procedentes",
        "Quantidade de reclamações reguladas - outras",
        "Quantidade de reclamações não reguladas",
        "Quantidade total de reclamações",
        "Quantidade total de clientes \x96 CCS e SCR",
        "Quantidade de clientes \x96 CCS",
        "Quantidade de clientes \x96 SCR",
    ]

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df = df.loc[:, df.columns != ""]
        df = df.dropna(axis=1, how="all")
        col_inst = df.columns[5]
        col_cnpj = df.columns[4]
        col_indice = df.columns[6]
        df["nome_norm"] = df[col_inst].apply(normalize_text)
        df["cnpj_norm"] = df[col_cnpj].apply(normalize_cnpj)
        df["indice"] = (
            df[col_indice]
            .str.strip()
            .str.replace(" ", "", regex=False)
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
        df["indice"] = pd.to_numeric(df["indice"], errors="coerce")
        for col in self.QTY_COLS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
