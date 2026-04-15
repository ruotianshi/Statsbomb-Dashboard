"""
player_match.py
---------------
Player Match Stats Dashboard 视图
包含：
  1. 比赛 + 球员选择（sidebar）
  2. 球员单场基础 Metrics 卡片（含 vs 赛季均值 delta）
  3. Tab 切换五种 Pitch 可视化：
     - ⚽ Shots
     - 🎯 Passes
     - 🏃 Dribbles
     - 🛡️ Defensive Actions
     - 🔥 Heatmap
  4. Pitch 图右侧对应数据摘要卡片
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from utils.data_loader import (
    load_competitions,
    load_events,
    load_matches,
    load_player_match_stats,
    load_player_season_stats,
)
from utils.image_helper import get_player_display_name, load_player_image, load_team_image
from utils.metrics_config import COLORS, PLOTLY_BASE_LAYOUT


# ─────────────────────────────────────────────
# 单场球员指标卡片定义
# ─────────────────────────────────────────────

MATCH_PLAYER_CARD_SPECS = [
    ("Minutes", "player_match_minutes", False),
    ("Goals", "player_match_goals", False),
    ("Assists", "player_match_assists", False),
    ("Passes", "player_match_passes", False),
    ("Pass %", "__pass_rate__", True),
    ("Key Passes", "player_match_key_passes", False),
    ("Dribbles", "player_match_dribbles", False),
    ("Tackles", "player_match_tackles", False),
    ("Interceptions", "player_match_interceptions", False),
    ("Turnovers", "player_match_turnovers", False),
    ("Pressures", "player_match_pressures", False),
]

# StatsBomb event type → pitch viz 列映射关系
# （player_match_stats 中通常不直接含坐标，需要从 events 数据提取）
# 这里提供一个通用的坐标列名候选列表，实际列名可能因 API 版本而异
_COORD_COLS = {
    "shots": {
        "x": ["player_match_shot_x", "x", "location_x"],
        "y": ["player_match_shot_y", "y", "location_y"],
        "outcome": ["player_match_shot_outcome", "outcome", "shot_outcome"],
        "xg": ["player_match_shot_xg", "xg", "shot_statsbomb_xg"],
    },
    "passes": {
        "x":       ["x", "location_x", "pass_x"],
        "y":       ["y", "location_y", "pass_y"],
        "end_x":   ["end_x", "pass_end_x", "end_location_x"],
        "end_y":   ["end_y", "pass_end_y", "end_location_y"],
        "outcome": ["outcome", "pass_outcome", "pass_outcome_name"],
    },
    "dribbles": {
        "x":       ["x", "location_x"],
        "y":       ["y", "location_y"],
        "outcome": ["outcome", "dribble_outcome", "dribble_outcome_name"],
    },
    "defensive": {
        "x":           ["x", "location_x"],
        "y":           ["y", "location_y"],
        "action_type": ["action_type", "type", "type_name"],
    },
    "heatmap": {
        "x": ["x", "location_x"],
        "y": ["y", "location_y"],
    },
}


# ─────────────────────────────────────────────
# 主入口
# ─────────────────────────────────────────────

def render():
    _render_sidebar_filters()

    comp_id   = st.session_state.get("pms_competition_id")
    season_id = st.session_state.get("pms_season_id")
    match_id  = st.session_state.get("pms_match_id")
    player_id = st.session_state.get("pms_player_id")
    player_name = st.session_state.get("pms_player_name")

    if not comp_id or not season_id or match_id is None:
        _render_welcome()
        return

    if player_id is None and not player_name:
        st.info("Select a player from the sidebar.")
        return

    # 加载单场球员统计
    with st.spinner("Loading player match data..."):
        raw_events_df   = load_events(match_id)
        match_player_df = load_player_match_stats(match_id)
        season_df       = load_player_season_stats(comp_id, season_id)
    events_df = _prepare_events_df(raw_events_df)

    if match_player_df.empty and events_df.empty:
        st.warning("No player match stats or event data available for this match.")
        return

    player_events = _filter_player_events(events_df, player_name=player_name, player_id=player_id)
    selected_player_name = _resolve_selected_player_name(player_events, player_name)
    player_row = _get_player_match_row(match_player_df, selected_player_name, player_id)

    if player_row is None and player_name:
        player_row = _get_player_match_row(match_player_df, player_name, player_id)

    if player_events.empty and player_row is None:
        st.warning("Player not found in this match data.")
        return

    # 赛季均值（用于 delta）
    season_row = _get_player_season_row(season_df, player_row, selected_player_name, player_id)

    # ── 主内容 ────────────────────────────────
    _render_player_banner(player_row, selected_player_name)

    st.markdown('<hr style="border:1px solid #2a2d3e; margin:12px 0">', unsafe_allow_html=True)

    if player_row is not None:
        _render_metric_cards(player_row, season_row)
    else:
        _render_event_summary_cards(player_events)

    st.markdown('<hr style="border:1px solid #2a2d3e; margin:12px 0">', unsafe_allow_html=True)

    _render_pitch_tabs(player_events, player_row, selected_player_name, raw_events_df)


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
        default_comp = st.session_state.get("pms_competition_name", comp_names[0])
        if default_comp not in comp_names:
            default_comp = comp_names[0]

        comp_name = st.selectbox("Competition", comp_names,
                                 index=comp_names.index(default_comp),
                                 key="pms_comp_select")
        comp_id = int(comps_df[comps_df["competition_name"] == comp_name]["competition_id"].iloc[0])

        season_opts = (comps_df[comps_df["competition_name"] == comp_name]
                       [["season_id", "season_name"]].drop_duplicates()
                       .sort_values("season_name", ascending=False))
        season_names   = season_opts["season_name"].tolist()
        default_season = st.session_state.get("pms_season_name", season_names[0])
        if default_season not in season_names:
            default_season = season_names[0]

        season_name = st.selectbox("Season", season_names,
                                   index=season_names.index(default_season),
                                   key="pms_season_select")
        season_id = int(season_opts[season_opts["season_name"] == season_name]["season_id"].iloc[0])

        st.divider()
        st.markdown("### ⚽ Match & Player")

        matches_df = load_matches(comp_id, season_id)
        all_teams = _get_all_teams(matches_df)
        selected_teams = st.multiselect(
            "Filter by Team",
            options=sorted(all_teams),
            default=st.session_state.get("pms_team_filter", []),
            key="pms_team_filter_select",
        )

        if selected_teams:
            filtered_matches = matches_df[
                matches_df.apply(_match_involves_teams, team_filter=selected_teams, axis=1)
            ]
        else:
            filtered_matches = matches_df

        match_opts = _build_match_opts(filtered_matches)

        if match_opts:
            match_labels = list(match_opts.keys())
            prev_mid = st.session_state.get("pms_match_id")
            default_mi = 0
            for i, mid in enumerate(match_opts.values()):
                if mid == prev_mid:
                    default_mi = i
                    break

            sel_match = st.selectbox("Match", match_labels,
                                     index=default_mi, key="pms_match_select")
            selected_match_id = match_opts[sel_match]
        else:
            selected_match_id = None

        # 球员选择（优先从 events 提取，保证和 pitch maps 一致）
        selected_player_id = None
        selected_player_name = None
        if selected_match_id is not None:
            events_df = load_events(selected_match_id)
            pms_df = load_player_match_stats(selected_match_id)
            player_options = _build_player_options(events_df, pms_df)

            if player_options:
                player_names = list(player_options.keys())
                prev_name = st.session_state.get("pms_player_name")
                default_idx = player_names.index(prev_name) if prev_name in player_names else 0
                sel_player = st.selectbox(
                    "Player",
                    player_names,
                    index=default_idx,
                    key="pms_player_select",
                )
                selected_player_name = sel_player
                selected_player_id = player_options[sel_player]

        st.session_state.update({
            "pms_competition_id":   comp_id,
            "pms_season_id":        season_id,
            "pms_competition_name": comp_name,
            "pms_season_name":      season_name,
            "pms_match_id":         selected_match_id,
            "pms_player_id":        selected_player_id,
            "pms_player_name":      selected_player_name,
            "pms_team_filter":      selected_teams,
        })


def _build_match_opts(matches_df: pd.DataFrame) -> dict:
    opts = {}
    if matches_df.empty:
        return opts
    for _, row in matches_df.sort_values("match_date").iterrows():
        home_info = _extract_match_side_info(row, "home")
        away_info = _extract_match_side_info(row, "away")
        hn = home_info["name"] or "Home"
        an = away_info["name"] or "Away"
        hs = _format_score_value(row.get("home_score"))
        as_ = _format_score_value(row.get("away_score"))
        dt = str(row.get("match_date", ""))[:10]
        opts[f"{dt} | {hn} {hs} v {as_} {an}"] = row["match_id"]
    return opts


# ─────────────────────────────────────────────
# 球员简介横幅
# ─────────────────────────────────────────────

def _render_player_banner(player_row, player_name: str):
    col_img, col_info, col_team = st.columns([1, 5, 1], gap="medium")

    with col_img:
        if player_row is not None and player_row.get("player_id") is not None:
            img = load_player_image(player_row.get("player_id"), size=(90, 90))
            st.image(img, width=85)

    with col_info:
        display_name = get_player_display_name(player_row) if player_row is not None else player_name
        team_name    = player_row.get("team_name", "") if player_row is not None else ""
        pos          = player_row.get("primary_position", "") if player_row is not None else ""
        minutes      = int(player_row.get("player_match_minutes", 0) or 0) if player_row is not None else 0

        st.markdown(f"""
        <div style="padding: 4px 0">
            <h2 style="margin:0; font-size:1.4rem; color:{COLORS['text']}">{display_name}</h2>
            <p style="margin:3px 0; color:{COLORS['muted']}; font-size:0.85rem">
                🏟️ {team_name} &nbsp;·&nbsp; 📍 {pos} &nbsp;·&nbsp; ⏱️ {minutes} min
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col_team:
        team_id = player_row.get("team_id") if player_row is not None else None
        team_name = player_row.get("team_name", "") if player_row is not None else ""
        if team_id:
            timg = load_team_image(team_id, size=(70, 70))
            st.image(timg, width=65)
        elif team_name:
            timg = load_team_image(team_name, size=(70, 70), team_name=team_name)
            st.image(timg, width=65)


# ─────────────────────────────────────────────
# 基础 Metrics 卡片行
# ─────────────────────────────────────────────

def _render_metric_cards(player_row, season_row):
    """渲染基于 sb.player_match_stats 的关键指标卡片。"""
    chunks = [MATCH_PLAYER_CARD_SPECS[:6], MATCH_PLAYER_CARD_SPECS[6:]]

    for chunk in chunks:
        cols = st.columns(len(chunk))
        for col_ui, (label, key, is_pct) in zip(cols, chunk):
            match_value = _metric_spec_value(player_row, key, scope="match")
            season_value = _metric_spec_value(season_row, key, scope="season")
            delta = None
            if _is_numeric_value(match_value) and _is_numeric_value(season_value):
                delta = match_value - season_value

            col_ui.metric(
                label,
                _format_metric_value(match_value, pct=is_pct),
                delta=_format_metric_delta(delta, pct=is_pct) if delta is not None else None,
                help=(
                    f"Season avg: {_format_metric_value(season_value, pct=is_pct)}"
                    if _is_numeric_value(season_value) else None
                ),
            )


# ─────────────────────────────────────────────
# Pitch 可视化 Tab
# ─────────────────────────────────────────────

def _render_pitch_tabs(player_events: pd.DataFrame, player_row, player_name: str, raw_events_df: pd.DataFrame):
    st.markdown("#### 🗺️ Pitch Maps")
    _render_event_data_status(player_events, raw_events_df, player_name)

    tabs = st.tabs(["🎯 Shots", "⚽ Passes", "🏃 Carries", "🛡️ Defensive Actions", "🔥 Heatmap"])

    with tabs[0]:
        _render_pitch_tab_shots(player_events, player_row, player_name)

    with tabs[1]:
        _render_pitch_tab_passes(player_events, player_row, player_name)

    with tabs[2]:
        _render_pitch_tab_carries(player_events, player_row, player_name)

    with tabs[3]:
        _render_pitch_tab_defensive(player_events, player_row, player_name)

    with tabs[4]:
        _render_pitch_tab_heatmap(player_events, player_row, player_name)


def _render_pitch_tab_shots(player_events: pd.DataFrame, player_row, player_name: str):
    col_pitch, col_stats = st.columns([7, 3], gap="medium")
    shot_events = _events_of_type(player_events, "Shot")
    attempts = len(shot_events)
    goals = _count_goal_shots(shot_events)
    total_xg = _sum_event_values(shot_events, ["shot_statsbomb_xg"])

    with col_stats:
        st.markdown("**Shot Summary**")
        _metric_value_line("Shot Attempts", attempts)
        _metric_value_line("Goals", goals)
        _metric_value_line("Total xG", total_xg, precision=2)
        st.caption(f"{attempts} shot events")

    with col_pitch:
        fig = _build_shots_pitch_figure(shot_events, player_name)
        st.plotly_chart(fig, use_container_width=True)
        if shot_events.empty:
            st.caption("No shot events found for this player in the loaded event data.")


def _render_pitch_tab_passes(player_events: pd.DataFrame, player_row, player_name: str):
    col_pitch, col_stats = st.columns([7, 3], gap="medium")
    pass_events = _events_of_type(player_events, "Pass")
    pass_rate = _metric_spec_value(player_row, "__pass_rate__", scope="match")

    with col_stats:
        st.markdown("**Pass Summary**")
        _metric_mini("Passes", player_row, "player_match_passes")
        _metric_value_line("Pass Rate", pass_rate, pct=True)
        _metric_mini("Forward", player_row, "player_match_forward_passes")
        _metric_mini("Backward", player_row, "player_match_backward_passes")
        _metric_mini("Sideways", player_row, "player_match_sideways_passes")
        _metric_mini("Key Passes", player_row, "player_match_key_passes")
        show_incomplete = st.toggle("Show Incomplete Passes", value=True, key="pms_pass_incomplete")
        st.caption(f"{len(pass_events)} pass events")

    with col_pitch:
        fig = _build_passes_pitch_figure(pass_events, player_name, show_incomplete=show_incomplete)
        st.plotly_chart(fig, use_container_width=True)
        if pass_events.empty:
            st.caption("No pass events found for this player in the loaded event data.")


def _render_pitch_tab_carries(player_events: pd.DataFrame, player_row, player_name: str):
    col_pitch, col_stats = st.columns([7, 3], gap="medium")
    carry_events = _events_of_type(player_events, "Carry")
    carry_attempts = len(carry_events)
    carry_success = int(_carry_success_mask(carry_events).sum()) if carry_attempts else 0
    carry_fail = max(carry_attempts - carry_success, 0)
    carry_rate = (carry_success / carry_attempts) if carry_attempts else np.nan

    with col_stats:
        st.markdown("**Carry Summary**")
        _metric_value_line("Attempts", carry_attempts)
        _metric_value_line("Successful", carry_success)
        _metric_value_line("Failed", carry_fail)
        _metric_value_line("Success Rate", carry_rate, pct=True)
        st.caption(f"{carry_attempts} carry events")

    with col_pitch:
        fig = _build_carries_pitch_figure(carry_events, player_name)
        st.plotly_chart(fig, use_container_width=True)
        if carry_events.empty:
            st.caption("No carry events found for this player in the loaded event data.")


def _render_pitch_tab_defensive(player_events: pd.DataFrame, player_row, player_name: str):
    col_pitch, col_stats = st.columns([7, 3], gap="medium")
    defensive_types = st.multiselect(
        "Select Defensive Action Types",
        options=["Ball Recovery", "Clearance", "Block", "Pressure", "Duel"],
        default=["Ball Recovery", "Block", "Duel"],
        key="pms_def_types",
    )
    type_series = _event_type_series(player_events)
    defensive_events = player_events[type_series.isin(defensive_types)] if type_series is not None else pd.DataFrame()

    with col_stats:
        st.markdown("**Defensive Summary**")
        all_defensive_counts = _defensive_action_counts(player_events)
        _metric_value_line("Ball Recovery", all_defensive_counts.get("Ball Recovery", 0))
        _metric_value_line("Block", all_defensive_counts.get("Block", 0))
        _metric_value_line("Pressure", all_defensive_counts.get("Pressure", 0))
        _metric_value_line("Duel", all_defensive_counts.get("Duel", 0))
        st.caption(f"{len(defensive_events)} defensive events")

    with col_pitch:
        fig = _build_defensive_pitch_figure(defensive_events, player_name)
        st.plotly_chart(fig, use_container_width=True)
        if defensive_events.empty:
            st.caption("No selected defensive action events found for this player in the loaded event data.")


def _render_pitch_tab_heatmap(player_events: pd.DataFrame, player_row, player_name: str):
    col_pitch, col_stats = st.columns([7, 3], gap="medium")
    location_events = _events_with_location(player_events)

    with col_stats:
        st.markdown("**Activity Summary**")
        _metric_mini("Minutes", player_row, "player_match_minutes")
        _metric_mini("Touches", player_row, "player_match_touches", alt_keys=["player_match_touch"])
        _metric_mini("Dribbles", player_row, "player_match_dribbles")
        _metric_mini("Pressures", player_row, "player_match_pressures")
        st.caption(f"{len(location_events)} events with location")

    with col_pitch:
        fig = _build_heatmap_pitch_figure(location_events, player_name)
        st.plotly_chart(fig, use_container_width=True)
        if location_events.empty:
            st.caption("No location-bearing events found for this player, so the heatmap is empty.")


# ─────────────────────────────────────────────
# 辅助函数
# ─────────────────────────────────────────────

def _metric_mini(label: str, row, col: str, pct: bool = False, alt_keys: list = None):
    """渲染一个小型 metric 项目（label: value）"""
    val = _metric_spec_value(row, col, scope="match", alt_keys=alt_keys)
    _metric_value_line(label, val, pct=pct)


def _metric_value_line(label: str, value, pct: bool = False, precision: int = 1):
    st.markdown(
        f"<div style='display:flex; justify-content:space-between; "
        f"padding:3px 0; border-bottom:1px solid {COLORS['grid']}; font-size:0.82rem'>"
        f"<span style='color:{COLORS['muted']}'>{label}</span>"
        f"<span style='color:{COLORS['text']}; font-weight:600'>{_format_metric_value(value, pct=pct, precision=precision)}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_event_summary_cards(player_events: pd.DataFrame):
    shots = len(_events_of_type(player_events, "Shot"))
    passes = len(_events_of_type(player_events, "Pass"))
    carries = len(_events_of_type(player_events, "Carry"))
    defensive_counts = _defensive_action_counts(player_events)
    defensive = sum(defensive_counts.values())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Shots", shots)
    c2.metric("Passes", passes)
    c3.metric("Carries", carries)
    c4.metric("Def Actions", defensive)


def _build_player_options(events_df: pd.DataFrame, pms_df: pd.DataFrame) -> dict:
    options = {}
    player_series = _event_player_series(events_df)
    if not events_df.empty and player_series is not None:
        event_players = sorted([p for p in player_series.dropna().astype(str).unique().tolist() if p.strip()])
        for name in event_players:
            options[name] = _lookup_player_id_from_match_stats(pms_df, name)
    elif not pms_df.empty:
        temp = pms_df.copy()
        temp["_display"] = temp.apply(get_player_display_name, axis=1)
        options = dict(zip(temp["_display"], temp["player_id"]))
    return options


def _lookup_player_id_from_match_stats(pms_df: pd.DataFrame, player_name: str):
    if pms_df.empty or "player_id" not in pms_df.columns:
        return None
    temp = pms_df.copy()
    temp["_display"] = temp.apply(get_player_display_name, axis=1).map(_normalize_text_key)
    matched = temp[temp["_display"] == _normalize_text_key(player_name)]
    if not matched.empty:
        return matched["player_id"].iloc[0]
    return None


def _filter_player_events(events_df: pd.DataFrame, player_name: str | None = None, player_id=None) -> pd.DataFrame:
    if events_df.empty:
        return pd.DataFrame()
    result = events_df.copy()
    player_series = _event_player_series(result)
    if player_name and player_series is not None:
        result = result[player_series.astype(str).map(_normalize_text_key) == _normalize_text_key(player_name)]
    elif player_id is not None and "player_id" in result.columns:
        result = result[result["player_id"] == player_id]
    return result


def _resolve_selected_player_name(player_events: pd.DataFrame, fallback_name: str | None) -> str:
    if fallback_name:
        return fallback_name
    player_series = _event_player_series(player_events)
    if not player_events.empty and player_series is not None and not player_series.dropna().empty:
        return str(player_series.dropna().iloc[0])
    return "Player"


def _get_player_match_row(match_player_df: pd.DataFrame, player_name: str, player_id=None):
    if match_player_df.empty:
        return None
    if player_id is not None and "player_id" in match_player_df.columns:
        rows = match_player_df[match_player_df["player_id"] == player_id]
        if not rows.empty:
            return rows.iloc[0]
    temp = match_player_df.copy()
    temp["_display"] = temp.apply(get_player_display_name, axis=1).map(_normalize_text_key)
    rows = temp[temp["_display"] == _normalize_text_key(player_name)]
    if not rows.empty:
        return rows.iloc[0]
    return None


def _get_player_season_row(season_df: pd.DataFrame, player_row, player_name: str, player_id=None):
    if season_df.empty:
        return None
    if player_id is not None and "player_id" in season_df.columns:
        rows = season_df[season_df["player_id"] == player_id]
        if not rows.empty:
            return rows.iloc[0]
    if player_row is not None and player_row.get("player_id") is not None:
        rows = season_df[season_df["player_id"] == player_row.get("player_id")]
        if not rows.empty:
            return rows.iloc[0]
    temp = season_df.copy()
    temp["_display"] = temp.apply(get_player_display_name, axis=1).map(_normalize_text_key)
    rows = temp[temp["_display"] == _normalize_text_key(player_name)]
    if not rows.empty:
        return rows.iloc[0]
    return None


def _get_all_teams(matches_df: pd.DataFrame) -> list:
    if matches_df.empty:
        return []
    teams = set()
    for _, row in matches_df.iterrows():
        teams.add(_extract_match_side_info(row, "home")["name"])
        teams.add(_extract_match_side_info(row, "away")["name"])
    return [t for t in teams if t]


def _match_involves_teams(row, team_filter: list[str]) -> bool:
    home_name = _extract_match_side_info(row, "home")["name"]
    away_name = _extract_match_side_info(row, "away")["name"]
    return home_name in team_filter or away_name in team_filter


def _extract_match_side_info(match_row, side: str) -> dict:
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


def _normalize_text_key(value: str) -> str:
    return "".join(ch for ch in str(value).strip().lower() if ch.isalnum())


def _events_of_type(events_df: pd.DataFrame, event_type: str) -> pd.DataFrame:
    if events_df.empty:
        return pd.DataFrame()
    type_series = _event_type_series(events_df)
    if type_series is None:
        return pd.DataFrame()
    return events_df[type_series.astype(str) == event_type].copy()


def _prepare_events_df(events_df: pd.DataFrame) -> pd.DataFrame:
    """
    标准化 sb.events 返回字段，尽量统一成当前页面使用的列名。
    兼容 dict 列、*_name 列，以及不同数据源下的轻微命名差异。
    """
    if events_df is None or events_df.empty:
        return pd.DataFrame()

    df = events_df.copy()
    _coerce_name_column(df, "type", "type_name")
    _coerce_name_column(df, "player", "player_name")
    _coerce_name_column(df, "team", "team_name")
    _coerce_name_column(df, "pass_height", "pass_height_name")
    _coerce_name_column(df, "pass_body_part", "pass_body_part_name")
    _coerce_name_column(df, "shot_body_part", "shot_body_part_name")
    _coerce_name_column(df, "shot_outcome", "shot_outcome_name")
    _coerce_name_column(df, "shot_technique", "shot_technique_name")
    _coerce_name_column(df, "clearance_body_part", "clearance_body_part_name")
    _coerce_name_column(df, "duel_type", "duel_type_name")
    _coerce_name_column(df, "duel_outcome", "duel_outcome_name", keep_null=True)
    _coerce_name_column(df, "pass_outcome", "pass_outcome_name", keep_null=True)
    return df


def _events_with_location(events_df: pd.DataFrame) -> pd.DataFrame:
    if events_df.empty:
        return pd.DataFrame()
    location_series = _event_location_series(events_df)
    if location_series is None:
        return pd.DataFrame()
    return events_df[location_series.apply(_is_valid_location)].copy()


def _is_valid_location(value) -> bool:
    return (
        isinstance(value, (list, tuple, np.ndarray))
        and len(value) >= 2
        and pd.notna(value[0])
        and pd.notna(value[1])
    )


def _extract_xy(location):
    if _is_valid_location(location):
        return float(location[0]), float(location[1])
    return None, None


def _create_pitch_figure(title: str, x_range=(0, 120), height: int = 760) -> go.Figure:
    fig = go.Figure()
    shape_base = dict(layer="below", line=dict(color=PITCH_LINE, width=2))

    fig.add_shape(type="rect", x0=0, y0=0, x1=120, y1=80, fillcolor=PITCH_BG, **shape_base)
    fig.add_shape(type="line", x0=60, y0=0, x1=60, y1=80, **shape_base)
    fig.add_shape(type="circle", x0=50, y0=30, x1=70, y1=50, **shape_base)
    fig.add_shape(type="rect", x0=0, y0=18, x1=18, y1=62, **shape_base)
    fig.add_shape(type="rect", x0=102, y0=18, x1=120, y1=62, **shape_base)
    fig.add_shape(type="rect", x0=0, y0=30, x1=6, y1=50, **shape_base)
    fig.add_shape(type="rect", x0=114, y0=30, x1=120, y1=50, **shape_base)
    fig.add_shape(type="circle", x0=58.8, y0=38.8, x1=61.2, y1=41.2, fillcolor=PITCH_LINE, **shape_base)
    fig.add_shape(type="circle", x0=10.8, y0=38.8, x1=13.2, y1=41.2, fillcolor=PITCH_LINE, **shape_base)
    fig.add_shape(type="circle", x0=106.8, y0=38.8, x1=109.2, y1=41.2, fillcolor=PITCH_LINE, **shape_base)

    layout = {**PLOTLY_BASE_LAYOUT}
    layout.update(dict(
        title=dict(text=title, x=0, font=dict(size=13, color=COLORS["text"])),
        xaxis=dict(range=list(x_range), showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(range=[80, 0], showgrid=False, zeroline=False, showticklabels=False, scaleanchor="x", scaleratio=1),
        height=height,
        plot_bgcolor=PITCH_BG,
        paper_bgcolor=PAPER_BG,
        hovermode="closest",
        legend=dict(
            x=1.02,
            xanchor="left",
            y=1,
            yanchor="top",
            orientation="v",
            bgcolor=LEGEND_BG,
            bordercolor="rgba(255,255,255,0.08)",
            borderwidth=1,
            font=dict(size=11, color=COLORS["text"]),
            tracegroupgap=6,
        ),
        margin=dict(l=16, r=178, t=54, b=18),
    ))
    fig.update_layout(**layout)
    return fig


SHOT_BODY_PART_COLORS = {
    "Right Foot": "#5da9e9",
    "Left Foot": "#ff7a59",
    "Head": "#4fd1b5",
    "Other": "#b794f4",
}

PASS_HEIGHT_COLORS = {
    "Ground Pass": "#2dd4bf",
    "Low Pass": "#7aa2ff",
    "High Pass": "#ff9966",
}

DEFENSIVE_TYPE_CONFIG = {
    "Ball Recovery": {"color": "#00d4aa", "symbol": "circle"},
    "Clearance": {"color": "#636EFA", "symbol": "square"},
    "Block": {"color": "#EF553B", "symbol": "diamond"},
    "Pressure": {"color": "#FFA15A", "symbol": "triangle-up"},
    "Duel": {"color": "#f7d716", "symbol": "x"},
}

PITCH_BG   = "#1a1d2e"              # 与主题 COLORS["bg_card"] 一致
PITCH_LINE = "#4a4e65"              # 与 pitch_viz.py LINE_COLOR 一致
PAPER_BG   = "rgba(0,0,0,0)"       # 透明，匹配其他 Plotly 图表
LEGEND_BG  = "rgba(26,29,46,0.86)"


def _create_half_pitch_figure(title: str) -> go.Figure:
    """
    横向半场 Plotly 球场（球门在上，中场线在下）。

    坐标映射（StatsBomb → Plotly）：
      SB x (60–120)  →  Plotly y（60=底/中场，120=顶/球门）
      SB y (0–80)    →  Plotly x（0=左，80=右）

    使用方法：所有 SB 坐标 (sx, sy) 在添加 trace 时写成 x=sy, y=sx。
    """
    _s = dict(layer="below", line=dict(color=PITCH_LINE, width=1.8))

    fig = go.Figure()

    # 半场底色 + 边框
    fig.add_shape(type="rect", x0=0, y0=60, x1=80, y1=120,
                  fillcolor=PITCH_BG, **_s)

    # 中场线（底部）
    fig.add_shape(type="line", x0=0, y0=60, x1=80, y1=60, **_s)

    # 禁区  SB(102≤x≤120, 18≤y≤62) → Plot(18≤px≤62, 102≤py≤120)
    fig.add_shape(type="rect", x0=18, y0=102, x1=62, y1=120, **_s)

    # 小禁区 SB(114≤x≤120, 30≤y≤50) → Plot(30≤px≤50, 114≤py≤120)
    fig.add_shape(type="rect", x0=30, y0=114, x1=50, y1=120, **_s)

    # 球门框（延伸至场外）
    fig.add_shape(type="rect", x0=36, y0=120, x1=44, y1=123.5,
                  fillcolor="#2a2d3e", **_s)

    # 罚球点  SB(108, 40) → Plot(40, 108)
    fig.add_shape(type="circle", x0=39.4, y0=107.4, x1=40.6, y1=108.6,
                  fillcolor=PITCH_LINE, line=dict(color=PITCH_LINE, width=0), layer="below")

    # 中场圆心点  SB(60, 40) → Plot(40, 60)
    fig.add_shape(type="circle", x0=39.4, y0=59.4, x1=40.6, y1=60.6,
                  fillcolor=PITCH_LINE, line=dict(color=PITCH_LINE, width=0), layer="below")

    # 中场圆弧（上半圆，在半场内）  center Plot(40, 60)  r=9.15
    thetas = np.linspace(0, np.pi, 60)
    fig.add_trace(go.Scatter(
        x=(40 + 9.15 * np.cos(thetas)).tolist(),
        y=(60 + 9.15 * np.sin(thetas)).tolist(),
        mode="lines", line=dict(color=PITCH_LINE, width=1.8),
        hoverinfo="skip", showlegend=False,
    ))

    # 罚球弧（D弧，禁区外部分）  center Plot(40, 108)  r=9.15
    # 仅画 py < 102 的部分（sin(θ) < -6/9.15）
    limit = np.arcsin(6.0 / 9.15)
    thetas_d = np.linspace(np.pi + limit, 2 * np.pi - limit, 60)
    fig.add_trace(go.Scatter(
        x=(40 + 9.15 * np.cos(thetas_d)).tolist(),
        y=(108 + 9.15 * np.sin(thetas_d)).tolist(),
        mode="lines", line=dict(color=PITCH_LINE, width=1.8),
        hoverinfo="skip", showlegend=False,
    ))

    # 角球弧（球门线两端，r=1）
    for cx, cy, a0, a1 in [
        (0,  120, 3 * np.pi / 2, 2 * np.pi),    # 左上角
        (80, 120, np.pi,          3 * np.pi / 2), # 右上角
    ]:
        thetas_c = np.linspace(a0, a1, 20)
        fig.add_trace(go.Scatter(
            x=(cx + np.cos(thetas_c)).tolist(),
            y=(cy + np.sin(thetas_c)).tolist(),
            mode="lines", line=dict(color=PITCH_LINE, width=1.5),
            hoverinfo="skip", showlegend=False,
        ))

    layout = {**PLOTLY_BASE_LAYOUT}
    layout.update(dict(
        title=dict(text=title, x=0, font=dict(size=13, color=COLORS["text"])),
        xaxis=dict(
            range=[-1, 81], showgrid=False, zeroline=False,
            showticklabels=False, fixedrange=True,
        ),
        yaxis=dict(
            range=[57, 125], showgrid=False, zeroline=False,
            showticklabels=False, fixedrange=True,
        ),
        height=470,
        plot_bgcolor=PITCH_BG,
        paper_bgcolor=PAPER_BG,
        hovermode="closest",
        legend=dict(
            x=1.02, xanchor="left", y=1, yanchor="top",
            orientation="v",
            bgcolor=LEGEND_BG,
            bordercolor="rgba(255,255,255,0.08)",
            borderwidth=1,
            font=dict(size=11, color=COLORS["text"]),
            tracegroupgap=6,
        ),
        margin=dict(l=16, r=178, t=54, b=18),
    ))
    fig.update_layout(**layout)
    return fig


def _build_shots_pitch_figure(shot_events: pd.DataFrame, player_name: str) -> go.Figure:
    """
    横向半场射门图。
    坐标变换：SB (sx, sy) → Plotly (px=sy, py=sx)
    球门在上（py≈120），中场在下（py=60）。
    """
    fig = _create_half_pitch_figure(f"{player_name} · Shots")
    if shot_events.empty:
        return fig
    shown_legend = set()
    for _, shot in shot_events.iterrows():
        sx0, sy0 = _extract_xy(_event_value(shot, ["location"]))
        end_loc = _event_value(shot, ["shot_end_location"])
        sx1, sy1 = _extract_xy(
            end_loc[:2] if isinstance(end_loc, (list, tuple, np.ndarray)) and len(end_loc) >= 2 else None
        )
        if sx0 is None or sx1 is None:
            continue
        # SB (sx, sy) → Plotly (px=sy, py=sx)
        px0, py0 = sy0, sx0
        px1, py1 = sy1, sx1
        body_part = _event_value(shot, ["shot_body_part", "shot_body_part_name"], "Other") or "Other"
        color = SHOT_BODY_PART_COLORS.get(body_part, SHOT_BODY_PART_COLORS["Other"])
        outcome = _event_value(shot, ["shot_outcome", "shot_outcome_name"], "N/A")
        is_goal = _normalize_text_key(outcome) == "goal"
        hover_text = (
            f"<b>{player_name}</b><br>"
            f"Minute: {shot.get('minute', 'N/A')}<br>"
            f"Outcome: {outcome}<br>"
            f"Technique: {_event_value(shot, ['shot_technique', 'shot_technique_name'], 'N/A')}<br>"
            f"xG: {float(_event_value(shot, ['shot_statsbomb_xg'], 0) or 0):.3f}<br>"
            f"Body Part: {body_part}"
        )
        show_legend = body_part not in shown_legend
        fig.add_trace(go.Scatter(
            x=[px0, px1], y=[py0, py1],
            mode="lines+markers+text" if is_goal else "lines+markers",
            line=dict(color=color, width=2.6),
            marker=dict(
                size=[6, 8 if is_goal else 12],
                color=[color, color],
                symbol=["circle", "circle" if is_goal else "x"],
                line=dict(color="rgba(255,255,255,0.25)", width=1),
            ),
            text=["", "⚽"] if is_goal else None,
            textfont=dict(size=18),
            textposition="middle center",
            hovertext=[hover_text, hover_text],
            hoverinfo="text",
            name=body_part,
            legendgroup=body_part,
            showlegend=show_legend,
        ))
        shown_legend.add(body_part)
    return fig


def _build_passes_pitch_figure(pass_events: pd.DataFrame, player_name: str, show_incomplete: bool) -> go.Figure:
    fig = _create_pitch_figure(f"{player_name} · Passes")
    if pass_events.empty:
        return fig
    pass_events = pass_events.copy()
    outcome_series = _first_existing_series(pass_events, ["pass_outcome", "pass_outcome_name"])
    height_series = _first_existing_series(pass_events, ["pass_height", "pass_height_name"])
    pass_events["pass_success"] = outcome_series.isna() if outcome_series is not None else True
    pass_events["_pass_height"] = height_series if height_series is not None else "Ground Pass"
    shown_legend = set()
    for is_success in [True, False]:
        if not is_success and not show_incomplete:
            continue
        for pass_height in ["Ground Pass", "Low Pass", "High Pass"]:
            subset = pass_events[
                (pass_events["pass_success"] == is_success) &
                (pass_events["_pass_height"].astype(str) == pass_height)
            ]
            if subset.empty:
                continue
            for _, event in subset.iterrows():
                x0, y0 = _extract_xy(_event_value(event, ["location"]))
                x1, y1 = _extract_xy(_event_value(event, ["pass_end_location"]))
                if x0 is None or x1 is None:
                    continue
                outcome_label = "Success" if is_success else "Incomplete"
                hover_text = (
                    f"<b>{player_name}</b><br>"
                    f"Minute: {event.get('minute', 'N/A')}<br>"
                    f"Height: {pass_height}<br>"
                    f"Body Part: {_event_value(event, ['pass_body_part', 'pass_body_part_name'], 'N/A')}<br>"
                    f"Outcome: {outcome_label}"
                )
                label = f"{pass_height} - {outcome_label}"
                show_legend = label not in shown_legend
                fig.add_trace(go.Scatter(
                    x=[x0, x1], y=[y0, y1],
                    mode="lines+markers",
                    line=dict(
                        color=PASS_HEIGHT_COLORS[pass_height],
                        dash="solid" if is_success else "dash",
                        width=1.9,
                    ),
                    marker=dict(
                        size=[5, 10],
                        color=[PASS_HEIGHT_COLORS[pass_height], PASS_HEIGHT_COLORS[pass_height]],
                        symbol=["circle", "triangle-right"],
                        line=dict(color="rgba(255,255,255,0.18)", width=1),
                    ),
                    hovertext=[hover_text, hover_text],
                    hoverinfo="text",
                    name=label,
                    legendgroup=label,
                    showlegend=show_legend,
                ))
                shown_legend.add(label)
    return fig


def _build_carries_pitch_figure(carry_events: pd.DataFrame, player_name: str) -> go.Figure:
    fig = _create_pitch_figure(f"{player_name} · Carries")
    if carry_events.empty:
        return fig
    shown_legend = set()
    for _, carry in carry_events.iterrows():
        x0, y0 = _extract_xy(_event_value(carry, ["location"]))
        x1, y1 = _extract_xy(_event_value(carry, ["carry_end_location"]))
        if x0 is None or x1 is None:
            continue
        obv = float(_event_value(carry, ["obv_total_net"], 0) or 0)
        color = "#3dd6a5" if obv > 0 else "#ff6b6b"
        label = "Positive OBV" if obv > 0 else "Negative OBV"
        hover_text = f"<b>{player_name}</b><br>Minute: {carry.get('minute', 'N/A')}<br>OBV Total Net: {obv:.3f}"
        fig.add_trace(go.Scatter(
            x=[x0, x1], y=[y0, y1],
            mode="lines+markers",
            line=dict(color=color, width=2.2),
            marker=dict(
                size=[5, 10],
                color=[color, color],
                symbol=["circle", "triangle-right"],
                line=dict(color="rgba(255,255,255,0.18)", width=1),
            ),
            hovertext=[hover_text, hover_text],
            hoverinfo="text",
            name=label,
            legendgroup=label,
            showlegend=label not in shown_legend,
        ))
        shown_legend.add(label)
    return fig


def _build_defensive_pitch_figure(defensive_events: pd.DataFrame, player_name: str) -> go.Figure:
    fig = _create_pitch_figure(f"{player_name} · Defensive Actions")
    if defensive_events.empty:
        return fig
    for event_type, cfg in DEFENSIVE_TYPE_CONFIG.items():
        type_series = _event_type_series(defensive_events)
        subset = defensive_events[type_series == event_type] if type_series is not None else pd.DataFrame()
        if subset.empty:
            continue
        xs, ys, hover_texts = [], [], []
        for _, event in subset.iterrows():
            x, y = _extract_xy(_event_value(event, ["location"]))
            if x is None:
                continue
            hover_info = f"<b>{player_name}</b><br>Type: {event_type}<br>Minute: {event.get('minute', 'N/A')}<br>"
            if event_type == "Block":
                for key, label in [("block_deflection", "Deflection"), ("block_offensive", "Offensive"), ("block_save_block", "Save Block")]:
                    if event.get(key) == True:
                        hover_info += f"{label}: TRUE<br>"
            elif event_type == "Clearance":
                hover_info += f"Body Part: {_event_value(event, ['clearance_body_part', 'clearance_body_part_name'], 'N/A')}<br>"
            elif event_type == "Ball Recovery":
                status = "Failure" if event.get("ball_recovery_recovery_failure") == True else "Success"
                hover_info += f"Status: {status}<br>"
            elif event_type == "Duel":
                hover_info += f"Duel Type: {_event_value(event, ['duel_type', 'duel_type_name'], 'N/A')}<br>"
                hover_info += f"Duel Outcome: {_event_value(event, ['duel_outcome', 'duel_outcome_name'], 'N/A')}<br>"
            xs.append(x)
            ys.append(y)
            hover_texts.append(hover_info)
        if not xs:
            continue
        fig.add_trace(go.Scatter(
            x=xs, y=ys,
            mode="markers",
            marker=dict(size=10, color=cfg["color"], symbol=cfg["symbol"], line=dict(color="white", width=1)),
            hovertext=hover_texts,
            hoverinfo="text",
            name=event_type,
        ))
    return fig


def _build_heatmap_pitch_figure(location_events: pd.DataFrame, player_name: str) -> go.Figure:
    fig = _create_pitch_figure(f"{player_name} · Heatmap")
    if location_events.empty:
        return fig
    location_series = _event_location_series(location_events)
    if location_series is None:
        return fig
    coords = [loc for loc in location_series.dropna().tolist() if _is_valid_location(loc)]
    if not coords:
        return fig
    locations = np.array([[loc[0], loc[1]] for loc in coords], dtype=float)
    fig.add_trace(go.Histogram2d(
        x=locations[:, 0],
        y=locations[:, 1],
        colorscale=[
            [0.0, "rgba(22,38,32,0.00)"],
            [0.20, "#23443a"],
            [0.45, "#1fbf8f"],
            [0.75, "#ffd166"],
            [1.0, "#ff6b6b"],
        ],
        xbins=dict(start=0, end=120, size=4),
        ybins=dict(start=0, end=80, size=4),
        zsmooth="best",
        colorbar=dict(title="Frequency", len=0.74, thickness=14),
        hovertemplate="Count: %{z}<extra></extra>",
        showscale=True,
    ))
    fig.update_traces(opacity=0.82)
    return fig


def _metric_spec_value(row, key: str, scope: str = "match", alt_keys: list | None = None):
    if row is None:
        return np.nan
    if key == "__pass_rate__":
        prefix = "player_match_" if scope == "match" else "player_season_"
        return _compute_pass_rate(row, prefix)

    lookup_key = key
    if scope == "season" and key.startswith("player_match_"):
        lookup_key = key.replace("player_match_", "player_season_")

    value = _coerce_numeric(row.get(lookup_key, np.nan))
    if not _is_numeric_value(value) and alt_keys:
        for alt_key in alt_keys:
            alt_lookup = alt_key.replace("player_match_", "player_season_") if scope == "season" else alt_key
            value = _coerce_numeric(row.get(alt_lookup, np.nan))
            if _is_numeric_value(value):
                break
    return value


def _compute_pass_rate(row, prefix: str):
    passes = _coerce_numeric(row.get(f"{prefix}passes", np.nan))
    successful = _coerce_numeric(row.get(f"{prefix}successful_passes", np.nan))
    if _is_numeric_value(passes) and passes > 0 and _is_numeric_value(successful):
        return successful / passes
    return np.nan


def _format_metric_value(value, pct: bool = False, precision: int = 1) -> str:
    if not _is_numeric_value(value):
        return "N/A"
    if pct:
        return f"{float(value) * 100:.1f}%"
    value = float(value)
    if float(value).is_integer():
        return f"{int(value)}"
    return f"{value:.{precision}f}"


def _format_metric_delta(value, pct: bool = False) -> str | None:
    if not _is_numeric_value(value):
        return None
    value = float(value)
    if pct:
        return f"{value * 100:+.1f}%"
    if value.is_integer():
        return f"{int(value):+d}"
    return f"{value:+.2f}"


def _is_numeric_value(value) -> bool:
    return value is not None and not (isinstance(value, float) and np.isnan(value))


def _coerce_numeric(value):
    try:
        if value is None or pd.isna(value):
            return np.nan
        return float(value)
    except (TypeError, ValueError):
        return np.nan


def _count_goal_shots(shot_events: pd.DataFrame) -> int:
    if shot_events.empty:
        return 0
    outcomes = _first_existing_series(shot_events, ["shot_outcome", "shot_outcome_name"])
    if outcomes is None:
        return 0
    return int(outcomes.astype(str).map(_normalize_text_key).eq("goal").sum())


def _sum_event_values(events_df: pd.DataFrame, columns: list[str]) -> float:
    if events_df.empty:
        return 0.0
    series = _first_existing_series(events_df, columns)
    if series is None:
        return 0.0
    numeric = pd.to_numeric(series, errors="coerce")
    return float(numeric.fillna(0).sum())


def _carry_success_mask(carry_events: pd.DataFrame) -> pd.Series:
    if carry_events.empty:
        return pd.Series(dtype=bool)
    if "carry_outcome" in carry_events.columns:
        return carry_events["carry_outcome"].isna()
    if "outcome" in carry_events.columns:
        return carry_events["outcome"].isna()
    if "carry_end_location" in carry_events.columns:
        return carry_events["carry_end_location"].apply(_is_valid_location)
    return pd.Series([True] * len(carry_events), index=carry_events.index)


def _defensive_action_counts(events_df: pd.DataFrame) -> dict:
    counts = {name: 0 for name in ["Ball Recovery", "Block", "Pressure", "Duel"]}
    if events_df.empty:
        return counts
    type_series = _event_type_series(events_df)
    if type_series is None:
        return counts
    for event_type in counts:
        counts[event_type] = int(type_series.astype(str).eq(event_type).sum())
    return counts


def _first_existing_series(df: pd.DataFrame, columns: list[str]):
    for col in columns:
        if col in df.columns:
            return df[col]
    return None


def _event_type_series(df: pd.DataFrame):
    return _first_existing_series(df, ["type", "type_name"])


def _event_player_series(df: pd.DataFrame):
    return _first_existing_series(df, ["player", "player_name"])


def _event_location_series(df: pd.DataFrame):
    return _first_existing_series(df, ["location"])


def _event_value(row, columns: list[str], default=None):
    for col in columns:
        if col in row.index:
            value = row.get(col)
            if value is not None and not (isinstance(value, float) and np.isnan(value)):
                return value
    return default


def _coerce_name_column(df: pd.DataFrame, base_col: str, name_col: str, keep_null: bool = False) -> None:
    """
    把 dict / *_name / 原始对象列统一成更易用的字符串列。
    keep_null=True 时保留 NaN，用于 pass_outcome 这种“为空即成功”的语义。
    """
    source_col = None
    if base_col in df.columns:
        source_col = base_col
    elif name_col in df.columns:
        source_col = name_col

    if source_col is None:
        return

    def _normalize_value(val):
        if val is None:
            return np.nan if keep_null else None
        if isinstance(val, float) and np.isnan(val):
            return np.nan if keep_null else None
        if isinstance(val, dict):
            for key in ("name", base_col, name_col):
                if key in val and val.get(key) not in (None, ""):
                    return val.get(key)
            return str(val)
        return val

    normalized = df[source_col].apply(_normalize_value)
    if keep_null:
        df[base_col] = normalized
    else:
        df[base_col] = normalized.fillna("")


def _render_event_data_status(player_events: pd.DataFrame, raw_events_df: pd.DataFrame, player_name: str):
    with st.expander("Event Data Status", expanded=False):
        st.write(f"Loaded event rows: {len(raw_events_df) if isinstance(raw_events_df, pd.DataFrame) else 0}")
        st.write(f"Filtered rows for player `{player_name}`: {len(player_events)}")
        if isinstance(raw_events_df, pd.DataFrame) and not raw_events_df.empty:
            show_cols = [c for c in [
                "type", "type_name", "player", "player_name", "location",
                "pass_end_location", "shot_end_location", "carry_end_location",
                "pass_height", "pass_outcome", "shot_body_part", "shot_outcome",
                "shot_technique", "obv_total_net"
            ] if c in raw_events_df.columns]
            st.write("Available event columns:", show_cols)
        else:
            st.info("No raw event rows were returned for this match.")


def _render_welcome():
    st.markdown("""
    <div style="text-align:center; padding: 60px 20px; color: #8b9bb4">
        <h2 style="font-size:2rem">📊 Player Match Stats</h2>
        <p style="font-size:1rem">
            Select a competition, season, match and player from the sidebar to begin.
        </p>
    </div>
    """, unsafe_allow_html=True)
