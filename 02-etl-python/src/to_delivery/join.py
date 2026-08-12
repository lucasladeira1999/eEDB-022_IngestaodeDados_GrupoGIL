import pandas as pd
from rapidfuzz import fuzz, process

from to_delivery.acronyms import resolve_acronym

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


def aggregate_reclamacoes(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["has_cnpj"] = df["cnpj_norm"].ne("") & df["cnpj_norm"].notna()
    by_cnpj = (
        df[df["has_cnpj"]]
        .groupby("cnpj_norm")
        .agg(
            total_reclamacoes=("Quantidade total de reclamações", "sum"),
            media_indice=("indice", "mean"),
            trimestres=("Trimestre", "nunique"),
            total_clientes=("Quantidade total de clientes \x96 CCS e SCR", "sum"),
            total_procedentes=("Quantidade de reclamações reguladas procedentes", "sum"),
        )
        .reset_index()
    )
    by_cnpj["join_key"] = by_cnpj["cnpj_norm"]
    by_cnpj["join_type"] = "cnpj"
    by_nome = (
        df[~df["has_cnpj"]]
        .groupby("nome_norm")
        .agg(
            total_reclamacoes=("Quantidade total de reclamações", "sum"),
            media_indice=("indice", "mean"),
            trimestres=("Trimestre", "nunique"),
            total_clientes=("Quantidade total de clientes \x96 CCS e SCR", "sum"),
            total_procedentes=("Quantidade de reclamações reguladas procedentes", "sum"),
        )
        .reset_index()
    )
    by_nome["join_key"] = by_nome["nome_norm"]
    by_nome["join_type"] = "nome"
    result = pd.concat([by_cnpj, by_nome], ignore_index=True)
    result["taxa_reclamacao_por_cliente"] = (
        result["total_reclamacoes"] / result["total_clientes"].replace(0, pd.NA)
    )
    result["pct_reclamacoes_procedentes"] = (
        result["total_procedentes"] / result["total_reclamacoes"].replace(0, pd.NA)
    )
    return result


REC_METRIC_COLS = [
    "total_reclamacoes",
    "media_indice",
    "trimestres",
    "taxa_reclamacao_por_cliente",
    "pct_reclamacoes_procedentes",
]


def join_bancos_reclamacoes(
    df_bancos: pd.DataFrame,
    df_rec_agg: pd.DataFrame,
) -> pd.DataFrame:
    rec_by_cnpj = df_rec_agg[df_rec_agg["join_type"] == "cnpj"]
    rec_by_nome = df_rec_agg[df_rec_agg["join_type"] == "nome"].copy()
    rec_by_nome["canonical"] = rec_by_nome["join_key"].apply(resolve_acronym)
    step1 = pd.merge(
        df_bancos,
        rec_by_cnpj[["join_key", *REC_METRIC_COLS]],
        left_on="cnpj_norm",
        right_on="join_key",
        how="left",
    ).drop(columns=["join_key"])
    unmatched = step1[step1["total_reclamacoes"].isna()].copy()
    if not unmatched.empty and not rec_by_nome.empty:
        canonical_to_key = dict(zip(rec_by_nome["canonical"], rec_by_nome["join_key"]))
        lookup = rec_by_nome.set_index("join_key")
        choices = list(canonical_to_key.keys())
        mapped = []
        for nome in unmatched["nome_norm"]:
            resolved = resolve_acronym(nome)
            if resolved in choices:
                mapped.append(canonical_to_key[resolved])
                choices.remove(resolved)
                continue
            best = process.extractOne(
                resolved, choices, scorer=fuzz.WRatio, score_cutoff=80
            )
            if best:
                mapped.append(canonical_to_key[best[0]])
                choices.remove(best[0])
            else:
                mapped.append(None)
        for col in REC_METRIC_COLS:
            unmatched[col] = [
                lookup.at[m, col] if m and m in lookup.index else None for m in mapped
            ]
    result = pd.concat(
        [step1[step1["total_reclamacoes"].notna()], unmatched],
        ignore_index=True,
    )
    return result


def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    has_cnpj = df["cnpj_norm"].ne("") & df["cnpj_norm"].notna()
    with_cnpj = df[has_cnpj].drop_duplicates(subset=["cnpj_norm"], keep="first")
    without_cnpj = df[~has_cnpj].drop_duplicates(subset=["nome_norm"], keep="first")
    return pd.concat([with_cnpj, without_cnpj], ignore_index=True)


def join_empregados(
    df: pd.DataFrame,
    df_empregados: pd.DataFrame,
) -> pd.DataFrame:
    rating_cols = [c for c in RATING_COLS if c in df_empregados.columns]
    emp_key = df_empregados.dropna(subset=["cnpj_norm"])
    emp_key = emp_key[emp_key["cnpj_norm"] != ""]
    result = df.copy()
    if not emp_key.empty:
        result = pd.merge(
            result,
            emp_key[["cnpj_norm", *rating_cols]],
            on="cnpj_norm",
            how="left",
        )
    remaining = result["Geral"].isna()
    if remaining.any() and not df_empregados.empty:
        df_emp_resolved = df_empregados.copy()
        df_emp_resolved["canonical"] = df_emp_resolved["nome_norm"].apply(
            resolve_acronym
        )
        available = df_emp_resolved.copy()
        for idx in result[remaining].index:
            nome = result.at[idx, "nome_norm"]
            resolved = resolve_acronym(nome)
            exact = available[available["canonical"] == resolved]
            if not exact.empty:
                row = exact.iloc[0]
                available = available.drop(exact.index[0])
            else:
                if available.empty:
                    break
                best = process.extractOne(
                    resolved,
                    available["canonical"].tolist(),
                    scorer=fuzz.WRatio,
                    score_cutoff=90,
                )
                if best:
                    match_idx = available[available["canonical"] == best[0]].index[0]
                    row = available.loc[match_idx]
                    available = available.drop(match_idx)
                else:
                    continue
            for col in rating_cols:
                result.at[idx, col] = row[col]
    return result
