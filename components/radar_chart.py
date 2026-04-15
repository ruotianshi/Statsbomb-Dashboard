"""
radar_chart.py
--------------
生成球员属性雷达图（Plotly Scatterpolar）
支持：
  - 自定义指标选择
  - 百分位排名标准化（在联赛球员池中的相对位置）
  - 双球员叠加对比
"""

import numpy as np
import plotly.graph_objects as go

from utils.metrics_config import COLORS, PLOTLY_BASE_LAYOUT, METRIC_LABELS
from utils.normalize import compute_percentile_row


def build_radar_chart(
    player_row,
    all_df,
    metrics: list[str],
    normalize: bool = True,
    min_minutes: int = 500,
    compare_row=None,
    compare_name: str = "Compare",
) -> go.Figure:
    """
    构建雷达图 Figure
    
    参数
    ----
    player_row   : 主球员的 Series（一行数据）
    all_df       : 同联赛同赛季所有球员 DataFrame（用于百分位计算）
    metrics      : 选中的指标列表（最多建议 10 个）
    normalize    : True → 百分位排名 (0-100)  False → 原始值 min-max 归一化到 0-100
    min_minutes  : 计算百分位时的最低上场分钟数阈值
    compare_row  : （可选）对比球员的 Series
    compare_name : 对比球员显示名
    """
    if not metrics:
        return go.Figure()

    # 过滤掉 DataFrame 中不存在的列
    valid_metrics = [m for m in metrics if m in all_df.columns]
    if not valid_metrics:
        return go.Figure()

    labels = [METRIC_LABELS.get(m, m.replace("player_season_", "").replace("_", " ").title())
              for m in valid_metrics]

    # ── 主球员数值 ───────────────────────────────
    main_values = _get_values(player_row, all_df, valid_metrics, normalize, min_minutes)

    # 闭合雷达图（首尾相连）
    r_main     = main_values + [main_values[0]]
    theta      = labels + [labels[0]]

    fig = go.Figure()

    # ── 主球员轨迹 ───────────────────────────────
    player_display = str(player_row.get("player_known_name") or player_row.get("player_name", "Player"))

    fig.add_trace(go.Scatterpolar(
        r=r_main,
        theta=theta,
        fill="toself",
        fillcolor=f"rgba(0, 212, 170, 0.25)",
        line=dict(color=COLORS["primary"], width=2.5),
        name=player_display,
        hovertemplate="<b>%{theta}</b><br>Value: %{r:.1f}<extra></extra>",
    ))

    # ── 对比球员轨迹（可选）────────────────────────
    if compare_row is not None:
        cmp_values = _get_values(compare_row, all_df, valid_metrics, normalize, min_minutes)
        r_cmp = cmp_values + [cmp_values[0]]

        fig.add_trace(go.Scatterpolar(
            r=r_cmp,
            theta=theta,
            fill="toself",
            fillcolor=f"rgba(255, 107, 53, 0.20)",
            line=dict(color=COLORS["secondary"], width=2.5, dash="dot"),
            name=compare_name,
            hovertemplate="<b>%{theta}</b><br>Value: %{r:.1f}<extra></extra>",
        ))

    # ── 布局 ─────────────────────────────────────
    range_max = 100 if normalize else 100
    subtitle  = "Percentile Rank" if normalize else "Normalised (0–100)"

    # 基础布局：从 PLOTLY_BASE_LAYOUT 复制后单独覆盖 legend，避免重复键
    layout = {**PLOTLY_BASE_LAYOUT}
    layout.update(dict(
        title=dict(
            text=f"Player Attributes · <span style='font-size:11px;color:{COLORS['muted']}'>{subtitle}</span>",
            font=dict(size=14, color=COLORS["text"]),
            x=0.5,
        ),
        polar=dict(
            bgcolor=COLORS["bg_card"],
            radialaxis=dict(
                visible=True,
                range=[0, range_max],
                tickfont=dict(size=9, color=COLORS["muted"]),
                gridcolor=COLORS["grid"],
                linecolor=COLORS["grid"],
                tickvals=[20, 40, 60, 80, 100],
            ),
            angularaxis=dict(
                tickfont=dict(size=10, color=COLORS["text"]),
                gridcolor=COLORS["grid"],
                linecolor=COLORS["grid"],
            ),
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5,
            font=dict(size=11),
        ),
        height=460,
        margin=dict(l=50, r=50, t=60, b=60),
    ))
    fig.update_layout(**layout)

    return fig


def _get_values(
    row,
    all_df,
    metrics: list[str],
    normalize: bool,
    min_minutes: int,
) -> list[float]:
    """提取并归一化某球员在各指标的值"""
    if normalize:
        pct_dict = compute_percentile_row(row, all_df, metrics, min_minutes)
        return [round(pct_dict.get(m, 50.0), 1) for m in metrics]
    else:
        # Min-Max 归一化到 0-100（使用整个 pool）
        values = []
        pool = all_df[all_df["player_season_minutes"] >= min_minutes] if min_minutes > 0 else all_df
        for m in metrics:
            val = row.get(m, np.nan)
            if np.isnan(val) if isinstance(val, float) else False:
                values.append(50.0)
                continue
            col = pool[m].dropna()
            mn, mx = col.min(), col.max()
            if mx == mn:
                values.append(50.0)
            else:
                values.append(round(float((val - mn) / (mx - mn) * 100), 1))
        return values
