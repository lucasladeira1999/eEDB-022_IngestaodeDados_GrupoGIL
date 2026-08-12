import pandas as pd

from to_trusted.etl.base import BaseETL
from to_trusted.etl.normalize import normalize_cnpj, normalize_text


class EmpregadosETL(BaseETL):
    name = "empregados"
    prefix = "Empregados/"
    extension = ".csv"
    sep = "|"
    encoding = "utf-8"

    RATING_COLS = [
        "Geral",
        "Cultura e valores",
        "Diversidade e inclusão",
        "Qualidade de vida",
        "Alta liderança",
        "Remuneração e benefícios",
        "Oportunidades de carreira",
        "Recomendam para outras pessoas(%)",
        "Perspectiva positiva da empresa(%)",
    ]

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["nome_norm"] = df["Nome"].apply(normalize_text)
        if "CNPJ" in df.columns:
            df["cnpj_norm"] = df["CNPJ"].apply(normalize_cnpj)
        else:
            df["cnpj_norm"] = ""
        for col in self.RATING_COLS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
