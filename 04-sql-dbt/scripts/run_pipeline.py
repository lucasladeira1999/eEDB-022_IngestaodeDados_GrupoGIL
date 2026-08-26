from pathlib import Path
import shutil
import subprocess
import sys
import duckdb


def run_step(description: str, command: list[str], cwd: Path) -> None:
    print(f"\n{'=' * 20} {description} {'=' * 20}")
    print(f"Executing: {' '.join(command)}")
    result = subprocess.run(command, cwd=cwd, check=False)
    if result.returncode != 0:
        print(f"[ERROR] Step failed: {description} (exit code {result.returncode})")
        sys.exit(result.returncode)
    print(f"[SUCCESS] Step completed: {description}")


def print_summary(db_path: Path) -> None:
    print(f"\n{'=' * 20} Pipeline Execution Summary {'=' * 20}")
    if not db_path.exists():
        print(f"[ERROR] Database file {db_path} does not exist!")
        return

    con = duckdb.connect(str(db_path))
    try:
        print("\n--- Camada Raw ---")
        for table in ["bancos", "empregados", "reclamacoes"]:
            count = con.execute(f"SELECT count(*) FROM raw.{table}").fetchone()[0]
            print(f"  raw.{table}: {count} registros")

        print("\n--- Camada Trusted ---")
        for table in ["tr_bancos", "tr_empregados", "tr_reclamacoes"]:
            count = con.execute(f"SELECT count(*) FROM trusted.{table}").fetchone()[0]
            print(f"  trusted.{table}: {count} registros")

        print("\n--- Camada Delivery ---")
        df_del = con.execute("""
            SELECT
                COUNT(*) as total_bancos,
                COUNT(reclamacao_total) as com_reclamacoes,
                COUNT(avaliacao_geral) as com_glassdoor,
                SUM(reclamacao_total) as total_reclamacoes,
                AVG(avaliacao_geral) as media_avaliacao_geral
            FROM delivery.bancos_indicadores
        """).df()
        print(df_del.to_string(index=False))

        print("\n--- Arquivos Parquet Gerados ---")
        data_dir = db_path.parent
        for folder in ["trusted", "delivery"]:
            parquet_files = list((data_dir / folder).glob("*.parquet"))
            for p in parquet_files:
                size_kb = p.stat().st_size / 1024
                print(f"  {p.relative_to(data_dir.parent)} ({size_kb:.2f} KB)")

    finally:
        con.close()


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    db_path = project_root / "data" / "database.duckdb"

    dbt_bin = shutil.which("dbt") or str(Path(sys.executable).parent / "dbt") or "dbt"
    dbt_cmd = [dbt_bin]

    # Step 1: Raw ingestion
    run_step(
        "1. Ingestão RAW em Python",
        [sys.executable, "scripts/ingest_raw.py"],
        cwd=project_root,
    )

    # Step 2: DBT Seed
    run_step(
        "2. Carga de Seeds DBT",
        [*dbt_cmd, "seed", "--no-partial-parse", "--profiles-dir", "."],
        cwd=project_root,
    )

    # Step 3: DBT Run
    run_step(
        "3. Execução dos Modelos DBT",
        [*dbt_cmd, "run", "--no-partial-parse", "--profiles-dir", "."],
        cwd=project_root,
    )

    # Step 4: DBT Test
    run_step(
        "4. Execução dos Testes DBT",
        [*dbt_cmd, "test", "--no-partial-parse", "--profiles-dir", "."],
        cwd=project_root,
    )

    # Summary
    print_summary(db_path)
    print("\n[OK] Pipeline concluído com sucesso!")


if __name__ == "__main__":
    main()
