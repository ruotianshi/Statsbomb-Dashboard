"""
team_season.py
--------------
Team Season Dashboard 视图
包含：
  1. 球队 Profile Card（队徽、基础信息、赛季战绩）
  2. 分 Tab 展示球队赛季统计（进攻/防守/传控/OBV）
  3. 赛季积分走势折线图（实际积分 + xG 期望对比）
  4. 联赛内球队排名可视化（柱状排名 / 双维散点 / 联赛总览）
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from utils.data_loader import (
    compute_points_timeline,
    compute_team_record,
    load_competitions,
    load_matches,
    load_player_season_stats,
    load_team_season_stats,
)
from utils.image_helper import load_team_image
from utils.metrics_config import COLORS, METRIC_LABELS, PLOTLY_BASE_LAYOUT

# ─────────────────────────────────────────────
# 球队赛季统计指标分组
# ─────────────────────────────────────────────

TEAM_METRIC_GROUPS = {
    "Attacking": [
        ("team_season_np_xg_90",           "NP xG p90"),
        ("team_season_op_xg_90",           "OP xG p90"),
        ("team_season_sp_xg_90",           "SP xG p90"),
        ("team_season_np_xg_per_shot",     "NP xG per Shot"),
        ("team_season_np_shots_90",        "NP Shots p90"),
        ("team_season_op_shots_90",        "OP Shots p90"),
        ("team_season_deep_completions_90","Deep Completions p90"),
        ("team_season_passes_inside_box_90","Passes into Box p90"),
        ("team_season_box_cross_ratio",    "Box Cross Ratio"),
        ("team_season_counter_attacking_shots_90", "Counter Att Shots p90"),
        ("team_season_high_press_shots_90","High Press Shots p90"),
        ("team_season_xgchain_90",         "xG Chain p90"),
    ],
    "Defending": [
        ("team_season_np_xg_conceded_90",         "NP xG Conceded p90"),
        ("team_season_ppda",                      "PPDA"),
        ("team_season_defensive_distance",        "Defensive Distance"),
        ("team_season_pressure_regains_90",       "Pressure Regains p90"),
        ("team_season_counterpressure_regains_90","Counterpressure Regains p90"),
        ("team_season_fhalf_pressures_ratio",     "F-Half Pressure %"),
        ("team_season_deep_completions_conceded_90","Deep Comp Conceded p90"),
        ("team_season_padj_tackles_90",           "PAdj Tackles p90"),
        ("team_season_padj_interceptions_90",     "PAdj Interceptions p90"),
    ],
    "Possession": [
        ("team_season_possession",             "Possession %"),
        ("team_season_passing_ratio",          "Pass Completion %"),
        ("team_season_directness",             "Directness"),
        ("team_season_gk_pass_distance",       "GK Pass Distance"),
        ("team_season_gk_long_pass_ratio",     "GK Long Pass %"),
        ("team_season_op_passes_90",           "OP Passes p90"),
        ("team_season_pressures_90",           "Pressures p90"),
        ("team_season_pace_towards_goal",      "Pace Towards Goal"),
    ],
    "OBV": [
        ("team_season_obv_90",                  "OBV p90"),
        ("team_season_obv_pass_90",             "OBV Pass p90"),
        ("team_season_obv_shot_90",             "OBV Shot p90"),
        ("team_season_obv_defensive_action_90", "OBV Def Action p90"),
        ("team_season_obv_dribble_carry_90",    "OBV Dribble/Carry p90"),
    ],
}

# ─────────────────────────────────────────────
# 主入口
# ─────────────────────────────────────────────

def render():
    _render_sidebar_filters()

    comp_id   = st.session_state.get("ts_competition_id")
    season_id = st.session_state.get("ts_season_id")
    team_id   = st.session_state.get("ts_team_id")

    if not comp_id or not season_id:
        _render_welcome()
        return

    # 加载数据
    with st.spinner("Loading team data..."):
        matches_df = load_matches(comp_id, season_id)
        team_stats = load_team_season_stats(comp_id, season_id)

    if matches_df.empty:
        st.warning("No match data available for this competition / season.")
        return

    if team_id is None:
        _render_welcome()
        return

    # 获取当前球队行（team_season_stats 需要付费账户，可能为空）
    team_row = None
    if not team_stats.empty and "team_id" in team_stats.columns:
        rows = team_stats[team_stats["team_id"] == team_id]
        if not rows.empty:
            team_row = rows.iloc[0]

    # ── 主内容（每个 section 独立 try/except，避免一处报错导致全空）──
    try:
        _render_team_header(team_row, team_id, matches_df)
    except Exception as e:
        st.error(f"Error rendering team header: {e}")

    st.markdown('<hr style="border:1px solid #2a2d3e; margin:16px 0">', unsafe_allow_html=True)

    if team_row is not None:
        try:
            _render_stats_tabs(team_row, team_stats)
        except Exception as e:
            st.error(f"Error rendering stats tabs: {e}")
        st.markdown('<hr style="border:1px solid #2a2d3e; margin:16px 0">', unsafe_allow_html=True)
    else:
        st.info("ℹ️ Detailed team season stats require a paid StatsBomb subscription. "
                "Showing match-derived data below.")

    try:
        _render_points_timeline(matches_df, team_id)
    except Exception as e:
        st.error(f"Error rendering points timeline: {e}")

    st.markdown('<hr style="border:1px solid #2a2d3e; margin:16px 0">', unsafe_allow_html=True)

    if not team_stats.empty:
        try:
            _render_league_ranking(team_stats, team_id)
        except Exception as e:
            st.error(f"Error rendering league ranking: {e}")


# ─────────────────────────────────────────────
# Sidebar 筛选
# ─────────────────────────────────────────────

def _render_sidebar_filters():
    with st.sidebar:
        st.markdown("### 🔍 Data Filters")

        comps_df = load_competitions()
        if comps_df.empty:
            st.error("No competitions available.")
            return

        comp_names    = sorted(comps_df["competition_name"].unique().tolist())
        default_comp  = st.session_state.get("ts_competition_name", comp_names[0])
        if default_comp not in comp_names:
            default_comp = comp_names[0]

        comp_name = st.selectbox("Competition", comp_names,
                                 index=comp_names.index(default_comp),
                                 key="ts_comp_select")
        comp_id = int(comps_df[comps_df["competition_name"] == comp_name]["competition_id"].iloc[0])

        season_opts = (comps_df[comps_df["competition_name"] == comp_name]
                       [["season_id", "season_name"]].drop_duplicates()
                       .sort_values("season_name", ascending=False))
        season_names   = season_opts["season_name"].tolist()
        default_season = st.session_state.get("ts_season_name", season_names[0])
        if default_season not in season_names:
            default_season = season_names[0]

        season_name = st.selectbox("Season", season_names,
                                   index=season_names.index(default_season),
                                   key="ts_season_select")
        season_id = int(season_opts[season_opts["season_name"] == season_name]["season_id"].iloc[0])

        st.divider()
        st.markdown("### 🏟️ Team Selection")

        # 从 matches 提取球队列表
        matches_df   = load_matches(comp_id, season_id)
        team_options = _extract_teams_from_matches(matches_df)

        # 备用：若 matches 提取失败，尝试从 team_season_stats 获取球队列表
        if not team_options:
            ts_df = load_team_season_stats(comp_id, season_id)
            if not ts_df.empty and "team_name" in ts_df.columns and "team_id" in ts_df.columns:
                team_options = dict(zip(
                    ts_df["team_name"].astype(str),
                    ts_df["team_id"].astype(int),
                ))

        # 调试展开器：显示 matches 实际列结构（排查数据问题用）
        with st.expander("🔧 Debug: matches columns", expanded=False):
            if matches_df.empty:
                st.write("matches_df is **empty** — check credentials or competition/season.")
            else:
                st.write(f"Rows: {len(matches_df)} | Columns: {list(matches_df.columns)}")
                st.write("Sample home_team value:", matches_df["home_team"].iloc[0]
                          if "home_team" in matches_df.columns else "column not found")
                st.write("team_options extracted:", team_options)

        if team_options:
            team_names   = sorted(team_options.keys())
            prev_team_id = st.session_state.get("ts_team_id")
            prev_name    = None
            for n, tid in team_options.items():
                if tid == prev_team_id:
                    prev_name = n
                    break
            default_idx = team_names.index(prev_name) if prev_name in team_names else 0

            selected_team_name = st.selectbox(
                "Select Team",
                team_names,
                index=default_idx,
                key="ts_team_select",
            )
            selected_team_id = team_options[selected_team_name]
            st.caption(f"{len(team_names)} teams in this competition")
        else:
            st.warning("⚠️ Could not load team list. Open the debug panel above to diagnose.")
            selected_team_id = None

        # 写入 session_state
        st.session_state.update({
            "ts_competition_id":   comp_id,
            "ts_season_id":        season_id,
            "ts_competition_name": comp_name,
            "ts_season_name":      season_name,
            "ts_team_id":          selected_team_id,
            "ts_team_name":        selected_team_name if team_options else None,
        })


def _extract_teams_from_matches(matches_df: pd.DataFrame) -> dict:
    """
    从 matches DataFrame 提取所有球队 {team_name: team_id}
    
    statsbombpy 有三种结构，按优先级尝试：
      1. 扁平列: home_team_id / home_team_name
      2. dict 嵌套: home_team = {"home_team_id":..., "home_team_name":...}
      3. home_team 列直接是字符串队名（无 id）→ 用行号生成虚拟 id，
         同时在 matches_df 里注入 _home_team_str / _away_team_str 标记
    """
    teams = {}
    if matches_df.empty:
        return teams

    cols = matches_df.columns.tolist()

    # ── 方式1：扁平列 ──────────────────────────────
    if "home_team_id" in cols and "home_team_name" in cols:
        for _, row in matches_df.iterrows():
            try:
                h_id, h_name = row.get("home_team_id"), row.get("home_team_name", "")
                a_id, a_name = row.get("away_team_id"), row.get("away_team_name", "")
                if pd.notna(h_id) and h_name:
                    teams[str(h_name)] = int(h_id)
                if pd.notna(a_id) and a_name:
                    teams[str(a_name)] = int(a_id)
            except Exception:
                continue
        if teams:
            return teams

    # ── 方式2：dict 嵌套 ───────────────────────────
    if "home_team" in cols and "away_team" in cols:
        sample = matches_df["home_team"].dropna().iloc[0] if not matches_df.empty else None
        if isinstance(sample, dict):
            for _, row in matches_df.iterrows():
                try:
                    for side, id_key, name_key in [
                        ("home_team", "home_team_id", "home_team_name"),
                        ("away_team", "away_team_id", "away_team_name"),
                    ]:
                        val = row.get(side)
                        if isinstance(val, dict):
                            tid   = val.get(id_key)
                            tname = val.get(name_key, "")
                            if tid is not None and tname:
                                teams[str(tname)] = int(tid)
                except Exception:
                    continue
            if teams:
                return teams

    # ── 方式3：home_team 是纯字符串（队名）─────────
    # 没有 team_id，用队名本身作为 key，value 用枚举索引作为临时 id
    # _compute_timeline 会检测到这种情况改用队名匹配
    if "home_team" in cols:
        all_names = set()
        for _, row in matches_df.iterrows():
            h = row.get("home_team", "")
            a = row.get("away_team", "")
            if isinstance(h, str) and h:
                all_names.add(h)
            if isinstance(a, str) and a:
                all_names.add(a)
        # 用稳定的哈希生成虚拟 id（同一队名始终对应同一 id）
        for name in sorted(all_names):
            teams[name] = abs(hash(name)) % 1_000_000
        return teams

    return teams


def _detect_team_col_type(matches_df: pd.DataFrame) -> str:
    """
    检测 matches_df 的 home_team 列类型
    返回: 'flat' | 'dict' | 'str' | 'unknown'
    """
    if "home_team_id" in matches_df.columns:
        return "flat"
    if "home_team" not in matches_df.columns:
        return "unknown"
    sample = matches_df["home_team"].dropna().iloc[0] if not matches_df.empty else None
    if isinstance(sample, dict):
        return "dict"
    if isinstance(sample, str):
        return "str"
    return "unknown"


# ─────────────────────────────────────────────
# 球队 Profile Header
# ─────────────────────────────────────────────

def _render_team_header(team_row, team_id: int, matches_df: pd.DataFrame):
    record = compute_team_record(matches_df, team_id)

    # 队名优先级：team_season_stats → session_state → matches_df 反查
    if team_row is not None:
        team_name = team_row.get("team_name", "")
    else:
        team_name = st.session_state.get("ts_team_name", "")

    # 最后兜底：从 matches_df 反查队名（字符串模式下可直接取）
    if not team_name:
        col_type = _detect_team_col_type(matches_df)
        if col_type == "str":
            all_names = set()
            for _, row in matches_df.iterrows():
                for side in ("home_team", "away_team"):
                    v = row.get(side, "")
                    if isinstance(v, str) and v:
                        all_names.add(v)
            id_to_name = {abs(hash(n)) % 1_000_000: n for n in all_names}
            team_name = id_to_name.get(team_id, f"Team {team_id}")
        else:
            team_name = f"Team {team_id}"

    # 从 matches 提取主帅和主场球场
    manager_name, stadium_name = _extract_manager_stadium(matches_df, team_id)
    badge_team_id = _resolve_team_badge_id(team_row, team_id, team_name, matches_df)

    col_badge, col_info, col_record = st.columns([1, 4, 5], gap="medium")

    with col_badge:
        img = load_team_image(badge_team_id, size=(100, 100), team_name=team_name)
        st.image(img, width=100)

    with col_info:
        comp_name   = (team_row.get("competition_name", "") if team_row is not None else
                       st.session_state.get("ts_competition_name", ""))
        season_name = st.session_state.get("ts_season_name", "")

        st.markdown(f"""
        <div style="padding: 4px 0">
            <h2 style="margin:0; color:{COLORS['text']}; font-size:1.6rem">{team_name}</h2>
            <p style="margin:4px 0; color:{COLORS['muted']}; font-size:0.9rem">
                🏆 {comp_name} &nbsp;·&nbsp; 📅 {season_name}
            </p>
            <p style="margin:4px 0; font-size:0.85rem">
                👨‍💼 <b>Manager:</b> {manager_name}<br>
                🏟️ <b>Stadium:</b> {stadium_name}
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col_record:
        if record:
            c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
            c1.metric("Played",  record.get("played", 0))
            c2.metric("Won",     record.get("won", 0))
            c3.metric("Drawn",   record.get("drawn", 0))
            c4.metric("Lost",    record.get("lost", 0))
            c5.metric("GF",      record.get("gf", 0))
            c6.metric("GA",      record.get("ga", 0))
            gd = record.get("gd", 0)
            c7.metric("GD",      f"{'+' if gd >= 0 else ''}{gd}")

            st.markdown(
                f"<p style='font-size:1.15rem; color:{COLORS['primary']}; margin-top:6px'>"
                f"⭐ <b>Points: {record.get('points', 0)}</b></p>",
                unsafe_allow_html=True,
            )


def _extract_manager_stadium(matches_df: pd.DataFrame, team_id: int):
    """从 matches 数据提取主帅和主场球场名称，兼容三种数据结构"""
    manager_name = "N/A"
    stadium_name = "N/A"
    if matches_df.empty:
        return manager_name, stadium_name

    col_type = _detect_team_col_type(matches_df)

    # 字符串模式：先反查队名
    target_name = None
    if col_type == "str":
        all_names = set()
        for _, row in matches_df.iterrows():
            for side in ("home_team", "away_team"):
                v = row.get(side, "")
                if isinstance(v, str) and v:
                    all_names.add(v)
        id_to_name = {abs(hash(n)) % 1_000_000: n for n in all_names}
        target_name = id_to_name.get(team_id)
        if not target_name:
            return manager_name, stadium_name

    for _, row in matches_df.iterrows():
        # 判断是否是目标球队的主场
        is_home = False
        if col_type == "str":
            is_home = (str(row.get("home_team", "")) == target_name)
        elif col_type == "flat":
            v = row.get("home_team_id")
            is_home = (pd.notna(v) and int(v) == team_id)
        elif col_type == "dict":
            t = row.get("home_team", {})
            v = t.get("home_team_id") if isinstance(t, dict) else None
            is_home = (v is not None and int(v) == team_id)

        if is_home:
            stad = row.get("stadium")
            if isinstance(stad, dict):
                stadium_name = stad.get("name", "N/A")
            elif isinstance(stad, str) and stad:
                stadium_name = stad
            mgrs = row.get("home_managers", [])
            if isinstance(mgrs, list) and mgrs:
                m = mgrs[0]
                manager_name = m.get("name", "N/A") if isinstance(m, dict) else str(m)
            elif isinstance(mgrs, str) and mgrs:
                manager_name = mgrs
            break

    return manager_name, stadium_name


def _resolve_team_badge_id(team_row, team_id: int, team_name: str, matches_df: pd.DataFrame):
    """
    为队徽解析最可能的真实 team_id。

    优先级：
      1. team_season_stats 当前行里的 team_id
      2. player_season_stats 中按队名反查到的真实 team_id
      3. matches_df 中按队名反查到的真实 home/away_team_id
      4. 当前 session 里的 team_id
    """
    if team_row is not None:
        row_team_id = team_row.get("team_id")
        if pd.notna(row_team_id):
            try:
                return int(row_team_id)
            except (TypeError, ValueError):
                pass

    resolved_from_players = _lookup_real_team_id_from_player_stats(team_name)
    if resolved_from_players is not None:
        return resolved_from_players

    resolved_from_matches = _lookup_real_team_id_from_matches(matches_df, team_name)
    if resolved_from_matches is not None:
        return resolved_from_matches

    return team_id


def _lookup_real_team_id_from_player_stats(team_name: str) -> int | None:
    """
    通过 player_season_stats 按队名反查真实 team_id。
    这条链路和 Player Season 使用的是同一份球队 id 来源，最适合拿来找 badge。
    """
    if not team_name:
        return None

    comp_id = st.session_state.get("ts_competition_id")
    season_id = st.session_state.get("ts_season_id")
    if not comp_id or not season_id:
        return None

    try:
        players_df = load_player_season_stats(comp_id, season_id)
    except Exception:
        return None

    if players_df.empty or "team_name" not in players_df.columns or "team_id" not in players_df.columns:
        return None

    normalized_target = _normalize_team_key(team_name)
    team_names = players_df["team_name"].astype(str)
    normalized_names = team_names.map(_normalize_team_key)

    matched = players_df[normalized_names == normalized_target]
    if matched.empty:
        matched = players_df[
            normalized_names.str.contains(normalized_target, na=False)
            | pd.Series([normalized_target in name for name in normalized_names], index=players_df.index)
        ]
    if matched.empty:
        return None

    team_ids = matched["team_id"].dropna()
    if team_ids.empty:
        return None

    try:
        return int(team_ids.mode().iloc[0])
    except (TypeError, ValueError, IndexError):
        return None


def _lookup_real_team_id_from_matches(matches_df: pd.DataFrame, team_name: str) -> int | None:
    """从 matches_df 中按队名反查真实 team_id，兼容 flat / dict 两种结构。"""
    if matches_df.empty or not team_name:
        return None

    normalized_target = _normalize_team_key(team_name)
    if not normalized_target:
        return None

    for _, row in matches_df.iterrows():
        # flat columns
        for side in ("home", "away"):
            name_col = f"{side}_team_name"
            id_col = f"{side}_team_id"
            name_val = row.get(name_col)
            id_val = row.get(id_col)
            if (
                isinstance(name_val, str)
                and _team_names_match(name_val, normalized_target)
                and pd.notna(id_val)
            ):
                try:
                    return int(id_val)
                except (TypeError, ValueError):
                    pass

        # dict columns
        for side in ("home_team", "away_team"):
            team_val = row.get(side)
            if not isinstance(team_val, dict):
                continue

            name_key = f"{side}_name"
            id_key = f"{side}_id"
            name_val = team_val.get(name_key)
            id_val = team_val.get(id_key)
            if (
                isinstance(name_val, str)
                and _team_names_match(name_val, normalized_target)
                and id_val is not None
            ):
                try:
                    return int(id_val)
                except (TypeError, ValueError):
                    pass

    return None


def _normalize_team_key(value: str) -> str:
    """统一队名用于跨数据源匹配，忽略大小写、空格和常见标点差异。"""
    text = str(value).strip().lower()
    return "".join(ch for ch in text if ch.isalnum())


def _team_names_match(candidate: str, normalized_target: str) -> bool:
    """宽松比较两个队名，兼容 FC / AFC / 标点等命名差异。"""
    normalized_candidate = _normalize_team_key(candidate)
    if not normalized_candidate or not normalized_target:
        return False
    return (
        normalized_candidate == normalized_target
        or normalized_candidate in normalized_target
        or normalized_target in normalized_candidate
    )


# ─────────────────────────────────────────────
# 球队统计 Tab
# ─────────────────────────────────────────────

def _render_stats_tabs(team_row, all_teams_df: pd.DataFrame):
    st.markdown("#### 📊 Season Statistics")
    tab_names = list(TEAM_METRIC_GROUPS.keys())
    tabs = st.tabs([f"⚔️ {t}" if t == "Attacking" else
                    f"🛡️ {t}" if t == "Defending" else
                    f"🎯 {t}" if t == "Possession" else
                    f"📈 {t}" for t in tab_names])

    for tab, group_name in zip(tabs, tab_names):
        with tab:
            metrics = TEAM_METRIC_GROUPS[group_name]
            # 计算联赛均值
            _render_team_stats_grid(team_row, all_teams_df, metrics)


def _render_team_stats_grid(team_row, all_df: pd.DataFrame, metrics: list):
    """按 4 列渲染指标卡片，显示值 + 联赛均值 delta"""
    valid = [(col, lbl) for col, lbl in metrics
             if col in (all_df.columns if not all_df.empty else []) or
             (team_row is not None and col in team_row.index)]

    if not valid:
        st.info("No data available for this metric group.")
        return

    # 每行 4 个
    chunk_size = 4
    for i in range(0, len(valid), chunk_size):
        chunk = valid[i: i + chunk_size]
        cols  = st.columns(len(chunk))
        for j, (col, lbl) in enumerate(chunk):
            val = team_row.get(col, np.nan) if team_row is not None else np.nan
            avg = all_df[col].mean() if (not all_df.empty and col in all_df.columns) else np.nan

            if isinstance(val, (int, float)) and not (isinstance(val, float) and np.isnan(val)):
                is_pct = any(kw in col for kw in ["ratio", "possession", "proportion"])
                fmt = f"{val*100:.1f}%" if is_pct else f"{val:.3f}"
                if not np.isnan(avg):
                    delta = float(val) - float(avg)
                    delta_fmt = f"{delta*100:+.1f}%" if is_pct else f"{delta:+.3f}"
                    cols[j].metric(lbl, fmt, delta=delta_fmt)
                else:
                    cols[j].metric(lbl, fmt)
            else:
                cols[j].metric(lbl, "N/A")


# ─────────────────────────────────────────────
# 积分走势折线图
# ─────────────────────────────────────────────

def _render_points_timeline(matches_df: pd.DataFrame, team_id: int):
    st.markdown("#### 📈 Points Timeline")

    # ── 诊断展开器 ──────────────────────────────
    with st.expander("🔧 Debug: Points Timeline", expanded=False):
        st.write(f"**team_id passed in:** `{team_id}` (type: `{type(team_id).__name__}`)")
        st.write(f"**matches_df rows:** {len(matches_df)}")
        if not matches_df.empty:
            cols = matches_df.columns.tolist()
            col_type = _detect_team_col_type(matches_df)
            st.write(f"**col_type detected:** `{col_type}`")
            show_cols = [c for c in ["home_team_id","home_team_name","away_team_id",
                                      "away_team_name","home_team","away_team",
                                      "home_score","away_score","match_date"] if c in cols]
            st.dataframe(matches_df[show_cols].head(3))

    # ── 主队 timeline ─────────────────────────────
    main_timeline = _compute_timeline(matches_df, team_id)
    if main_timeline.empty:
        st.info("No match data to build points timeline.")
        return

    # ── 对比队伍选择 ──────────────────────────────
    # 从 matches_df 提取本赛季所有球队选项（排除当前球队）
    all_teams = _extract_teams_from_matches(matches_df)
    current_team_name = st.session_state.get("ts_team_name", "")
    compare_options = [n for n, tid in all_teams.items()
                       if tid != team_id and n != current_team_name]
    compare_options = sorted(compare_options)

    compare_sel = st.multiselect(
        "➕ Add teams to compare",
        options=compare_options,
        default=[],
        max_selections=4,
        key="ts_timeline_compare",
        help="Add up to 4 other teams from the same season to compare points progression",
    )

    # ── 颜色映射 ──────────────────────────────────
    result_color  = {"W": COLORS["primary"], "D": COLORS["warning"], "L": COLORS["danger"]}
    marker_symbol = {"W": "circle", "D": "square", "L": "x"}

    # 对比队颜色序列
    compare_colors = ["#4e9af1", "#f7d716", "#ff6b35", "#c084fc"]

    fig = go.Figure()

    # ── 对比队折线（先画，在主队下面）─────────────
    for i, cmp_name in enumerate(compare_sel):
        cmp_id = all_teams.get(cmp_name)
        if cmp_id is None:
            continue
        cmp_timeline = _compute_timeline(matches_df, cmp_id)
        if cmp_timeline.empty:
            continue

        cmp_color = compare_colors[i % len(compare_colors)]
        cmp_hover = [
            f"<b>{cmp_name}</b><br>"
            f"{r['match_date'].strftime('%d %b %Y')}<br>"
            f"{'🏠 Home' if r['venue']=='H' else '✈️ Away'} vs {r['opponent']}<br>"
            f"Score: {r['gf']}–{r['ga']} "
            f"{'✅' if r['result']=='W' else ('➖' if r['result']=='D' else '❌')}<br>"
            f"Cumulative: <b>{r['cumulative_points']} pts</b>"
            for _, r in cmp_timeline.iterrows()
        ]

        fig.add_trace(go.Scatter(
            x=cmp_timeline["match_date"],
            y=cmp_timeline["cumulative_points"],
            mode="lines+markers",
            name=cmp_name,
            line=dict(color=cmp_color, width=1.8, dash="dot"),
            marker=dict(size=6, color=cmp_color),
            hovertext=cmp_hover,
            hoverinfo="text",
            opacity=0.75,
        ))

    # ── 主队形势色块 ──────────────────────────────
    for _, row in main_timeline.iterrows():
        fc = result_color.get(row["result"], COLORS["muted"])
        fig.add_vrect(
            x0=row["match_date"], x1=row["match_date"],
            fillcolor=fc, opacity=0.08, layer="below", line_width=0,
        )

    # ── 主队 hover ────────────────────────────────
    main_name = current_team_name or f"Team {team_id}"
    hover_texts = []
    for _, r in main_timeline.iterrows():
        venue_str    = "🏠 Home" if r["venue"] == "H" else "✈️ Away"
        result_emoji = {"W": "✅", "D": "➖", "L": "❌"}.get(r["result"], "")
        mgr_str  = f"<br>👨‍💼 {r['home_manager']}"  if r.get("home_manager") else ""
        opp_mgr  = f" vs {r['away_manager']}"       if r.get("away_manager") else ""
        hover_texts.append(
            f"<b>{main_name}</b><br>"
            f"{r['match_date'].strftime('%d %b %Y')}<br>"
            f"{venue_str} vs <b>{r['opponent']}</b><br>"
            f"Score: <b>{r['gf']}–{r['ga']}</b> {result_emoji}<br>"
            f"Points this game: <b>{r['points_gained']}</b><br>"
            f"Cumulative: <b>{r['cumulative_points']} pts</b>"
            f"{mgr_str}{opp_mgr}"
        )

    # ── 主队折线（粗线、实线、置于最前）─────────────
    fig.add_trace(go.Scatter(
        x=main_timeline["match_date"],
        y=main_timeline["cumulative_points"],
        mode="lines+markers",
        name=main_name,
        line=dict(color=COLORS["primary"], width=2.8),
        marker=dict(
            size=10,
            color=[result_color.get(r, COLORS["muted"]) for r in main_timeline["result"]],
            symbol=[marker_symbol.get(r, "circle") for r in main_timeline["result"]],
            line=dict(color="white", width=1.2),
        ),
        hovertext=hover_texts,
        hoverinfo="text",
    ))

    # ── 参考线 ────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=main_timeline["match_date"],
        y=list(range(3, (len(main_timeline) + 1) * 3, 3)),
        mode="lines", name="Max Possible",
        line=dict(color=COLORS["grid"], width=1, dash="dot"),
        hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=main_timeline["match_date"],
        y=[1.5 * i for i in range(1, len(main_timeline) + 1)],
        mode="lines", name="Avg Pace (1.5 pts/g)",
        line=dict(color=COLORS["muted"], width=1, dash="dash"),
        hoverinfo="skip",
    ))

    # 最后一场积分标注
    last = main_timeline.iloc[-1]
    fig.add_annotation(
        x=last["match_date"], y=last["cumulative_points"],
        text=f"  <b>{last['cumulative_points']} pts</b>",
        showarrow=False, font=dict(color=COLORS["primary"], size=12), xanchor="left",
    )

    layout = {**PLOTLY_BASE_LAYOUT}
    layout.update(dict(
        xaxis=dict(
            title="Match Date", type="date",
            gridcolor=COLORS["grid"], linecolor=COLORS["grid"],
            tickformat="%d %b",
        ),
        yaxis=dict(
            title="Cumulative Points",
            gridcolor=COLORS["grid"], linecolor=COLORS["grid"],
            rangemode="tozero",
        ),
        height=400,
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.22, x=0.5, xanchor="center"),
        margin=dict(l=20, r=20, t=20, b=70),
    ))
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True)

    # ── 近期5场形势卡片 ───────────────────────────
    recent = main_timeline.tail(5)
    if not recent.empty:
        st.markdown("**Recent Form (last 5 matches)**")
        cols = st.columns(5)
        for i, (_, r) in enumerate(recent.iterrows()):
            bg = {"W": "#003d2e", "D": "#3d3000", "L": "#3d0000"}.get(r["result"], "#1a1d2e")
            fg = result_color.get(r["result"], COLORS["muted"])
            cols[i].markdown(
                f"""<div style="background:{bg}; border:1px solid {fg}; border-radius:8px;
                    padding:8px; text-align:center">
                    <div style="font-size:1.1rem; font-weight:700; color:{fg}">{r['result']}</div>
                    <div style="font-size:0.7rem; color:{COLORS['muted']}">{r['gf']}–{r['ga']}</div>
                    <div style="font-size:0.65rem; color:{COLORS['muted']}">{str(r['opponent'])[:10]}</div>
                </div>""",
                unsafe_allow_html=True,
            )


def _compute_timeline(matches_df: pd.DataFrame, team_id: int) -> pd.DataFrame:
    """
    从 matches_df 计算逐场积分走势
    自动检测 home_team 列的类型并选择对应匹配策略：
      - 'flat': 用 home_team_id 整数比较
      - 'dict': 用 home_team["home_team_id"] 整数比较
      - 'str' : 用 home_team 字符串队名比较
                （此时 team_id 是从 hash(team_name) 生成的虚拟 id，
                 需要先反查出真实队名）
    """
    if matches_df.empty:
        return pd.DataFrame()

    col_type = _detect_team_col_type(matches_df)

    # ── 字符串模式：team_id 是虚拟 hash id，需反查队名 ──
    if col_type == "str":
        # 重建 name→虚拟id 映射，反查当前 team_id 对应的队名
        all_names = set()
        for _, row in matches_df.iterrows():
            h = row.get("home_team", "")
            a = row.get("away_team", "")
            if isinstance(h, str) and h:
                all_names.add(h)
            if isinstance(a, str) and a:
                all_names.add(a)
        name_to_id = {name: abs(hash(name)) % 1_000_000 for name in all_names}
        id_to_name = {v: k for k, v in name_to_id.items()}
        target_name = id_to_name.get(team_id)

        if not target_name:
            return pd.DataFrame()

        rows = []
        for _, row in matches_df.sort_values("match_date").iterrows():
            try:
                h_name = str(row.get("home_team", ""))
                a_name = str(row.get("away_team", ""))

                if h_name == target_name:
                    h_score = row.get("home_score")
                    a_score = row.get("away_score")
                    if pd.isna(h_score) or pd.isna(a_score):
                        continue
                    gf, ga = int(h_score), int(a_score)
                    opp    = a_name
                    venue  = "H"
                elif a_name == target_name:
                    h_score = row.get("home_score")
                    a_score = row.get("away_score")
                    if pd.isna(h_score) or pd.isna(a_score):
                        continue
                    gf, ga = int(a_score), int(h_score)
                    opp    = h_name
                    venue  = "A"
                else:
                    continue

                result = "W" if gf > ga else ("D" if gf == ga else "L")
                pts    = 3 if result == "W" else (1 if result == "D" else 0)

                home_mgr = _get_manager_from_row(row, "home")
                away_mgr = _get_manager_from_row(row, "away")

                rows.append({
                    "match_id":      row.get("match_id", ""),
                    "match_date":    pd.to_datetime(row["match_date"]),
                    "match_week":    row.get("match_week", len(rows) + 1),
                    "opponent":      opp,
                    "venue":         venue,
                    "result":        result,
                    "gf":            gf,
                    "ga":            ga,
                    "points_gained": pts,
                    "home_manager":  home_mgr,
                    "away_manager":  away_mgr,
                })
            except Exception:
                continue

        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        df["cumulative_points"] = df["points_gained"].cumsum()
        return df

    # ── 扁平列 / dict 嵌套模式：用 team_id 整数比较 ────
    has_flat = (col_type == "flat")

    def _get_id(row, side):
        if has_flat:
            v = row.get(f"{side}_team_id")
            return int(v) if pd.notna(v) else None
        t = row.get(f"{side}_team", {})
        v = t.get(f"{side}_team_id") if isinstance(t, dict) else None
        return int(v) if v is not None else None

    def _get_name(row, side):
        if has_flat:
            return str(row.get(f"{side}_team_name", ""))
        t = row.get(f"{side}_team", {})
        return str(t.get(f"{side}_team_name", "")) if isinstance(t, dict) else ""

    rows = []
    for _, row in matches_df.sort_values("match_date").iterrows():
        try:
            h_id = _get_id(row, "home")
            a_id = _get_id(row, "away")

            if h_id == team_id:
                h_score = row.get("home_score")
                a_score = row.get("away_score")
                if pd.isna(h_score) or pd.isna(a_score):
                    continue
                gf, ga   = int(h_score), int(a_score)
                opp      = _get_name(row, "away")
                venue    = "H"
                home_mgr = _get_manager_from_row(row, "home")
                away_mgr = _get_manager_from_row(row, "away")
            elif a_id == team_id:
                h_score = row.get("home_score")
                a_score = row.get("away_score")
                if pd.isna(h_score) or pd.isna(a_score):
                    continue
                gf, ga   = int(a_score), int(h_score)
                opp      = _get_name(row, "home")
                venue    = "A"
                home_mgr = _get_manager_from_row(row, "away")
                away_mgr = _get_manager_from_row(row, "home")
            else:
                continue

            result = "W" if gf > ga else ("D" if gf == ga else "L")
            pts    = 3 if result == "W" else (1 if result == "D" else 0)

            rows.append({
                "match_id":      row.get("match_id", ""),
                "match_date":    pd.to_datetime(row["match_date"]),
                "match_week":    row.get("match_week", len(rows) + 1),
                "opponent":      opp,
                "venue":         venue,
                "result":        result,
                "gf":            gf,
                "ga":            ga,
                "points_gained": pts,
                "home_manager":  home_mgr,
                "away_manager":  away_mgr,
            })
        except Exception:
            continue

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["cumulative_points"] = df["points_gained"].cumsum()
    return df


def _get_manager_from_row(row, side: str) -> str:
    """从 matches 行提取指定边的主教练名"""
    mgrs = row.get(f"{side}_managers", [])
    if isinstance(mgrs, list) and mgrs:
        m = mgrs[0]
        return m.get("name", "") if isinstance(m, dict) else str(m)
    if isinstance(mgrs, str):
        return mgrs
    return ""


# ─────────────────────────────────────────────
# 联赛排名对比
# ─────────────────────────────────────────────

def _render_league_ranking(team_stats: pd.DataFrame, highlight_team_id: int):
    st.markdown("#### 🏆 League Ranking Comparison")

    effective_highlight_id = _resolve_team_highlight_id(team_stats, highlight_team_id)

    view_tabs = st.tabs(["📊 Bar Ranking", "🔵 Scatter (2D)", "🕸️ League Overview"])

    with view_tabs[0]:
        _render_bar_ranking_view(team_stats, effective_highlight_id)
    with view_tabs[1]:
        _render_scatter_view(team_stats, effective_highlight_id)
    with view_tabs[2]:
        _render_overview_radar(team_stats, effective_highlight_id)


def _get_all_numeric_metrics(df: pd.DataFrame) -> dict:
    """
    从 team_season_stats DataFrame 提取所有数值列
    返回 {readable_label: col_name}
    """
    numeric_cols = [c for c in df.select_dtypes(include="number").columns
                    if c not in ("team_id", "competition_id", "season_id", "account_id")]
    result = {}
    for col in sorted(numeric_cols):
        # 生成可读标签：去掉 team_season_ 前缀，替换下划线
        label = col.replace("team_season_", "").replace("team_match_", "").replace("_", " ").title()
        result[label] = col
    return result


# ── 视图A：柱状排名（无 Metric Group，显示全部 metrics）────

def _render_bar_ranking_view(df: pd.DataFrame, highlight_id: int):
    all_metrics = _get_all_numeric_metrics(df)
    if not all_metrics:
        st.info("No numeric metrics available.")
        return

    ctrl1, ctrl2, ctrl3 = st.columns([3, 2, 1])

    with ctrl1:
        metric_lbl = st.selectbox(
            "Metric",
            list(all_metrics.keys()),
            key="ts_bar_metric_v2",
        )
        metric_col = all_metrics[metric_lbl]

    with ctrl2:
        team_name_map = _build_team_name_map(df)
        compare_options = [n for n, i in team_name_map.items() if i != highlight_id]
        compare_sel = st.multiselect(
            "Compare Teams (highlight)",
            compare_options,
            default=[],
            max_selections=3,
            key="ts_compare_teams_v2",
        )
        compare_ids = [team_name_map[n] for n in compare_sel if n in team_name_map]

    with ctrl3:
        ascending = st.toggle("↑ Asc", value=False, key="ts_bar_asc_v2")

    _fig = _build_team_bar(df, metric_col, metric_lbl, highlight_id, compare_ids, ascending)
    st.plotly_chart(_fig, use_container_width=True)


def _build_team_bar(df, metric, metric_label, highlight_id, compare_ids, ascending):
    sub = df.dropna(subset=[metric]).copy()
    # Plotly 横向柱状图：row[-1] 在顶部
    # ascending=False（最高在顶）→ sort ascending=True + 不截断（全显示）
    # ascending=True（最低在顶）→ sort ascending=False
    sub = sub.sort_values(metric, ascending=(not ascending))

    name_col = "team_name" if "team_name" in sub.columns else sub.columns[0]
    ids_col  = "team_id"   if "team_id"   in sub.columns else None

    colors = []
    for _, row in sub.iterrows():
        tid = row.get(ids_col) if ids_col else None
        if tid == highlight_id:
            colors.append(COLORS["primary"])
        elif tid in compare_ids:
            colors.append(COLORS["secondary"])
        else:
            colors.append(COLORS["muted"])

    fig = go.Figure(go.Bar(
        x=sub[metric],
        y=sub[name_col],
        orientation="h",
        marker=dict(color=colors, opacity=0.82, line=dict(width=0)),
        text=[f"{v:.3f}" for v in sub[metric]],
        textposition="outside",
        textfont=dict(size=9.5, color=COLORS["text"]),
        hovertemplate="<b>%{y}</b><br>" + metric_label + ": %{x:.3f}<extra></extra>",
    ))

    layout = {**PLOTLY_BASE_LAYOUT}
    layout.update(dict(
        title=dict(text=f"League Ranking · <b>{metric_label}</b>",
                   font=dict(size=13), x=0),
        xaxis=dict(gridcolor=COLORS["grid"], linecolor=COLORS["grid"],
                   zeroline=False, tickfont=dict(size=10)),
        yaxis=dict(automargin=True, tickfont=dict(size=10, color=COLORS["text"]),
                   gridcolor="rgba(0,0,0,0)"),
        bargap=0.28,
        height=max(340, len(sub) * 26),
        margin=dict(l=10, r=80, t=45, b=20),
    ))
    fig.update_layout(**layout)
    return fig


# ── 视图B：双维散点（全 metrics + 标准化开关）────────────

def _render_scatter_view(df: pd.DataFrame, highlight_id: int):
    all_metrics = _get_all_numeric_metrics(df)
    if len(all_metrics) < 2:
        st.info("Not enough metrics for scatter plot.")
        return

    metric_keys = list(all_metrics.keys())

    ctrl1, ctrl2 = st.columns(2)
    default_x = next((k for k in metric_keys if "xg" in k.lower() and "conceded" not in k.lower()), metric_keys[0])
    default_y = next((k for k in metric_keys if "conceded" in k.lower()), metric_keys[1])

    with ctrl1:
        x_label = st.selectbox("X Axis", metric_keys,
                                index=metric_keys.index(default_x),
                                key="ts_scatter_x_v2")
    with ctrl2:
        y_label = st.selectbox("Y Axis", metric_keys,
                                index=metric_keys.index(default_y),
                                key="ts_scatter_y_v2")

    # 标准化开关
    standardize = st.toggle(
        "Standardise (z-score)",
        value=False,
        key="ts_scatter_standardize",
        help="Normalise both axes to z-scores so metrics on different scales are comparable",
    )

    x_col = all_metrics[x_label]
    y_col = all_metrics[y_label]

    sub = df.dropna(subset=[x_col, y_col]).copy()
    if sub.empty:
        st.info("No data for selected metrics.")
        return

    x_vals = sub[x_col].astype(float)
    y_vals = sub[y_col].astype(float)

    x_axis_label = x_label
    y_axis_label = y_label

    if standardize:
        x_mean, x_std = x_vals.mean(), x_vals.std()
        y_mean, y_std = y_vals.mean(), y_vals.std()
        x_vals = (x_vals - x_mean) / x_std if x_std > 0 else x_vals * 0
        y_vals = (y_vals - y_mean) / y_std if y_std > 0 else y_vals * 0
        x_axis_label += " (z)"
        y_axis_label += " (z)"

    name_col = "team_name" if "team_name" in sub.columns else sub.columns[0]
    id_col   = "team_id"   if "team_id"   in sub.columns else None

    point_colors = [
        COLORS["primary"] if (id_col and row.get(id_col) == highlight_id) else COLORS["muted"]
        for _, row in sub.iterrows()
    ]
    point_sizes = [
        16 if (id_col and row.get(id_col) == highlight_id) else 9
        for _, row in sub.iterrows()
    ]

    fig = go.Figure()
    fig.add_vline(x=float(x_vals.mean()), line=dict(color=COLORS["grid"], width=1, dash="dot"))
    fig.add_hline(y=float(y_vals.mean()), line=dict(color=COLORS["grid"], width=1, dash="dot"))

    fig.add_trace(go.Scatter(
        x=x_vals, y=y_vals,
        mode="markers+text",
        text=sub[name_col],
        textposition="top center",
        textfont=dict(size=8, color=COLORS["text"]),
        marker=dict(color=point_colors, size=point_sizes,
                    line=dict(color="white", width=0.5), opacity=0.85),
        customdata=sub[[sub.columns[0] if name_col not in sub.columns else name_col,
                        x_col, y_col]].values,
        hovertemplate=(
            "<b>%{text}</b><br>"
            + x_label + ": %{customdata[1]:.3f}<br>"
            + y_label + ": %{customdata[2]:.3f}<extra></extra>"
        ),
    ))

    layout = {**PLOTLY_BASE_LAYOUT}
    layout.update(dict(
        title=dict(text=f"<b>{x_axis_label}</b> vs <b>{y_axis_label}</b>",
                   font=dict(size=13), x=0),
        xaxis=dict(title=x_axis_label, gridcolor=COLORS["grid"],
                   linecolor=COLORS["grid"], tickfont=dict(size=10)),
        yaxis=dict(title=y_axis_label, gridcolor=COLORS["grid"],
                   linecolor=COLORS["grid"], tickfont=dict(size=10)),
        height=500,
        margin=dict(l=20, r=20, t=40, b=20),
        hovermode="closest",
    ))
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True)


# ── 视图C：联赛总览雷达（可选 metrics + 可调变量数量）────

def _render_overview_radar(df: pd.DataFrame, highlight_id: int):
    all_metrics = _get_all_numeric_metrics(df)
    metric_keys = list(all_metrics.keys())

    if len(metric_keys) < 3:
        st.info("Insufficient metrics for radar chart.")
        return

    # ── 控制区 ────────────────────────────────────
    st.markdown("**Radar Metrics Selection**")

    # 默认 6 个核心指标
    default_labels = []
    for kw in ["Np Xg 90", "Np Xg Conceded", "Possession", "Ppda", "Passing Ratio", "Obv 90"]:
        match = next((k for k in metric_keys if kw.lower() in k.lower()), None)
        if match:
            default_labels.append(match)
    if not default_labels:
        default_labels = metric_keys[:6]

    selected_labels = st.multiselect(
        "Select metrics for radar (3–10)",
        options=metric_keys,
        default=default_labels[:6],
        key="ts_radar_metrics",
        help="Choose 3 to 10 metrics to display on the league overview radar",
    )

    if len(selected_labels) < 3:
        st.warning("Please select at least 3 metrics.")
        return
    if len(selected_labels) > 10:
        st.warning("Maximum 10 metrics. Only the first 10 will be used.")
        selected_labels = selected_labels[:10]

    cols_sel   = [all_metrics[lbl] for lbl in selected_labels]
    labels_sel = selected_labels

    # 对选中列进行 min-max 归一化到 0-1
    norm_df = df.copy()
    for c in cols_sel:
        if c not in norm_df.columns:
            norm_df[c] = 0.5
            continue
        mn, mx = df[c].min(), df[c].max()
        norm_df[c] = (df[c] - mn) / (mx - mn) if mx > mn else 0.5

    name_col = "team_name" if "team_name" in norm_df.columns else norm_df.columns[0]
    id_col   = "team_id"   if "team_id"   in norm_df.columns else None
    n_teams  = len(norm_df)
    n_cols   = min(5, n_teams)
    n_rows   = (n_teams + n_cols - 1) // n_cols

    fig = make_subplots(
        rows=n_rows, cols=n_cols,
        specs=[[{"type": "polar"}] * n_cols for _ in range(n_rows)],
        vertical_spacing=0.06,
        horizontal_spacing=0.04,
    )

    theta = labels_sel + [labels_sel[0]]

    for i, (_, row) in enumerate(norm_df.iterrows()):
        r_idx = i // n_cols + 1
        c_idx = i % n_cols  + 1
        tid   = row.get(id_col) if id_col else None
        is_hl = (tid == highlight_id)
        color = COLORS["primary"] if is_hl else COLORS["muted"]
        fill  = "rgba(0,212,170,0.25)" if is_hl else "rgba(139,155,180,0.12)"

        r_vals = [round(float(row.get(c, 0) or 0), 3) for c in cols_sel] + \
                 [round(float(row.get(cols_sel[0], 0) or 0), 3)]

        fig.add_trace(
            go.Scatterpolar(
                r=r_vals, theta=theta,
                fill="toself",
                fillcolor=fill,
                line=dict(color=color, width=1.8 if is_hl else 0.8),
                name=row[name_col],
                hoverinfo="name+r",
            ),
            row=r_idx, col=c_idx,
        )
        fig.add_annotation(
            text=f"<b>{str(row[name_col])[:12]}</b>" if is_hl else str(row[name_col])[:12],
            x=(c_idx - 1 + 0.5) / n_cols,
            y=1.0 - (r_idx - 1) / n_rows,
            xref="paper", yref="paper",
            showarrow=False,
            font=dict(size=8, color=color),
            xanchor="center",
        )

    for i in range(1, n_rows * n_cols + 1):
        key = f"polar{i}" if i > 1 else "polar"
        is_hl_cell = (i - 1) < n_teams and id_col and \
                     (norm_df.iloc[i - 1].get(id_col) == highlight_id)
        fig.update_layout(**{
            key: dict(
                bgcolor="#1a3a2a" if is_hl_cell else COLORS["bg_card"],
                radialaxis=dict(visible=False, range=[0, 1]),
                angularaxis=dict(
                    tickfont=dict(size=6, color=COLORS["muted"]),
                    gridcolor=COLORS["grid"],
                ),
            )
        })

    layout = {**PLOTLY_BASE_LAYOUT}
    layout.update(dict(
        title=dict(
            text=f"League Overview · {len(selected_labels)} Metrics (normalised 0–1)",
            font=dict(size=13), x=0,
        ),
        showlegend=False,
        height=max(320, n_rows * 210),
        margin=dict(l=10, r=10, t=40, b=10),
    ))
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True)



# ─────────────────────────────────────────────
# 辅助
# ─────────────────────────────────────────────

PITCH_COLOR = "#1a1d2e"

def _build_team_name_map(df: pd.DataFrame) -> dict:
    if "team_name" in df.columns and "team_id" in df.columns:
        return dict(zip(df["team_name"], df["team_id"]))
    return {}


def _resolve_team_highlight_id(team_stats: pd.DataFrame, current_team_id: int) -> int:
    """
    为 League Ranking 视图解析 team_stats 内部可识别的高亮 team_id。
    当前 session 中的 ts_team_id 可能来自 matches 的临时/虚拟 id，需要按队名映射回 team_stats 真实 id。
    """
    if team_stats.empty or "team_id" not in team_stats.columns:
        return current_team_id

    team_ids = pd.to_numeric(team_stats["team_id"], errors="coerce").dropna().astype(int)
    if not team_ids.empty and current_team_id in set(team_ids.tolist()):
        return current_team_id

    team_name = st.session_state.get("ts_team_name", "")
    if not team_name or "team_name" not in team_stats.columns:
        return current_team_id

    normalized_target = _normalize_team_key(team_name)
    normalized_names = team_stats["team_name"].astype(str).map(_normalize_team_key)

    matched = team_stats[normalized_names == normalized_target]
    if matched.empty:
        matched = team_stats[
            normalized_names.str.contains(normalized_target, na=False)
            | pd.Series([normalized_target in name for name in normalized_names], index=team_stats.index)
        ]

    if matched.empty:
        return current_team_id

    resolved_ids = pd.to_numeric(matched["team_id"], errors="coerce").dropna().astype(int)
    if resolved_ids.empty:
        return current_team_id

    return int(resolved_ids.mode().iloc[0])


def _render_welcome():
    st.markdown("""
    <div style="text-align:center; padding: 60px 20px; color: #8b9bb4">
        <h2 style="font-size:2rem">🏟️ Team Season Dashboard</h2>
        <p style="font-size:1rem">
            Select a competition, season, and team from the sidebar to begin.
        </p>
    </div>
    """, unsafe_allow_html=True)
