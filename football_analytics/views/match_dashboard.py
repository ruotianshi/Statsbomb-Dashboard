"""
match_dashboard.py
------------------
Match Dashboard 视图
包含：
  1. 比赛 Header（队名、队徽、比分、场地、裁判、主帅）
  2. Tab 1 - Team Stats：两队指标对比（进度条式 + 分组卡片）
  3. Tab 2 - Lineups：阵型可视化（mplsoccer pitch）+ 替补列表
  4. Tab 3 - Set Pieces：定位球专项数据
  5. Tab 4 - OBV：OBV 分解对比
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.pitch_viz import fig_to_streamlit, plot_lineup_pitch
from utils.data_loader import (
    load_competitions,
    load_events,
    load_lineups,
    load_matches,
    load_team_match_stats,
)
from utils.image_helper import load_team_image
from utils.metrics_config import COLORS, PLOTLY_BASE_LAYOUT


# ─────────────────────────────────────────────
# 指标分组（用于 Tab 展示）
# ─────────────────────────────────────────────

MATCH_STAT_GROUPS = {
    "Attacking": [
        ("team_match_np_xg",            "NP xG"),
        ("team_match_op_xg",            "OP xG"),
        ("team_match_sp_xg",            "SP xG"),
        ("team_match_np_xg_per_shot",   "NP xG / Shot"),
        ("team_match_np_shots",         "NP Shots"),
        ("team_match_op_shots",         "OP Shots"),
        ("team_match_deep_completions", "Deep Completions"),
        ("team_match_passes_inside_box","Passes in Box"),
        ("team_match_counter_attacking_shots", "Counter Shots"),
        ("team_match_high_press_shots", "High Press Shots"),
    ],
    "Defending": [
        ("team_match_np_xg_conceded",       "NP xG Conceded"),
        ("team_match_ppda",                 "PPDA"),
        ("team_match_defensive_distance",   "Defensive Distance"),
        ("team_match_pressure_regains",     "Pressure Regains"),
        ("team_match_fhalf_pressures_ratio","F-Half Pressure %"),
        ("team_match_deep_completions_conceded","Deep Comp Conceded"),
    ],
    "Possession": [
        ("team_match_possession",       "Possession %"),
        ("team_match_passing_ratio",    "Pass Completion %"),
        ("team_match_directness",       "Directness"),
        ("team_match_gk_pass_distance", "GK Pass Distance"),
        ("team_match_op_passes",        "OP Passes"),
        ("team_match_pressures",        "Pressures"),
    ],
    "OBV": [
        ("team_match_obv",                  "OBV Total"),
        ("team_match_obv_pass",             "OBV Pass"),
        ("team_match_obv_shot",             "OBV Shot"),
        ("team_match_obv_defensive_action", "OBV Def Action"),
        ("team_match_obv_dribble_carry",    "OBV Dribble/Carry"),
    ],
    "Set Pieces": [
        ("team_match_corners",              "Corners"),
        ("team_match_corner_xg",            "Corner xG"),
        ("team_match_free_kicks",           "Free Kicks"),
        ("team_match_free_kick_xg",         "Free Kick xG"),
        ("team_match_direct_free_kicks",    "Direct FK"),
        ("team_match_direct_free_kick_xg",  "Direct FK xG"),
        ("team_match_throw_ins",            "Throw-ins"),
        ("team_match_sp_goals",             "SP Goals"),
        ("team_match_penalties_won",        "Penalties Won"),
    ],
}


# ─────────────────────────────────────────────
# 主入口
# ─────────────────────────────────────────────

def render():
    _render_sidebar_filters()

    comp_id   = st.session_state.get("md_competition_id")
    season_id = st.session_state.get("md_season_id")
    match_id  = st.session_state.get("md_match_id")

    if not comp_id or not season_id:
        _render_welcome()
        return

    if match_id is None:
        _render_welcome()
        return

    # 加载数据
    with st.spinner("Loading match data..."):
        matches_df   = load_matches(comp_id, season_id)
        match_stats  = load_team_match_stats(match_id)
        lineups_dict = load_lineups(match_id)
        events_df    = load_events(match_id)

    if matches_df.empty:
        st.warning("No match data available.")
        return

    # 找到对应的比赛行
    match_rows = matches_df[matches_df["match_id"] == match_id]
    if match_rows.empty:
        st.warning("Match not found.")
        return
    match_row = match_rows.iloc[0]

    # ── 主内容 ────────────────────────────────
    _render_match_header(match_row, match_stats)

    st.markdown('<hr style="border:1px solid #2a2d3e; margin:14px 0">', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Team Stats",
        "⚽ Lineups",
        "🎯 Set Pieces",
        "📈 OBV",
    ])

    with tab1:
        _render_team_stats(match_stats, match_row)

    with tab2:
        _render_lineups(lineups_dict, match_row, match_stats, events_df)

    with tab3:
        _render_set_pieces(match_stats)

    with tab4:
        _render_obv_tab(match_stats)


# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────

def _render_sidebar_filters():
    with st.sidebar:
        st.markdown("### 🔍 Data Filters")

        comps_df = load_competitions()
        if comps_df.empty:
            return

        comp_names   = sorted(comps_df["competition_name"].unique().tolist())
        default_comp = st.session_state.get("md_competition_name", comp_names[0])
        if default_comp not in comp_names:
            default_comp = comp_names[0]

        comp_name = st.selectbox("Competition", comp_names,
                                 index=comp_names.index(default_comp),
                                 key="md_comp_select")
        comp_id = int(comps_df[comps_df["competition_name"] == comp_name]["competition_id"].iloc[0])

        season_opts = (comps_df[comps_df["competition_name"] == comp_name]
                       [["season_id", "season_name"]].drop_duplicates()
                       .sort_values("season_name", ascending=False))
        season_names   = season_opts["season_name"].tolist()
        default_season = st.session_state.get("md_season_name", season_names[0])
        if default_season not in season_names:
            default_season = season_names[0]

        season_name = st.selectbox("Season", season_names,
                                   index=season_names.index(default_season),
                                   key="md_season_select")
        season_id = int(season_opts[season_opts["season_name"] == season_name]["season_id"].iloc[0])

        st.divider()
        st.markdown("### ⚽ Match Selection")

        matches_df = load_matches(comp_id, season_id)

        if not matches_df.empty:
            # Team 筛选
            all_teams = _get_all_teams(matches_df)
            team_filter = st.selectbox("Filter by Team",
                                       ["All Teams"] + sorted(all_teams),
                                       key="md_team_filter")

            # 按球队过滤比赛
            if team_filter != "All Teams":
                filtered_matches = matches_df[
                    matches_df.apply(_match_involves_team, team=team_filter, axis=1)
                ]
            else:
                filtered_matches = matches_df

            # 生成比赛选项列表
            match_options = _build_match_options(filtered_matches)
            if match_options:
                match_labels = list(match_options.keys())
                prev_match   = st.session_state.get("md_match_id")
                default_mi   = 0
                for i, (lbl, mid) in enumerate(match_options.items()):
                    if mid == prev_match:
                        default_mi = i
                        break

                selected_label = st.selectbox("Select Match", match_labels,
                                              index=default_mi, key="md_match_select")
                selected_match_id = match_options[selected_label]
            else:
                selected_match_id = None
        else:
            selected_match_id = None

        st.session_state.update({
            "md_competition_id":   comp_id,
            "md_season_id":        season_id,
            "md_competition_name": comp_name,
            "md_season_name":      season_name,
            "md_match_id":         selected_match_id,
        })


def _get_all_teams(matches_df: pd.DataFrame) -> list:
    teams = set()
    for _, row in matches_df.iterrows():
        home_info = _extract_match_side_info(row, "home")
        away_info = _extract_match_side_info(row, "away")
        if home_info["name"]:
            teams.add(home_info["name"])
        if away_info["name"]:
            teams.add(away_info["name"])
    return [t for t in teams if t]


def _match_involves_team(row, team: str) -> bool:
    h_name = _extract_match_side_info(row, "home")["name"]
    a_name = _extract_match_side_info(row, "away")["name"]
    return team in (h_name, a_name)


def _build_match_options(matches_df: pd.DataFrame) -> dict:
    """生成比赛选项 {'2026-04-01 · Home 2 v 1 Away': match_id}"""
    opts = {}
    for _, row in matches_df.sort_values("match_date").iterrows():
        home_info = _extract_match_side_info(row, "home")
        away_info = _extract_match_side_info(row, "away")
        h_name = home_info["name"] or "Home"
        a_name = away_info["name"] or "Away"
        hs = _format_score_value(row.get("home_score"))
        as_ = _format_score_value(row.get("away_score"))
        dt  = str(row.get("match_date", ""))[:10]
        lbl = f"{dt} · {h_name} {hs} v {as_} {a_name}"
        opts[lbl] = row["match_id"]
    return opts


# ─────────────────────────────────────────────
# 比赛 Header
# ─────────────────────────────────────────────

def _render_match_header(match_row, match_stats: pd.DataFrame):
    home_info = _extract_match_side_info(match_row, "home")
    away_info = _extract_match_side_info(match_row, "away")
    h_name = home_info["name"] or "Home"
    a_name = away_info["name"] or "Away"
    h_id = _resolve_match_team_id(home_info["id"], h_name, match_stats)
    a_id = _resolve_match_team_id(away_info["id"], a_name, match_stats)
    hs = _format_score_value(match_row.get("home_score"))
    as_ = _format_score_value(match_row.get("away_score"))

    comp   = match_row.get("competition", {})
    season = match_row.get("season", {})
    comp_name   = comp.get("competition_name", "")   if isinstance(comp, dict) else str(comp)
    season_name = season.get("season_name", "")      if isinstance(season, dict) else str(season)

    stadium  = match_row.get("stadium", {})
    stadium_name = stadium.get("name", "N/A") if isinstance(stadium, dict) else str(stadium or "N/A")
    referee  = match_row.get("referee", {})
    referee_name = referee.get("name", "N/A") if isinstance(referee, dict) else str(referee or "N/A")
    attendance   = match_row.get("attendance", "N/A")
    mw = match_row.get("match_week", "N/A")

    # ── 比分行 ─────────────────────────────────
    col_h, col_score, col_a = st.columns([3, 2, 3], gap="medium")

    with col_h:
        himg = load_team_image(h_id, size=(80, 80), team_name=h_name) if h_id is not None else load_team_image(h_name, size=(80, 80), team_name=h_name)
        inner_col1, inner_col2 = st.columns([1, 3])
        with inner_col1:
            if himg:
                st.image(himg, width=70)
        with inner_col2:
            st.markdown(
                f"<h3 style='color:{COLORS['text']}; margin:0; padding-top:12px'>{h_name}</h3>",
                unsafe_allow_html=True)
            # 主队主帅
            hm = match_row.get("home_managers", [])
            if isinstance(hm, list) and hm:
                mgr = hm[0].get("name", "") if isinstance(hm[0], dict) else str(hm[0])
                st.markdown(f"<span style='color:{COLORS['muted']};font-size:0.8rem'>👨‍💼 {mgr}</span>",
                            unsafe_allow_html=True)

    with col_score:
        attendance_text = ""
        if attendance is not None and str(attendance) not in ("N/A", "nan"):
            try:
                attendance_text = f" · 👥 Att: {int(float(attendance)):,}"
            except (TypeError, ValueError):
                attendance_text = ""

        st.markdown(f"## {hs} - {as_}")
        st.caption(f"🏆 {comp_name} · {season_name}")
        st.caption(f"📅 Matchweek {mw} · 🏟️ {stadium_name}")
        st.caption(f"👤 Referee: {referee_name}{attendance_text}")

    with col_a:
        aimg = load_team_image(a_id, size=(80, 80), team_name=a_name) if a_id is not None else load_team_image(a_name, size=(80, 80), team_name=a_name)
        inner_col1, inner_col2 = st.columns([3, 1])
        with inner_col1:
            st.markdown(
                f"<h3 style='color:{COLORS['text']}; margin:0; padding-top:12px; text-align:right'>{a_name}</h3>",
                unsafe_allow_html=True)
            am = match_row.get("away_managers", [])
            if isinstance(am, list) and am:
                mgr = am[0].get("name", "") if isinstance(am[0], dict) else str(am[0])
                st.markdown(f"<span style='color:{COLORS['muted']};font-size:0.8rem;float:right'>👨‍💼 {mgr}</span>",
                            unsafe_allow_html=True)
        with inner_col2:
            if aimg:
                st.image(aimg, width=70)


# ─────────────────────────────────────────────
# Tab 1 — Team Stats
# ─────────────────────────────────────────────

def _render_team_stats(match_stats: pd.DataFrame, match_row):
    if match_stats.empty:
        st.info("No team stats available for this match.")
        return

    home_info = _extract_match_side_info(match_row, "home")
    away_info = _extract_match_side_info(match_row, "away")
    h_name = home_info["name"] or "Home"
    a_name = away_info["name"] or "Away"
    h_id = _resolve_match_team_id(home_info["id"], h_name, match_stats)
    a_id = _resolve_match_team_id(away_info["id"], a_name, match_stats)

    # 提取两队数据行
    home_row = _get_team_row(match_stats, h_id, h_name)
    away_row = _get_team_row(match_stats, a_id, a_name)

    if home_row is None and away_row is None:
        st.info("No team data found in match stats.")
        return

    # 分组 tab
    stat_tabs = st.tabs(["⚔️ Attacking", "🛡️ Defending", "🎯 Possession"])
    groups = ["Attacking", "Defending", "Possession"]

    for stab, grp in zip(stat_tabs, groups):
        with stab:
            _render_comparison_bars(
                MATCH_STAT_GROUPS[grp],
                home_row, away_row,
                h_name, a_name,
                match_stats,
            )


def _get_team_row(df: pd.DataFrame, team_id=None, team_name: str | None = None):
    if df.empty:
        return None
    if "team_id" in df.columns:
        numeric_ids = pd.to_numeric(df["team_id"], errors="coerce")
        if team_id is not None:
            rows = df[numeric_ids == int(team_id)]
            if not rows.empty:
                return rows.iloc[0]
    if team_name and "team_name" in df.columns:
        normalized_target = _normalize_team_name(team_name)
        rows = df[df["team_name"].astype(str).map(_normalize_team_name) == normalized_target]
        if rows.empty:
            rows = df[
                df["team_name"].astype(str).map(_normalize_team_name).str.contains(normalized_target, na=False)
            ]
        if not rows.empty:
            return rows.iloc[0]
    return None


def _render_comparison_bars(
    metrics: list,
    home_row, away_row,
    home_name: str, away_name: str,
    df: pd.DataFrame,
):
    """
    渲染类似电视转播风格的两队数据对比条
    每行：指标名 | 主队值 [进度条] | 客队值
    """
    valid = [(col, lbl) for col, lbl in metrics
             if col in (df.columns if not df.empty else [])]

    if not valid:
        st.info("No data for this group.")
        return

    for col, lbl in valid:
        hv = float(home_row.get(col, 0) or 0) if home_row is not None else 0.0
        av = float(away_row.get(col, 0) or 0) if away_row is not None else 0.0
        total = hv + av
        if total == 0:
            h_pct = a_pct = 50
        else:
            h_pct = hv / total * 100
            a_pct = av / total * 100

        is_pct = any(kw in col for kw in ["ratio", "possession", "proportion"])
        h_str  = f"{hv*100:.1f}%" if is_pct else f"{hv:.2f}"
        a_str  = f"{av*100:.1f}%" if is_pct else f"{av:.2f}"

        # 自定义进度条 HTML
        bar_html = f"""
        <div style="margin-bottom:8px">
            <div style="display:flex; justify-content:space-between;
                        font-size:0.78rem; color:{COLORS['muted']}; margin-bottom:2px">
                <span style="color:{COLORS['text']}; font-weight:600">{h_str}</span>
                <span style="font-size:0.72rem">{lbl}</span>
                <span style="color:{COLORS['text']}; font-weight:600">{a_str}</span>
            </div>
            <div style="display:flex; height:7px; border-radius:4px; overflow:hidden; background:{COLORS['grid']}">
                <div style="width:{h_pct:.1f}%; background:{COLORS['primary']}; transition:width 0.3s"></div>
                <div style="width:{a_pct:.1f}%; background:{COLORS['secondary']}"></div>
            </div>
        </div>
        """
        st.markdown(bar_html, unsafe_allow_html=True)

    # 图例
    st.markdown(
        f"""<div style="display:flex; gap:16px; font-size:0.75rem; margin-top:6px">
            <span style="color:{COLORS['primary']}">■ {home_name}</span>
            <span style="color:{COLORS['secondary']}">■ {away_name}</span>
        </div>""",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# Tab 2 — Lineups（阵型图）
# ─────────────────────────────────────────────

def _render_lineups(lineups_dict: dict, match_row, match_stats: pd.DataFrame, events_df: pd.DataFrame):
    if not lineups_dict:
        st.info("No lineup data available for this match.")
        return

    home_info = _extract_match_side_info(match_row, "home")
    away_info = _extract_match_side_info(match_row, "away")
    h_name = home_info["name"] or "Home"
    a_name = away_info["name"] or "Away"

    # 解析阵容数据
    home_lineup_raw = _get_lineup_for_team(lineups_dict, h_name)
    away_lineup_raw = _get_lineup_for_team(lineups_dict, a_name)

    home_starters, home_subs = _split_starters_subs(home_lineup_raw)
    away_starters, away_subs = _split_starters_subs(away_lineup_raw)
    home_sub_annotations = _build_substitution_annotations(events_df, h_name)
    away_sub_annotations = _build_substitution_annotations(events_df, a_name)

    # ── 阵型图 ─────────────────────────────────
    try:
        fig = plot_lineup_pitch(
            home_starters,
            away_starters,
            h_name,
            a_name,
            home_sub_annotations=home_sub_annotations,
            away_sub_annotations=away_sub_annotations,
            figsize=(13, 8),
        )
        st.pyplot(fig_to_streamlit(fig))
        import matplotlib.pyplot as plt
        plt.close(fig)
    except Exception as e:
        st.error(f"Could not render lineup pitch: {e}")

    # ── 替补列表 ──────────────────────────────
    st.markdown("#### Substitutes")
    col_h, col_a = st.columns(2)

    with col_h:
        st.markdown(f"**{h_name}**")
        _render_substitution_summary(home_sub_annotations, COLORS["primary"])
        _render_sub_list(home_subs, COLORS["primary"])

    with col_a:
        st.markdown(f"**{a_name}**")
        _render_substitution_summary(away_sub_annotations, COLORS["secondary"])
        _render_sub_list(away_subs, COLORS["secondary"])


def _split_starters_subs(lineup_df) -> tuple:
    """将 lineup DataFrame 分成首发（is_starter=True）和替补"""
    if lineup_df is None or (isinstance(lineup_df, pd.DataFrame) and lineup_df.empty):
        return pd.DataFrame(), pd.DataFrame()
    if isinstance(lineup_df, pd.DataFrame):
        df = lineup_df.copy()
    else:
        return pd.DataFrame(), pd.DataFrame()

    # StatsBomb lineups 结构中，positions 列包含位置信息
    # 首发球员 from_period == 1 且 from_time == '00:00'（或直接有 is_starter 字段）
    if "positions" in df.columns:
        def _is_starter(pos_list):
            if not isinstance(pos_list, list) or len(pos_list) == 0:
                return False
            first = pos_list[0]
            if isinstance(first, dict):
                from_val = str(first.get("from", "") or "").strip()
                from_period = first.get("from_period", 1)
                start_reason = str(first.get("start_reason", "") or "").strip().lower()
                # StatsBomb 不同返回结构下，首发信息可能来自 from/from_period 或 start_reason
                return (
                    (from_val in ("00:00", "0:00", "0") and from_period == 1)
                    or start_reason in ("starting xi", "starting xi tactical", "starter", "starting")
                )
            return False

        def _get_pos_name(pos_list):
            if isinstance(pos_list, list) and len(pos_list) > 0:
                first = pos_list[0]
                if isinstance(first, dict):
                    pos = first.get("position", "")
                    if isinstance(pos, dict):
                        return pos.get("name", "")
                    return pos
            return ""

        df["_is_starter"]     = df["positions"].apply(_is_starter)
        df["position_name"]   = df["positions"].apply(_get_pos_name)
        starters = df[df["_is_starter"]].copy()
        subs     = df[~df["_is_starter"]].copy()

        # 若 positions 存在但未能识别出首发，则退回前 11 人
        if starters.empty and len(df) >= 11:
            starters = df.head(11).copy()
            subs = df.iloc[11:].copy()
    else:
        # 没有 positions 列时按行数估算（前11行为首发）
        starters = df.head(11)
        subs     = df.iloc[11:]

    return starters, subs


def _render_sub_list(subs_df: pd.DataFrame, color: str):
    """渲染替补球员列表"""
    if subs_df.empty:
        st.markdown("<span style='color:#8b9bb4; font-size:0.85rem'>No substitutes data</span>",
                    unsafe_allow_html=True)
        return

    name_col = "player_name" if "player_name" in subs_df.columns else subs_df.columns[0]
    num_col  = "jersey_number" if "jersey_number" in subs_df.columns else None
    pos_col  = "position_name" if "position_name" in subs_df.columns else None

    for _, row in subs_df.iterrows():
        name = str(row.get(name_col, ""))
        num  = f"#{int(row[num_col])}" if num_col and not pd.isna(row.get(num_col, np.nan)) else ""
        pos  = str(row.get(pos_col, "")) if pos_col else ""
        st.markdown(
            f"<div style='padding:3px 0; font-size:0.82rem'>"
            f"<span style='color:{color}; font-weight:600'>{num}</span>"
            f"&nbsp; {name}"
            f"<span style='color:#8b9bb4; font-size:0.75rem'>&nbsp; {pos}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )


def _render_substitution_summary(sub_annotations: dict, color: str):
    if not sub_annotations:
        return
    st.markdown(
        f"<div style='margin:0 0 8px 0; color:{color}; font-size:0.82rem; font-weight:600'>Substitutions</div>",
        unsafe_allow_html=True,
    )
    for note in sub_annotations.values():
        outgoing = note.get("outgoing", "")
        replacement = note.get("replacement", "")
        reason = note.get("reason", "")
        minute = note.get("minute", "")
        minute_part = f"{minute}' " if minute else ""
        reason_part = f" ({reason})" if reason else ""
        st.markdown(
            f"<div style='font-size:0.78rem; color:{COLORS['muted']}; margin-bottom:2px'>"
            f"{minute_part}{outgoing} → {replacement}{reason_part}</div>",
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────
# Tab 3 — Set Pieces
# ─────────────────────────────────────────────

def _render_set_pieces(match_stats: pd.DataFrame):
    if match_stats.empty:
        st.info("No set piece data available.")
        return

    if "team_name" not in match_stats.columns:
        st.info("Cannot identify teams in match stats.")
        return

    teams = match_stats["team_name"].tolist()
    sp_metrics = MATCH_STAT_GROUPS["Set Pieces"]
    valid = [(col, lbl) for col, lbl in sp_metrics if col in match_stats.columns]

    if not valid:
        st.info("No set piece metrics available.")
        return

    fig = go.Figure()
    x_labels = [lbl for _, lbl in valid]

    colors_list = [COLORS["primary"], COLORS["secondary"]]
    for i, (_, row) in enumerate(match_stats.iterrows()):
        vals = [float(row.get(col, 0) or 0) for col, _ in valid]
        fig.add_trace(go.Bar(
            name=row.get("team_name", f"Team {i+1}"),
            x=x_labels,
            y=vals,
            marker_color=colors_list[i % 2],
            opacity=0.82,
            hovertemplate="<b>%{x}</b><br>%{y:.3f}<extra></extra>",
        ))

    layout = {**PLOTLY_BASE_LAYOUT}
    layout.update(dict(
        title=dict(text="Set Piece Statistics", font=dict(size=13), x=0),
        barmode="group",
        xaxis=dict(gridcolor=COLORS["grid"], linecolor=COLORS["grid"],
                   tickfont=dict(size=10)),
        yaxis=dict(gridcolor=COLORS["grid"], linecolor=COLORS["grid"],
                   tickfont=dict(size=10), zeroline=False),
        legend=dict(**PLOTLY_BASE_LAYOUT.get("legend", {}), orientation="h", y=1.08, x=0.5, xanchor="center"),
        height=380,
        margin=dict(l=20, r=20, t=60, b=40),
    ))
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────
# Tab 4 — OBV
# ─────────────────────────────────────────────

def _render_obv_tab(match_stats: pd.DataFrame):
    if match_stats.empty:
        st.info("No OBV data available.")
        return

    obv_metrics = MATCH_STAT_GROUPS["OBV"]
    valid = [(col, lbl) for col, lbl in obv_metrics if col in match_stats.columns]
    if not valid:
        st.info("No OBV metrics available.")
        return

    x_labels = [lbl for _, lbl in valid]
    colors_list = [COLORS["primary"], COLORS["secondary"]]

    fig = go.Figure()
    for i, (_, row) in enumerate(match_stats.iterrows()):
        vals = [float(row.get(col, 0) or 0) for col, _ in valid]
        fig.add_trace(go.Bar(
            name=row.get("team_name", f"Team {i+1}"),
            x=x_labels,
            y=vals,
            marker_color=colors_list[i % 2],
            opacity=0.85,
            text=[f"{v:+.4f}" for v in vals],
            textposition="outside",
            textfont=dict(size=9),
        ))

    layout = {**PLOTLY_BASE_LAYOUT}
    layout.update(dict(
        title=dict(text="On-Ball Value (OBV) Breakdown", font=dict(size=13), x=0),
        barmode="group",
        xaxis=dict(gridcolor=COLORS["grid"], linecolor=COLORS["grid"],
                   tickfont=dict(size=10)),
        yaxis=dict(gridcolor=COLORS["grid"], linecolor=COLORS["grid"],
                   zeroline=True, zerolinecolor=COLORS["muted"], zerolinewidth=1,
                   tickfont=dict(size=10)),
        legend=dict(**PLOTLY_BASE_LAYOUT.get("legend", {}), orientation="h", y=1.08, x=0.5, xanchor="center"),
        height=380,
        margin=dict(l=20, r=20, t=60, b=40),
    ))
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True)


def _extract_match_side_info(match_row, side: str) -> dict:
    """
    从 sb.matches 返回行中提取主/客队名称和 id，兼容 flat 和 dict 两种结构。
    side: 'home' | 'away'
    """
    team_col = f"{side}_team"
    team_name_col = f"{side}_team_name"
    team_id_col = f"{side}_team_id"

    if team_name_col in match_row.index or team_id_col in match_row.index:
        name = match_row.get(team_name_col, "")
        team_id = match_row.get(team_id_col)
    else:
        team_val = match_row.get(team_col, {})
        if isinstance(team_val, dict):
            name = team_val.get(team_name_col, "")
            team_id = team_val.get(team_id_col)
        else:
            name = str(team_val) if isinstance(team_val, str) else ""
            team_id = None

    try:
        team_id = int(team_id) if pd.notna(team_id) else None
    except (TypeError, ValueError):
        team_id = None

    return {"name": str(name or ""), "id": team_id}


def _format_score_value(value) -> int | str:
    try:
        if value is None or pd.isna(value):
            return "?"
        return int(float(value))
    except (TypeError, ValueError):
        return "?"


def _normalize_team_name(value: str) -> str:
    return "".join(ch for ch in str(value).strip().lower() if ch.isalnum())


def _resolve_match_team_id(team_id, team_name: str, match_stats: pd.DataFrame):
    """
    优先使用 matches 自带 id；若缺失或不在 team_match_stats 中，则按 team_name 反查 team_id。
    """
    if team_id is not None and "team_id" in match_stats.columns:
        numeric_ids = pd.to_numeric(match_stats["team_id"], errors="coerce").dropna().astype(int)
        if int(team_id) in set(numeric_ids.tolist()):
            return int(team_id)

    if not team_name or "team_id" not in match_stats.columns or "team_name" not in match_stats.columns:
        return team_id

    normalized_target = _normalize_team_name(team_name)
    matched = match_stats[
        match_stats["team_name"].astype(str).map(_normalize_team_name) == normalized_target
    ]
    if matched.empty:
        matched = match_stats[
            match_stats["team_name"].astype(str).map(_normalize_team_name).str.contains(normalized_target, na=False)
        ]
    if matched.empty:
        return team_id

    resolved_ids = pd.to_numeric(matched["team_id"], errors="coerce").dropna().astype(int)
    if resolved_ids.empty:
        return team_id
    return int(resolved_ids.iloc[0])


def _get_lineup_for_team(lineups_dict: dict, team_name: str):
    """从 sb.lineups 返回的 dict 中按队名宽松匹配阵容 DataFrame。"""
    if not isinstance(lineups_dict, dict) or not lineups_dict:
        return pd.DataFrame()

    if team_name in lineups_dict:
        return lineups_dict[team_name]

    normalized_target = _normalize_team_name(team_name)
    for key, value in lineups_dict.items():
        if _normalize_team_name(key) == normalized_target:
            return value
    for key, value in lineups_dict.items():
        normalized_key = _normalize_team_name(key)
        if normalized_target in normalized_key or normalized_key in normalized_target:
            return value
    return pd.DataFrame()


def _build_substitution_annotations(events_df: pd.DataFrame, team_name: str) -> dict:
    """
    从 sb.events(match_id=...) 中提取换人信息。
    key 为被换下球员名的规范化形式，value 包含 replacement / reason / minute。
    """
    if events_df.empty or not team_name:
        return {}

    candidate_type_cols = ["type", "type_name"]
    team_cols = ["team", "team_name"]
    player_cols = ["player", "player_name"]
    replacement_cols = ["substitution_replacement", "substitution_replacement_name"]
    outcome_cols = ["substitution_outcome", "substitution_outcome_name"]

    sub_df = events_df.copy()
    if "type" in sub_df.columns and not pd.api.types.is_string_dtype(sub_df["type"]):
        sub_df["type"] = sub_df["type"].astype(str)

    type_mask = pd.Series(False, index=sub_df.index)
    for col in candidate_type_cols:
        if col in sub_df.columns:
            type_mask = type_mask | sub_df[col].astype(str).str.contains("Substitution", case=False, na=False)
    sub_df = sub_df[type_mask]
    if sub_df.empty:
        return {}

    normalized_team = _normalize_team_name(team_name)
    team_mask = pd.Series(False, index=sub_df.index)
    for col in team_cols:
        if col in sub_df.columns:
            team_mask = team_mask | sub_df[col].astype(str).map(_normalize_team_name).eq(normalized_team)
    sub_df = sub_df[team_mask]
    if sub_df.empty:
        return {}

    notes = {}
    for _, row in sub_df.iterrows():
        outgoing = _first_non_empty_value(row, player_cols)
        replacement = _first_non_empty_value(row, replacement_cols)
        reason = _first_non_empty_value(row, outcome_cols)
        minute = row.get("minute", "")
        key = _normalize_team_name(outgoing)
        if not key:
            continue
        notes[key] = {
            "outgoing": outgoing,
            "replacement": replacement,
            "reason": reason,
            "minute": int(minute) if pd.notna(minute) and str(minute) != "" else "",
        }
    return notes


def _first_non_empty_value(row, columns: list[str]) -> str:
    for col in columns:
        if col not in row.index:
            continue
        value = row.get(col)
        if value is None:
            continue
        if isinstance(value, float) and pd.isna(value):
            continue
        text = str(value).strip()
        if text and text.lower() != "nan":
            return text
    return ""


# ─────────────────────────────────────────────
# 欢迎页
# ─────────────────────────────────────────────

def _render_welcome():
    st.markdown("""
    <div style="text-align:center; padding: 60px 20px; color: #8b9bb4">
        <h2 style="font-size:2rem">⚽ Match Dashboard</h2>
        <p style="font-size:1rem">
            Select a competition, season, and match from the sidebar to begin.
        </p>
    </div>
    """, unsafe_allow_html=True)
