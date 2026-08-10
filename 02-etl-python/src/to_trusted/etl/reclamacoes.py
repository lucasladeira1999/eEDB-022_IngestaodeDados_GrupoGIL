from to_trusted.etl.base import BaseETL


class ReclamacoesETL(BaseETL):
    name = "reclamacoes"
    prefix = "Reclamacoes/"
    extension = ".csv"
    sep = ";"
    dtype = str
