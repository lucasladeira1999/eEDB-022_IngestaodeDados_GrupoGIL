from to_trusted.etl.base import BaseETL


class EmpregadosETL(BaseETL):
    name = "empregados"
    prefix = "Empregados/"
    extension = ".csv"
    sep = "|"
