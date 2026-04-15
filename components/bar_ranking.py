"""
bar_ranking.py
--------------
生成联赛球员指标排名横向柱状图（Plotly）
核心原则：目标球员（highlight_player_id）始终出现在图中，
          不论其数值是否进入 top_n，甚至值为 0 或 NaN 也强制显示
"""

import pandas as pd
import plotly.graph_objects as go

from utils.image_helper import get_player_display_name
from utils.metrics_config import COLORS, PLOTLY_BASE_LAYOUT, METRIC_LABELS


def build_bar_ranking(
    all_df: pd.DataFrame,
    metric: str,
    highlight_player_id,
    position_filter: list[str] | None = None,
    min_minutes: int = 500,
    top_n: int = 25,
    ascending: bool = False,
) -> go.Figure:
    """
    构建联赛排名横向柱状图

    核心原则：
      - ascending=False（默认）: 显示 top_n 最高值，最高值在视觉顶部
      - ascending=True          : 显示 bottom_n 最低值，最低值在视觉顶部
      - 目标球员始终出现在图中
      - Plotly 规则：DataFrame row[0] 在图表底部，row[-1] 在顶部
        → 降序想让最大在顶：用 ascending 排序让最大值在 row[-1]
        → 升序想让最小在顶：用 descending 排序让最小值在 row[-1]
    """
    if metric not in all_df.columns:
        return go.Figure()

    df = all_df.copy()

    # ── Step 1: display_name，过滤无效名字 ─────────────
    df["display_name"] = df.apply(get_player_display_name, axis=1)
    df = df[
        df["display_name"].notna() &
        (df["display_name"] != "Unknown") &
        (df["display_name"].str.strip() != "")
    ]
    if df.empty:
        return go.Figure()

    # ── Step 2: 单独保存目标球员行 ─────────────────────
    hl_df = pd.DataFrame()
    if highlight_player_id is not None:
        hl_df = df[df["player_id"] == highlight_player_id].copy()
        if not hl_df.empty and pd.isna(hl_df[metric].iloc[0]):
            hl_df[metric] = 0.0

    # ── Step 3: 联赛池（排除目标球员）──────────────────
    pool = df[df["player_id"] != highlight_player_id].copy() \
           if highlight_player_id is not None else df.copy()

    pool = pool[pool["player_season_minutes"] >= min_minutes]

    if position_filter and "primary_position" in pool.columns:
        pool = pool[pool["primary_position"].isin(position_filter)]

    # 只排除 NaN；保留 0 值（0 是合法的指标值）
    pool = pool.dropna(subset=[metric])

    if pool.empty and hl_df.empty:
        return go.Figure()

    actual_n = min(top_n, len(pool))

    # ── Step 4: 选人 ────────────────────────────────────
    # ascending=False → 取最高 n 个值（top performers）
    # ascending=True  → 取最低 n 个值（bottom performers / lower-is-better metrics）
    if not ascending:
        # 降序：取 top_n 最高值
        # 用 ascending=True sort + tail() 确保 row[-1]=最高，便于后续直接显示
        selected = pool.sort_values(metric, ascending=True).tail(actual_n).copy()
    else:
        # 升序：取 bottom_n 最低值
        # 用 descending sort + tail() 确保 row[-1]=最低，便于后续直接显示
        selected = pool.sort_values(metric, ascending=False).tail(actual_n).copy()

    # ── Step 5: 强制加入目标球员 ─────────────────────────
    if not hl_df.empty and highlight_player_id not in selected["player_id"].values:
        selected = pd.concat([selected, hl_df.iloc[[0]]], ignore_index=True)
        # 重新按选人逻辑排序，保持 row[-1] = 视觉顶部的值
        if not ascending:
            selected = selected.sort_values(metric, ascending=True)
        else:
            selected = selected.sort_values(metric, ascending=False)

    top_df = selected.reset_index(drop=True)

    if top_df.empty:
        return go.Figure()

    # ── Step 6: 排名计算（始终 rank 1 = 最好）────────────
    metric_label = METRIC_LABELS.get(
        metric,
        metric.replace("player_season_", "").replace("_", " ").title()
    )
    rank_label = ""
    if not hl_df.empty:
        full_pool = df[df["player_season_minutes"] >= min_minutes].copy()
        if position_filter and "primary_position" in full_pool.columns:
            hl_pos = hl_df["primary_position"].iloc[0] if "primary_position" in hl_df.columns else None
            if hl_pos and hl_pos in position_filter:
                full_pool = full_pool[full_pool["primary_position"].isin(position_filter)]
        full_pool = full_pool.dropna(subset=[metric])
        hl_val = float(hl_df[metric].iloc[0])
        if ascending:
            # lower is better → rank 1 = lowest value
            rank  = int((full_pool[metric] < hl_val).sum()) + 1
        else:
            # higher is better → rank 1 = highest value
            rank  = int((full_pool[metric] > hl_val).sum()) + 1
        total = len(full_pool)
        rank_label = f"Rank {rank} / {total}"

    # ── Step 7: 颜色 ─────────────────────────────────────
    bar_colors = [
        COLORS["primary"] if pid == highlight_player_id else COLORS["muted"]
        for pid in top_df["player_id"]
    ]
    opacity = [
        1.0 if pid == highlight_player_id else 0.55
        for pid in top_df["player_id"]
    ]

    # ── Step 8: hover ────────────────────────────────────
    hover_texts = []
    for name, val, (_, r) in zip(top_df["display_name"], top_df[metric], top_df.iterrows()):
        mins     = r.get("player_season_minutes", 0)
        mins_str = f"{int(mins):,}" if pd.notna(mins) else "N/A"
        text     = (
            f"<b>{name}</b><br>{r.get('team_name', '')}<br>"
            f"{metric_label}: <b>{val:.3f}</b><br>"
            f"Minutes: {mins_str}"
        )
        if r.get("player_id") == highlight_player_id and rank_label:
            text += f"<br><i>{rank_label}</i>"
        hover_texts.append(text)

    # ── Step 9: x 轴上限截断，防止极端离群值压扁其他柱子 ──
    # 用所有显示值的 95 百分位作为参考上限（但保留目标球员完整柱子显示）
    import numpy as np
    non_hl_vals = top_df.loc[top_df["player_id"] != highlight_player_id, metric].dropna()
    hl_val_display = float(hl_df[metric].iloc[0]) if not hl_df.empty else None
    if len(non_hl_vals) > 3:
        p95 = float(np.percentile(non_hl_vals, 95))
        all_display_max = max(non_hl_vals.max(), hl_val_display or 0)
        # 仅当最大值超过 p95 的 2.5 倍时才截断（避免过度裁剪）
        x_max = all_display_max * 1.12
        if all_display_max > p95 * 2.5:
            x_max = p95 * 1.4
    else:
        x_max = None

    # ── Step 10: 图表 ────────────────────────────────────
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=top_df[metric],
        y=top_df["display_name"],
        orientation="h",
        marker=dict(color=bar_colors, opacity=opacity, line=dict(width=0)),
        text=[f"{v:.3f}" for v in top_df[metric]],
        textposition="outside",
        textfont=dict(size=10, color=COLORS["text"]),
        hovertext=hover_texts,
        hoverinfo="text",
        showlegend=False,
    ))

    # 目标球员参考线
    hl_in_chart = top_df[top_df["player_id"] == highlight_player_id]
    if not hl_in_chart.empty:
        hl_val_line = float(hl_in_chart[metric].iloc[0])
        hl_name     = hl_in_chart["display_name"].iloc[0]
        ann_text    = f"  {hl_name}"
        if rank_label:
            ann_text += f"  ({rank_label})"
        fig.add_vline(
            x=hl_val_line,
            line=dict(color=COLORS["primary"], width=1.5, dash="dot"),
            annotation_text=ann_text,
            annotation_position="top right",
            annotation_font=dict(color=COLORS["primary"], size=10),
        )

    direction_note = "↑ lowest at top" if ascending else "↓ highest at top"
    layout = {**PLOTLY_BASE_LAYOUT}
    layout.update(dict(
        title=dict(
            text=(
                f"League Ranking · <b>{metric_label}</b>"
                f"<span style='font-size:10px;color:{COLORS['muted']}'>"
                f"  (min {min_minutes} min · top {top_n} · {direction_note})</span>"
            ),
            font=dict(size=13, color=COLORS["text"]),
            x=0,
        ),
        xaxis=dict(
            title=metric_label,
            range=[0, x_max] if x_max else None,
            gridcolor=COLORS["grid"],
            linecolor=COLORS["grid"],
            tickcolor=COLORS["muted"],
            tickfont=dict(size=10),
            zeroline=False,
        ),
        yaxis=dict(
            gridcolor="rgba(0,0,0,0)",
            linecolor=COLORS["grid"],
            tickfont=dict(size=10, color=COLORS["text"]),
            automargin=True,
        ),
        bargap=0.3,
        height=max(350, len(top_df) * 28),
        margin=dict(l=10, r=80, t=50, b=40),
    ))
    fig.update_layout(**layout)
    return fig


def build_obv_breakdown(player_row, all_df, min_minutes: int = 500) -> go.Figure:
    """
    生成球员 OBV 构成横向条形图（正负分两侧）
    展示 Pass / Shot / Defensive Action / Dribble & Carry / GK 各维度贡献
    """
    obv_cols = {
        "OBV Pass":          "player_season_obv_pass_90",
        "OBV Shot":          "player_season_obv_shot_90",
        "OBV Def Action":    "player_season_obv_defensive_action_90",
        "OBV Dribble/Carry": "player_season_obv_dribble_carry_90",
        "OBV GK":            "player_season_obv_gk_90",
    }

    valid = {k: v for k, v in obv_cols.items() if v in all_df.columns}
    if not valid:
        return go.Figure()

    pool = all_df[all_df["player_season_minutes"] >= min_minutes] if min_minutes > 0 else all_df

    labels, player_vals, league_avg = [], [], []
    for label, col in valid.items():
        val = player_row.get(col, 0) or 0
        avg = pool[col].mean() if col in pool.columns else 0
        labels.append(label)
        player_vals.append(round(float(val), 4))
        league_avg.append(round(float(avg), 4))

    colors_bar = [COLORS["primary"] if v >= 0 else COLORS["danger"] for v in player_vals]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=league_avg, y=labels,
        mode="markers",
        marker=dict(symbol="line-ns", color=COLORS["warning"], size=14,
                    line=dict(width=2, color=COLORS["warning"])),
        name="League Avg",
        hovertemplate="<b>%{y}</b><br>League Avg: %{x:.4f}<extra></extra>",
    ))

    fig.add_trace(go.Bar(
        x=player_vals, y=labels,
        orientation="h",
        marker=dict(color=colors_bar, opacity=0.85),
        name="Player",
        text=[f"{v:+.4f}" for v in player_vals],
        textposition="outside",
        textfont=dict(size=10, color=COLORS["text"]),
        hovertemplate="<b>%{y}</b><br>Value: %{x:.4f}<extra></extra>",
    ))

    layout = {**PLOTLY_BASE_LAYOUT}
    layout.update(dict(
        title=dict(text="OBV Breakdown (p90)", font=dict(size=13, color=COLORS["text"])),
        xaxis=dict(
            gridcolor=COLORS["grid"], linecolor=COLORS["grid"],
            zeroline=True, zerolinecolor=COLORS["muted"], zerolinewidth=1.5,
            tickfont=dict(size=10),
        ),
        yaxis=dict(gridcolor="rgba(0,0,0,0)", automargin=True, tickfont=dict(size=11)),
        barmode="overlay",
        height=280,
        margin=dict(l=10, r=70, t=40, b=20),
        legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"),
    ))
    fig.update_layout(**layout)
    return fig
