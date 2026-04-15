"""
pitch_viz.py
------------
所有基于球场的可视化组件，使用 mplsoccer 库
包含：
  - 射门分布图
  - 传球分布图（带箭头）
  - 过人尝试分布图
  - 防守行为分布图
  - 球员活动热力图
  - 阵型可视化（用于 Match Dashboard）
"""

import matplotlib
matplotlib.use("Agg")  # 非交互后端，适合 Streamlit

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from mplsoccer import Pitch, VerticalPitch

# ─────────────────────────────────────────────
# 全局颜色（与主题一致）
# ─────────────────────────────────────────────

PITCH_COLOR   = "#1a1d2e"
LINE_COLOR    = "#4a4e65"
BG_COLOR      = "#0e1117"
PRIMARY       = "#00d4aa"
SECONDARY     = "#ff6b35"
ACCENT        = "#4e9af1"
WARNING       = "#f7d716"
DANGER        = "#ff3b3b"
MUTED         = "#8b9bb4"

_PITCH_KWARGS = dict(
    pitch_type="statsbomb",
    pitch_color=PITCH_COLOR,
    line_color=LINE_COLOR,
    linewidth=1.2,
    corner_arcs=True,
)


def _base_fig(figsize=(8, 5.5), vertical=False):
    """创建带有统一背景色的 Figure"""
    fig, ax = plt.subplots(figsize=figsize, facecolor=BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    return fig, ax


# ─────────────────────────────────────────────
# 1. 射门分布图
# ─────────────────────────────────────────────

def plot_shots(
    shots_df: pd.DataFrame,
    player_name: str = "",
    figsize=(7, 5),
) -> plt.Figure:
    """
    绘制球员射门分布图（垂直球场，仅展示进攻半场）
    shots_df 列：x, y, outcome（goal/saved/missed/blocked），xg（可选）

    mplsoccer 坐标系：x 0-120，y 0-80
    """
    pitch = VerticalPitch(
        **_PITCH_KWARGS,
        half=True,          # 只显示半场
        goal_type="box",
    )
    fig, ax = pitch.draw(figsize=figsize)
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(PITCH_COLOR)

    if shots_df.empty:
        ax.text(40, 55, "No shot data available",
                ha="center", va="center", color=MUTED, fontsize=11)
        return fig

    # 按结果着色
    outcome_map = {
        "Goal":              {"color": PRIMARY,    "marker": "o",  "zorder": 5},
        "Saved":             {"color": ACCENT,     "marker": "o",  "zorder": 4},
        "Missed":            {"color": MUTED,      "marker": "x",  "zorder": 3},
        "Blocked":           {"color": SECONDARY,  "marker": "s",  "zorder": 3},
        "Post":              {"color": WARNING,    "marker": "D",  "zorder": 4},
    }

    legend_handles = []
    for outcome, style in outcome_map.items():
        mask = shots_df["outcome"].str.contains(outcome, case=False, na=False)
        sub  = shots_df[mask]
        if sub.empty:
            continue

        # 气泡大小 = xg 值（若无则固定大小）
        if "xg" in sub.columns:
            sizes = (sub["xg"].fillna(0.05) * 800).clip(40, 800)
        else:
            sizes = 120

        pitch.scatter(
            sub["x"], sub["y"],
            ax=ax,
            s=sizes,
            color=style["color"],
            marker=style["marker"],
            alpha=0.85,
            edgecolors="white",
            linewidth=0.4,
            zorder=style["zorder"],
        )
        legend_handles.append(
            mpatches.Patch(color=style["color"], label=f"{outcome} ({mask.sum()})")
        )

    # 图例
    ax.legend(
        handles=legend_handles,
        loc="lower left",
        fontsize=8,
        facecolor=PITCH_COLOR,
        edgecolor=LINE_COLOR,
        labelcolor="white",
        framealpha=0.85,
    )

    _set_title(ax, f"Shot Map", player_name)
    return fig


# ─────────────────────────────────────────────
# 2. 传球分布图（带箭头）
# ─────────────────────────────────────────────

def plot_passes(
    passes_df: pd.DataFrame,
    player_name: str = "",
    show_incomplete: bool = True,
    figsize=(8, 5.5),
) -> plt.Figure:
    """
    绘制球员传球分布图
    passes_df 列：x, y, end_x, end_y, outcome（Complete/Incomplete），
                  pass_type（可选）
    """
    pitch = Pitch(**_PITCH_KWARGS)
    fig, ax = pitch.draw(figsize=figsize)
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(PITCH_COLOR)

    if passes_df.empty:
        ax.text(60, 40, "No pass data available",
                ha="center", va="center", color=MUTED, fontsize=11)
        return fig

    complete   = passes_df[passes_df["outcome"].str.contains("Complete", case=False, na=True)]
    incomplete = passes_df[~passes_df["outcome"].str.contains("Complete", case=False, na=True)]

    # 完成传球 - 青绿箭头
    if not complete.empty:
        pitch.arrows(
            complete["x"], complete["y"],
            complete["end_x"], complete["end_y"],
            ax=ax,
            color=PRIMARY,
            alpha=0.55,
            width=1.2,
            headwidth=4,
            headlength=4,
            zorder=3,
        )

    # 未完成传球 - 橙色虚线
    if show_incomplete and not incomplete.empty:
        pitch.arrows(
            incomplete["x"], incomplete["y"],
            incomplete["end_x"], incomplete["end_y"],
            ax=ax,
            color=SECONDARY,
            alpha=0.45,
            width=0.8,
            headwidth=3,
            headlength=3,
            linestyle="dashed",
            zorder=2,
        )

    # 起点散点
    pitch.scatter(
        passes_df["x"], passes_df["y"],
        ax=ax,
        s=18, color="white", alpha=0.6, zorder=4,
    )

    # 图例
    handles = [
        mpatches.Patch(color=PRIMARY,    label=f"Complete ({len(complete)})"),
        mpatches.Patch(color=SECONDARY,  label=f"Incomplete ({len(incomplete)})"),
    ]
    ax.legend(handles=handles, loc="lower left", fontsize=8,
              facecolor=PITCH_COLOR, edgecolor=LINE_COLOR,
              labelcolor="white", framealpha=0.85)

    _set_title(ax, "Pass Map", player_name)
    return fig


# ─────────────────────────────────────────────
# 3. 过人尝试分布图
# ─────────────────────────────────────────────

def plot_dribbles(
    dribbles_df: pd.DataFrame,
    player_name: str = "",
    figsize=(8, 5.5),
) -> plt.Figure:
    """
    绘制过人尝试分布图
    dribbles_df 列：x, y, outcome（Complete/Incomplete）
    """
    pitch = Pitch(**_PITCH_KWARGS)
    fig, ax = pitch.draw(figsize=figsize)
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(PITCH_COLOR)

    if dribbles_df.empty:
        ax.text(60, 40, "No dribble data available",
                ha="center", va="center", color=MUTED, fontsize=11)
        return fig

    success = dribbles_df[dribbles_df["outcome"].str.contains("Complete", case=False, na=True)]
    failed  = dribbles_df[~dribbles_df["outcome"].str.contains("Complete", case=False, na=True)]

    if not success.empty:
        pitch.scatter(
            success["x"], success["y"], ax=ax,
            s=120, color=PRIMARY, marker="o",
            edgecolors="white", linewidth=0.5,
            alpha=0.85, zorder=4, label=f"Success ({len(success)})",
        )

    if not failed.empty:
        pitch.scatter(
            failed["x"], failed["y"], ax=ax,
            s=100, color=DANGER, marker="x",
            linewidths=1.5,
            alpha=0.75, zorder=4, label=f"Failed ({len(failed)})",
        )

    ax.legend(loc="lower left", fontsize=8,
              facecolor=PITCH_COLOR, edgecolor=LINE_COLOR,
              labelcolor="white", framealpha=0.85)
    _set_title(ax, "Dribble Map", player_name)
    return fig


# ─────────────────────────────────────────────
# 4. 防守行为分布图
# ─────────────────────────────────────────────

def plot_defensive_actions(
    def_df: pd.DataFrame,
    player_name: str = "",
    figsize=(8, 5.5),
) -> plt.Figure:
    """
    绘制防守行为分布图
    def_df 列：x, y, action_type（Tackle/Interception/Clearance/Block/Pressure）
    """
    pitch = Pitch(**_PITCH_KWARGS)
    fig, ax = pitch.draw(figsize=figsize)
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(PITCH_COLOR)

    if def_df.empty:
        ax.text(60, 40, "No defensive action data available",
                ha="center", va="center", color=MUTED, fontsize=11)
        return fig

    action_style = {
        "Tackle":        {"color": PRIMARY,   "marker": "o", "s": 110},
        "Interception":  {"color": ACCENT,    "marker": "D", "s": 100},
        "Clearance":     {"color": WARNING,   "marker": "s", "s": 95},
        "Block":         {"color": SECONDARY, "marker": "^", "s": 100},
        "Pressure":      {"color": MUTED,     "marker": ".", "s": 55},
    }

    handles = []
    for action, style in action_style.items():
        mask = def_df["action_type"].str.contains(action, case=False, na=False)
        sub  = def_df[mask]
        if sub.empty:
            continue
        pitch.scatter(
            sub["x"], sub["y"], ax=ax,
            s=style["s"], color=style["color"],
            marker=style["marker"],
            edgecolors="white", linewidth=0.4,
            alpha=0.8, zorder=4,
        )
        handles.append(mpatches.Patch(color=style["color"], label=f"{action} ({mask.sum()})"))

    if handles:
        ax.legend(handles=handles, loc="lower left", fontsize=8,
                  facecolor=PITCH_COLOR, edgecolor=LINE_COLOR,
                  labelcolor="white", framealpha=0.85)

    _set_title(ax, "Defensive Actions", player_name)
    return fig


# ─────────────────────────────────────────────
# 5. 球员活动热力图
# ─────────────────────────────────────────────

def plot_heatmap(
    events_df: pd.DataFrame,
    player_name: str = "",
    figsize=(8, 5.5),
) -> plt.Figure:
    """
    绘制球员活动热力图（KDE）
    events_df 列：x, y（任意事件的坐标）
    """
    pitch = Pitch(**_PITCH_KWARGS, line_alpha=0.5)
    fig, ax = pitch.draw(figsize=figsize)
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(PITCH_COLOR)

    if events_df.empty or len(events_df) < 5:
        ax.text(60, 40, "Insufficient data for heatmap",
                ha="center", va="center", color=MUTED, fontsize=11)
        return fig

    pitch.kdeplot(
        events_df["x"], events_df["y"],
        ax=ax,
        cmap="YlOrRd",
        fill=True,
        levels=50,
        alpha=0.7,
        bw_adjust=0.6,
        zorder=2,
    )
    _set_title(ax, "Activity Heatmap", player_name)
    return fig


# ─────────────────────────────────────────────
# 6. 阵型可视化（Match Dashboard 用）
# ─────────────────────────────────────────────

# StatsBomb 位置名称 → 球场坐标映射（标准 120×80 坐标系）
_SB_POSITION_COORDS = {
    # GK
    "Goalkeeper":             (5,  40),
    # Defenders
    "Right Back":             (20, 65),
    "Right Center Back":      (18, 55),
    "Center Back":            (18, 40),
    "Left Center Back":       (18, 25),
    "Left Back":              (20, 15),
    "Right Wing Back":        (30, 72),
    "Left Wing Back":         (30,  8),
    # Defensive / Central Mids
    "Defensive Midfield":     (38, 40),
    "Right Defensive Midfield":(38, 55),
    "Left Defensive Midfield": (38, 25),
    "Right Center Midfield":  (50, 58),
    "Center Midfield":        (50, 40),
    "Left Center Midfield":   (50, 22),
    # Attacking Mids / Wingers
    "Right Midfield":         (60, 68),
    "Left Midfield":          (60, 12),
    "Right Wing":             (72, 68),
    "Left Wing":              (72, 12),
    "Attacking Midfield":     (65, 40),
    "Right Attacking Midfield":(65, 58),
    "Left Attacking Midfield": (65, 22),
    # Forwards
    "Right Center Forward":   (85, 55),
    "Center Forward":         (88, 40),
    "Left Center Forward":    (85, 25),
    "Secondary Striker":      (78, 40),
}

_FALLBACK_Y_BY_IDX = [72, 58, 40, 22, 8]   # 找不到位置时的 y 坐标备选


def plot_lineup_pitch(
    home_lineup: pd.DataFrame,
    away_lineup: pd.DataFrame,
    home_team: str = "Home",
    away_team: str = "Away",
    home_sub_annotations: dict | None = None,
    away_sub_annotations: dict | None = None,
    figsize=(14, 9),
) -> plt.Figure:
    """
    绘制双队首发阵型图
    home/away_lineup 需包含列：
        player_name, position_name（字符串，StatsBomb 位置名）, jersey_number

    使用两个纵向球场分别展示主队和客队。
    """
    fig, axes = plt.subplots(1, 2, figsize=figsize, facecolor=BG_COLOR)
    if not isinstance(axes, np.ndarray):
        axes = np.array([axes])

    pitch = VerticalPitch(**_PITCH_KWARGS, half=False)
    for ax in axes:
        pitch.draw(ax=ax)
        ax.set_facecolor(PITCH_COLOR)

    left_ax, right_ax = axes[0], axes[1]

    left_ax.text(
        40, 122, home_team,
        ha="center", va="bottom",
        color=PRIMARY, fontsize=12, fontweight="bold", alpha=0.95,
    )
    right_ax.text(
        40, 122, away_team,
        ha="center", va="bottom",
        color=SECONDARY, fontsize=12, fontweight="bold", alpha=0.95,
    )

    _draw_players_on_pitch(
        left_ax,
        home_lineup,
        mirror=False,
        color=PRIMARY,
        text_color="white",
        sub_annotations=home_sub_annotations,
        vertical=True,
    )

    _draw_players_on_pitch(
        right_ax,
        away_lineup,
        mirror=False,
        color=SECONDARY,
        text_color="white",
        sub_annotations=away_sub_annotations,
        vertical=True,
    )

    plt.tight_layout(pad=1.0, w_pad=2.0)
    return fig


def _draw_players_on_pitch(
    ax,
    lineup_df: pd.DataFrame,
    mirror: bool,
    color: str,
    text_color: str,
    sub_annotations: dict | None = None,
    vertical: bool = False,
):
    """在球场上绘制一支球队的球员节点"""
    if lineup_df is None or lineup_df.empty:
        return

    # 确定位置列名（StatsBomb lineups 中 position 可能嵌套）
    pos_col  = "position_name" if "position_name" in lineup_df.columns else "position"
    if "player_name" in lineup_df.columns:
        name_col = "player_name"
    elif "player_nickname" in lineup_df.columns:
        name_col = "player_nickname"
    elif "player" in lineup_df.columns:
        name_col = "player"
    elif "player_id" in lineup_df.columns:
        name_col = "player_id"
    else:
        name_col = lineup_df.columns[0]
    num_col  = "jersey_number" if "jersey_number" in lineup_df.columns else None
    sub_annotations = sub_annotations or {}

    for idx, row in lineup_df.iterrows():
        pos_name = str(row.get(pos_col, ""))
        coords   = _SB_POSITION_COORDS.get(pos_name)

        if coords is None:
            # 找不到位置时按顺序排列在中场附近
            i = idx % len(_FALLBACK_Y_BY_IDX)
            coords = (50, _FALLBACK_Y_BY_IDX[i])

        x, y = coords
        if mirror:
            x = 120 - x     # 客队坐标镜像
        if vertical:
            x, y = y, x

        # 球员圆圈
        ax.scatter(x, y, s=420, color=color, zorder=5,
                   edgecolors="white", linewidths=1.2, alpha=0.92)

        # 号码
        if num_col and not pd.isna(row.get(num_col, np.nan)):
            ax.text(x, y, str(int(row[num_col])),
                    ha="center", va="center",
                    color="black", fontsize=7.5,
                    fontweight="bold", zorder=6)

        # 球员名（下方）
        player_name = str(row.get(name_col, ""))
        short_name  = _shorten_name(player_name)
        ax.text(x, y - 3.8, short_name,
                ha="center", va="top",
                color=text_color, fontsize=6.5,
                fontweight="500", zorder=6,
                bbox=dict(boxstyle="round,pad=0.15",
                          fc=PITCH_COLOR, ec="none", alpha=0.6))

        # 换人标注：主队显示在节点下方，客队同样显示在节点下方
        sub_note = sub_annotations.get(_normalize_name_key(player_name))
        if sub_note:
            replacement = sub_note.get("replacement", "")
            reason = sub_note.get("reason", "")
            minute = sub_note.get("minute", "")
            replacement_short = _shorten_name(replacement) if replacement else "Sub"
            reason_lower = str(reason).strip().lower()
            is_injury = "injury" in reason_lower
            signal = "✚" if is_injury else "→"
            minute_part = f"{minute}' " if minute else ""
            ax.text(
                x,
                y - 7.2,
                f"{minute_part}{signal} {replacement_short}",
                ha="center",
                va="top",
                color="#ff5a5a" if is_injury else "#c7d2e2",
                fontsize=5.6,
                zorder=6,
                bbox=dict(boxstyle="round,pad=0.12", fc=BG_COLOR, ec="none", alpha=0.72),
            )


def _shorten_name(full_name: str) -> str:
    """将全名缩短：'Lionel Messi' → 'L. Messi'"""
    parts = full_name.strip().split()
    if len(parts) <= 1:
        return full_name
    return f"{parts[0][0]}. {' '.join(parts[1:])}"


def _normalize_name_key(value: str) -> str:
    return "".join(ch for ch in str(value).strip().lower() if ch.isalnum())


# ─────────────────────────────────────────────
# 辅助
# ─────────────────────────────────────────────

def _set_title(ax, chart_type: str, player_name: str):
    """统一标题样式"""
    title = f"{player_name}  ·  {chart_type}" if player_name else chart_type
    ax.set_title(title, color="white", fontsize=11,
                 fontweight="600", pad=8, loc="left")


def fig_to_streamlit(fig: plt.Figure):
    """
    将 matplotlib Figure 转为 Streamlit 可显示的格式
    使用方法：st.pyplot(fig_to_streamlit(fig))
    实际上直接返回 fig，Streamlit 的 st.pyplot() 接受 Figure 对象
    """
    plt.tight_layout(pad=0.5)
    return fig
