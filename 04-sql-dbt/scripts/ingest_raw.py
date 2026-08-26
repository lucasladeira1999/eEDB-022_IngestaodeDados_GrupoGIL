from pathlib import Path
import duckdb
import pandas as pd


def get_base_paths() -> tuple[Path, Path, str]:
    current_dir = Path(__file__).resolve().parent.parent

    # Priority 1: Container mount /dados
    if Path("/dados").exists():
        dados_dir = Path("/dados")
    else:
        # Priority 2: ../dados from project root
        dados_dir = current_dir.parent / "dados"
        if not dados_dir.exists():
            dados_dir = current_dir / "dados"

    data_dir = current_dir / "data"
    raw_dir = data_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    db_path = str(data_dir / "database.duckdb")
    return dados_dir, raw_dir, db_path


def ingest_bancos(
    dados_dir: Path, raw_dir: Path, con: duckdb.DuckDBPyConnection
) -> None:
    bancos_file = dados_dir / "Bancos" / "EnquadramentoInicia_v2.tsv"
    print(f"[*] Ingesting Bancos from {bancos_file}...")
    df = pd.read_csv(bancos_file, sep="\t", encoding="utf-8", dtype=str)

    # Save raw CSV in data/raw
    df.to_csv(raw_dir / "bancos.csv", index=False)

    # Ingest into DuckDB raw.bancos
    con.execute("CREATE SCHEMA IF NOT EXISTS raw;")
    con.register("df_bancos_view", df)
    con.execute("CREATE OR REPLACE TABLE raw.bancos AS SELECT * FROM df_bancos_view;")
    print(f"[+] raw.bancos loaded with {len(df)} records.")


def ingest_empregados(
    dados_dir: Path, raw_dir: Path, con: duckdb.DuckDBPyConnection
) -> None:
    emp_dir = dados_dir / "Empregados"
    emp_files = sorted(emp_dir.glob("*.csv"))
    print(f"[*] Ingesting Empregados from {emp_files}...")

    dfs = []
    for file_path in emp_files:
        try:
            df = pd.read_csv(file_path, sep="|", encoding="utf-8", dtype=str)
            if "CNPJ" not in df.columns:
                df["CNPJ"] = ""
            if "Segmento" not in df.columns:
                df["Segmento"] = ""
            dfs.append(df)
        except (
            pd.errors.EmptyDataError,
            pd.errors.ParserError,
            OSError,
            ValueError,
            UnicodeDecodeError,
        ) as e:
            print(f"[-] Warning: Failed to read {file_path}: {e}")

    df_emp = pd.concat(dfs, ignore_index=True)

    # Save raw CSV in data/raw
    df_emp.to_csv(raw_dir / "empregados.csv", index=False)

    # Ingest into DuckDB raw.empregados
    con.register("df_emp_view", df_emp)
    con.execute("CREATE OR REPLACE TABLE raw.empregados AS SELECT * FROM df_emp_view;")
    print(f"[+] raw.empregados loaded with {len(df_emp)} records.")


def ingest_reclamacoes(
    dados_dir: Path, raw_dir: Path, con: duckdb.DuckDBPyConnection
) -> None:
    rec_dir = dados_dir / "Reclamacoes"
    rec_files = sorted(rec_dir.glob("*.csv"))
    print(f"[*] Ingesting Reclamacoes from {rec_files}...")

    dfs = []
    for file_path in rec_files:
        if file_path.stat().st_size == 0:
            print(f"[-] Skipping empty file: {file_path}")
            continue
        try:
            df = pd.read_csv(
                file_path,
                sep=";",
                encoding="iso-8859-1",
                dtype=str,
                low_memory=False,
            )
            # Remove empty/trailing columns
            df = df.loc[:, df.columns != ""]
            df = df.dropna(axis=1, how="all")

            # Map standard column positions
            column_names = [
                "ano",
                "trimestre",
                "categoria",
                "tipo",
                "cnpj_if",
                "instituicao_financeira",
                "indice",
                "qtd_reclamacoes_reguladas_procedentes",
                "qtd_reclamacoes_reguladas_outras",
                "qtd_reclamacoes_nao_reguladas",
                "qtd_total_reclamacoes",
                "qtd_total_clientes_ccs_scr",
                "qtd_clientes_ccs",
                "qtd_clientes_scr",
            ]
            if len(df.columns) >= len(column_names):
                df.columns = column_names[: len(df.columns)]
                dfs.append(df)
        except (
            pd.errors.EmptyDataError,
            pd.errors.ParserError,
            OSError,
            ValueError,
            UnicodeDecodeError,
        ) as e:
            print(f"[-] Warning: Failed to read {file_path}: {e}")

    df_rec = pd.concat(dfs, ignore_index=True)

    # Save raw CSV in data/raw
    df_rec.to_csv(raw_dir / "reclamacoes.csv", index=False)

    # Ingest into DuckDB raw.reclamacoes
    con.register("df_rec_view", df_rec)
    con.execute("CREATE OR REPLACE TABLE raw.reclamacoes AS SELECT * FROM df_rec_view;")
    print(f"[+] raw.reclamacoes loaded with {len(df_rec)} records.")


def main() -> None:
    dados_dir, raw_dir, db_path = get_base_paths()
    print("=== Starting Raw Ingestion ===")
    print(f"Source dir: {dados_dir}")
    print(f"Raw storage dir: {raw_dir}")
    print(f"DuckDB path: {db_path}")

    con = duckdb.connect(db_path)
    try:
        ingest_bancos(dados_dir, raw_dir, con)
        ingest_empregados(dados_dir, raw_dir, con)
        ingest_reclamacoes(dados_dir, raw_dir, con)
        print("=== Raw Ingestion Completed Successfully ===")
    finally:
        con.close()


if __name__ == "__main__":
    main()
