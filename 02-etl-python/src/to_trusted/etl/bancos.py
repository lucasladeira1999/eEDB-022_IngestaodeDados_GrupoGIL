from to_trusted.etl.base import BaseETL


class BancosETL(BaseETL):
    name = "bancos"
    prefix = "Bancos/"
    extension = ".tsv"
    sep = "\t"
