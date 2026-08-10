import pandas as pd

from to_trusted.etl.base import BaseETL
from to_trusted.etl.normalize import normalize_cnpj, normalize_text


class BancosETL(BaseETL):
    name = "bancos"
    prefix = "Bancos/"
    extension = ".tsv"
    sep = "\t"

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["nome_norm"] = df["Nome"].apply(normalize_text)
        df["cnpj_norm"] = df["CNPJ"].apply(normalize_cnpj)
        return df
