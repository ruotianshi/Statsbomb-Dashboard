"""
normalize.py
------------
提供数据标准化和百分位排名计算函数
雷达图使用百分位排名（在同赛季同联赛球员中的相对位置）
"""

import numpy as np
import pandas as pd
from scipy import stats


def percentile_rank(series: pd.Series, value: float) -> float:
    """
    计算 value 在 series 中的百分位排名 (0~100)
    使用 scipy.stats.percentileofscore，kind='rank'
    """
    clean = series.dropna()
    if len(clean) == 0 or pd.isna(value):
        return 50.0
    return float(stats.percentileofscore(clean, value, kind="rank"))


def compute_percentile_row(
    player_row: pd.Series,
    all_df: pd.DataFrame,
    metrics: list[str],
    min_minutes: int = 0,
) -> dict[str, float]:
    """
    计算单名球员在 metrics 中每个指标的百分位排名
    all_df: 同联赛同赛季球员池（已经过 min_minutes 过滤）
    返回 {metric: percentile_value}
    """
    if min_minutes > 0:
        pool = all_df[all_df["player_season_minutes"] >= min_minutes]
    else:
        pool = all_df

    result = {}
    for m in metrics:
        if m not in all_df.columns or m not in player_row.index:
            result[m] = 50.0
            continue
        val = player_row.get(m, np.nan)
        result[m] = percentile_rank(pool[m], val)
    return result


def minmax_normalize(series: pd.Series) -> pd.Series:
    """Min-Max 归一化到 [0, 1]"""
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series([0.5] * len(series), index=series.index)
    return (series - mn) / (mx - mn)


def normalize_df_columns(
    df: pd.DataFrame,
    metrics: list[str],
) -> pd.DataFrame:
    """
    对 DataFrame 中的指定列进行 Min-Max 归一化
    返回新 DataFrame，原数据不修改
    """
    result = df.copy()
    for m in metrics:
        if m in result.columns:
            result[m] = minmax_normalize(result[m])
    return result


def compute_league_percentiles(
    df: pd.DataFrame,
    metrics: list[str],
    min_minutes: int = 0,
) -> pd.DataFrame:
    """
    为 DataFrame 中所有球员批量计算百分位排名
    新列名格式: {metric}_pct
    """
    if min_minutes > 0:
        pool = df[df["player_season_minutes"] >= min_minutes]
    else:
        pool = df

    result = df.copy()
    for m in metrics:
        if m not in df.columns:
            continue
        result[f"{m}_pct"] = df[m].apply(
            lambda v: percentile_rank(pool[m], v)
        )
    return result
