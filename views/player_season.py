"""
player_season.py
----------------
Player Season Dashboard 视图
包含：
  1. 球员 Profile Card（照片、队徽、基础信息）
  2. 属性雷达图（可选标准化、自定义指标、双人对比）
  3. OBV 构成条形图
  4. 联赛排名柱状图（可过滤位置、指标、数量）
"""

import numpy as np
import streamlit as st

from components.bar_ranking import build_bar_ranking, build_obv_breakdown
from components.radar_chart import build_radar_chart
from utils.data_loader import load_competitions, load_player_season_stats
from utils.image_helper import (
    compute_age,
    format_birth_date,
    get_player_display_name,
    load_player_image,
    load_team_image,
)
from utils.metrics_config import (
    BAR_METRIC_GROUPS,
    COLORS,
    METRIC_LABELS,
    POSITION_GROUPS,
    RADAR_PRESET_GROUPS,
)


# ─────────────────────────────────────────────
# 主入口
# ─────────────────────────────────────────────

def render():
    # ── Sidebar 筛选 ─────────────────────────────
    _render_sidebar_filters()

    comp_id   = st.session_state.get("ps_competition_id")
    season_id = st.session_state.get("ps_season_id")
    player_id = st.session_state.get("ps_player_id")

    if not comp_id or not season_id:
        _render_welcome()
        return

    # 加载数据
    with st.spinner("Loading player data..."):
        df = load_player_season_stats(comp_id, season_id)

    if df.empty:
        st.warning("No player data available for this competition / season.")
        return

    if player_id is None:
        _render_welcome()
        return

    # 获取当前球员行
    player_rows = df[df["player_id"] == player_id]
    if player_rows.empty:
        st.warning("Player not found in dataset.")
        return
    player_row = player_rows.iloc[0]

    # ── 主内容区 ─────────────────────────────────
    _render_profile_card(player_row)

    st.markdown('<hr style="border:1px solid #2a2d3e; margin:16px 0">', unsafe_allow_html=True)

    # Row 2: Radar + OBV
    col_radar, col_obv = st.columns([4, 6], gap="medium")
    with col_radar:
        _render_radar_section(player_row, df)
    with col_obv:
        _render_obv_section(player_row, df)

    st.markdown('<hr style="border:1px solid #2a2d3e; margin:16px 0">', unsafe_allow_html=True)

    # Row 3: 联赛排名
    _render_bar_ranking_section(player_row, df)


# ─────────────────────────────────────────────
# Sidebar 筛选面板
# ─────────────────────────────────────────────

def _render_sidebar_filters():
    with st.sidebar:
        st.markdown("### 🔍 Data Filters")

        # 加载赛事列表
        comps_df = load_competitions()
        if comps_df.empty:
            st.error("No competitions available.")
            return

        # Competition 选择
        comp_names = sorted(comps_df["competition_name"].unique().tolist())
        default_comp = st.session_state.get("ps_competition_name", comp_names[0])
        if default_comp not in comp_names:
            default_comp = comp_names[0]

        comp_name = st.selectbox(
            "Competition",
            comp_names,
            index=comp_names.index(default_comp),
            key="ps_comp_select",
        )
        comp_id = int(comps_df[comps_df["competition_name"] == comp_name]["competition_id"].iloc[0])

        # Season 选择
        season_options = comps_df[comps_df["competition_name"] == comp_name][
            ["season_id", "season_name"]
        ].drop_duplicates().sort_values("season_name", ascending=False)

        season_names = season_options["season_name"].tolist()
        default_season = st.session_state.get("ps_season_name", season_names[0])
        if default_season not in season_names:
            default_season = season_names[0]

        season_name = st.selectbox(
            "Season",
            season_names,
            index=season_names.index(default_season),
            key="ps_season_select",
        )
        season_id = int(season_options[season_options["season_name"] == season_name]["season_id"].iloc[0])

        st.divider()
        st.markdown("### 👤 Player Selection")

        # 最低上场分钟数
        min_minutes = st.slider(
            "Min. Minutes Played",
            min_value=0, max_value=3000,
            value=st.session_state.get("ps_min_minutes", 500),
            step=50,
            key="ps_min_minutes_slider",
        )

        # 加载球员数据以填充选择框
        df = load_player_season_stats(comp_id, season_id)
        if not df.empty:
            filtered = df[df["player_season_minutes"] >= min_minutes].copy()

            # ── Team Filter ──────────────────────────────
            if "team_name" in filtered.columns:
                team_list     = sorted(filtered["team_name"].dropna().unique().tolist())
                team_list_all = ["All Teams"] + team_list

                prev_team = st.session_state.get("ps_team_name", "All Teams")
                if prev_team not in team_list_all:
                    prev_team = "All Teams"

                selected_team = st.selectbox(
                    "Team",
                    team_list_all,
                    index=team_list_all.index(prev_team),
                    key="ps_team_select",
                )
                if selected_team != "All Teams":
                    filtered = filtered[filtered["team_name"] == selected_team]
            else:
                selected_team = "All Teams"

            # 生成显示名称，过滤掉名字异常的行（Unknown / 空）
            filtered["_display"] = filtered.apply(get_player_display_name, axis=1)
            filtered = filtered[
                filtered["_display"].notna() &
                (filtered["_display"] != "Unknown") &
                (filtered["_display"].str.strip() != "")
            ]
            filtered = filtered.sort_values("_display")

            if filtered.empty:
                st.warning("No players match the current filters.")
                selected_player_id = None
            else:
                # 显示当前筛选结果数量
                st.caption(f"{len(filtered)} players found")

                player_options = dict(zip(filtered["_display"], filtered["player_id"]))
                player_display_names = list(player_options.keys())

                # 保持上次选择的球员
                prev_id = st.session_state.get("ps_player_id")
                prev_name = None
                if prev_id is not None:
                    prev_rows = filtered[filtered["player_id"] == prev_id]
                    if not prev_rows.empty:
                        prev_name = prev_rows["_display"].iloc[0]

                default_idx = 0
                if prev_name and prev_name in player_display_names:
                    default_idx = player_display_names.index(prev_name)

                selected_name = st.selectbox(
                    "Select Player",
                    player_display_names,
                    index=default_idx,
                    key="ps_player_select",
                )
                selected_player_id = player_options[selected_name]
        else:
            selected_player_id = None

        # 写入 session_state
        st.session_state["ps_competition_id"]   = comp_id
        st.session_state["ps_season_id"]        = season_id
        st.session_state["ps_competition_name"] = comp_name
        st.session_state["ps_season_name"]      = season_name
        st.session_state["ps_player_id"]        = selected_player_id
        st.session_state["ps_min_minutes"]       = min_minutes
        st.session_state["ps_team_name"]         = st.session_state.get("ps_team_select", "All Teams")


# ─────────────────────────────────────────────
# Profile Card
# ─────────────────────────────────────────────

def _render_profile_card(row):
    col_photo, col_info, col_stats, col_badge = st.columns([1, 3, 3, 1], gap="medium")

    # ── 球员照片 ─────────────────────────────────
    with col_photo:
        player_img = load_player_image(row["player_id"], size=(110, 110))
        st.image(player_img, use_container_width=False, width=110)

    # ── 基础信息 ─────────────────────────────────
    with col_info:
        display_name = get_player_display_name(row)
        age          = compute_age(row.get("birth_date"))
        dob          = format_birth_date(row.get("birth_date"))
        age_str      = f" ({age} yrs)" if age else ""
        height       = row.get("player_height", "N/A")
        weight       = row.get("player_weight", "N/A")
        primary_pos  = row.get("primary_position", "N/A")
        secondary_pos = row.get("secondary_position", "")
        pos_str      = primary_pos
        if secondary_pos and isinstance(secondary_pos, str) and secondary_pos.strip():
            pos_str += f" / {secondary_pos}"

        st.markdown(f"""
        <div style="padding: 4px 0">
            <h2 style="margin:0; color:{COLORS['text']}; font-size:1.5rem">{display_name}</h2>
            <p style="margin:2px 0; color:{COLORS['muted']}; font-size:0.9rem">
                🏟️ {row.get('team_name', 'N/A')} &nbsp;·&nbsp; {row.get('competition_name', 'N/A')}
            </p>
            <p style="margin:6px 0; font-size:0.85rem">
                🎂 <b>DOB:</b> {dob}{age_str}<br>
                📍 <b>Position:</b> {pos_str}<br>
                📏 <b>Height:</b> {height} cm &nbsp;·&nbsp; ⚖️ <b>Weight:</b> {weight} kg
            </p>
        </div>
        """, unsafe_allow_html=True)

    # ── 赛季统计 ─────────────────────────────────
    with col_stats:
        minutes     = int(row.get("player_season_minutes", 0) or 0)
        appearances = int(row.get("player_season_appearances", 0) or 0)
        avg_min     = round(float(row.get("player_season_average_minutes", 0) or 0), 0)
        nineties    = round(float(row.get("player_season_90s_played", 0) or 0), 1)

        # 用 st.metric 展示关键赛季数值
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Minutes",     f"{minutes:,}")
        m2.metric("Apps",        appearances)
        m3.metric("Avg Min",     f"{avg_min:.0f}")
        m4.metric("90s",         nineties)

    # ── 球队队徽 ─────────────────────────────────
    with col_badge:
        team_img = load_team_image(row["team_id"], size=(80, 80))
        st.image(team_img, use_container_width=False, width=80)


# ─────────────────────────────────────────────
# 雷达图区域
# ─────────────────────────────────────────────

def _render_radar_section(player_row, df):
    st.markdown(f"#### 🕸️ Attribute Radar")

    min_min = st.session_state.get("ps_min_minutes", 500)

    # 指标组预设选择
    preset_options = ["Custom"] + list(RADAR_PRESET_GROUPS.keys())
    preset = st.selectbox(
        "Metric Preset",
        preset_options,
        key="radar_preset",
        help="Choose a preset group or select custom metrics below",
    )

    # 确定可选指标（仅使用 df 中实际存在的列）
    available = [c for c in METRIC_LABELS if c in df.columns]
    available_labels = {METRIC_LABELS[c]: c for c in available}

    if preset != "Custom":
        default_metrics = [m for m in RADAR_PRESET_GROUPS[preset] if m in df.columns]
    else:
        default_metrics = st.session_state.get("radar_custom_metrics", available[:6])

    selected_labels = st.multiselect(
        "Select Metrics (max 10)",
        options=list(available_labels.keys()),
        default=[METRIC_LABELS.get(m, m) for m in default_metrics if METRIC_LABELS.get(m, m) in available_labels],
        max_selections=10,
        key="radar_metrics_select",
    )
    selected_metrics = [available_labels[lbl] for lbl in selected_labels if lbl in available_labels]

    # 标准化开关
    col_norm, col_cmp_toggle = st.columns(2)
    with col_norm:
        normalize = st.toggle("Percentile Rank", value=True, key="radar_normalize",
                              help="ON: percentile vs league pool  OFF: min-max 0-100")
    with col_cmp_toggle:
        show_compare = st.toggle("Compare Player", value=False, key="radar_compare_toggle")

    # 对比球员选择
    compare_row  = None
    compare_name = ""
    if show_compare:
        pool = df[df["player_season_minutes"] >= min_min].copy()
        pool["_display"] = pool.apply(get_player_display_name, axis=1)
        # 过滤掉当前球员和名字异常行
        pool = pool[
            (pool["player_id"] != player_row["player_id"]) &
            (pool["_display"] != "Unknown") &
            (pool["_display"].str.strip() != "")
        ]

        # ── 对比球员球队筛选 ──────────────────────────
        cmp_col1, cmp_col2 = st.columns(2)
        with cmp_col1:
            if "team_name" in pool.columns:
                cmp_team_list = ["All Teams"] + sorted(pool["team_name"].dropna().unique().tolist())
                cmp_team = st.selectbox(
                    "Filter by Team",
                    cmp_team_list,
                    key="radar_compare_team",
                )
                if cmp_team != "All Teams":
                    pool = pool[pool["team_name"] == cmp_team]

        pool = pool.sort_values("_display")
        cmp_options = dict(zip(pool["_display"], pool["player_id"]))

        with cmp_col2:
            if cmp_options:
                cmp_name_sel = st.selectbox(
                    "Select Compare Player",
                    list(cmp_options.keys()),
                    key="radar_compare_player",
                )
            else:
                st.info("No players found.")
                cmp_name_sel = None

        if cmp_name_sel:
            cmp_id = cmp_options[cmp_name_sel]
            cmp_rows = df[df["player_id"] == cmp_id]
            if not cmp_rows.empty:
                compare_row  = cmp_rows.iloc[0]
                compare_name = cmp_name_sel

    # 生成雷达图
    if selected_metrics:
        fig = build_radar_chart(
            player_row,
            df,
            selected_metrics,
            normalize=normalize,
            min_minutes=min_min,
            compare_row=compare_row,
            compare_name=compare_name,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Select at least one metric to display the radar chart.")


# ─────────────────────────────────────────────
# OBV 构成图区域
# ─────────────────────────────────────────────

def _render_obv_section(player_row, df):
    st.markdown(f"#### 📈 OBV Breakdown (p90)")

    min_min = st.session_state.get("ps_min_minutes", 500)
    fig = build_obv_breakdown(player_row, df, min_minutes=min_min)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)

    # ── 额外指标卡片（Key Stats 快览）───────────────
    st.markdown(f"#### 📊 Key Stats Overview")

    # 选择最具代表性的 8 个指标展示为卡片
    key_stats = [
        ("player_season_np_xg_90",          "NP xG p90"),
        ("player_season_xa_90",             "xA p90"),
        ("player_season_padj_tackles_90",   "PAdj Tackles"),
        ("player_season_padj_interceptions_90", "PAdj Int"),
        ("player_season_pressures_90",      "Pressures p90"),
        ("player_season_passing_ratio",     "Pass Comp %"),
        ("player_season_dribble_ratio",     "Dribble %"),
        ("player_season_obv_90",            "OBV p90"),
    ]

    # 计算联赛均值（用于 delta）
    valid_stats = [(col, lbl) for col, lbl in key_stats if col in df.columns]
    cols = st.columns(len(valid_stats))
    min_min = st.session_state.get("ps_min_minutes", 500)
    pool = df[df["player_season_minutes"] >= min_min]

    for i, (col, lbl) in enumerate(valid_stats):
        val  = player_row.get(col, np.nan)
        avg  = pool[col].mean() if col in pool.columns else np.nan
        if isinstance(val, float) and not np.isnan(val):
            delta = round(float(val) - float(avg), 3) if not np.isnan(avg) else None
            is_pct = "ratio" in col or "proportion" in col
            fmt = f"{val*100:.1f}%" if is_pct else f"{val:.3f}"
            delta_fmt = f"{delta*100:+.1f}%" if (is_pct and delta is not None) else (f"{delta:+.3f}" if delta is not None else None)
            cols[i].metric(lbl, fmt, delta=delta_fmt)
        else:
            cols[i].metric(lbl, "N/A")


# ─────────────────────────────────────────────
# 联赛排名柱状图区域
# ─────────────────────────────────────────────

def _render_bar_ranking_section(player_row, df):
    st.markdown("#### 🏆 League Ranking")

    # ── Row 1：指标选择 ───────────────────────────
    ctrl1, ctrl2, ctrl3, ctrl4 = st.columns([3, 3, 2, 1], gap="small")

    with ctrl1:
        group_options = list(BAR_METRIC_GROUPS.keys())
        selected_group = st.selectbox("Metric Group", group_options, key="bar_metric_group")
        group_metrics = [m for m in BAR_METRIC_GROUPS[selected_group] if m in df.columns]
        metric_label_map = {METRIC_LABELS.get(m, m): m for m in group_metrics}
        selected_metric_label = st.selectbox(
            "Metric", list(metric_label_map.keys()), key="bar_metric_select",
        )
        selected_metric = metric_label_map[selected_metric_label]

    with ctrl2:
        min_min_bar = st.number_input(
            "Min Minutes",
            min_value=0, max_value=3000,
            value=st.session_state.get("ps_min_minutes", 500),
            step=50, key="bar_min_minutes",
        )

    with ctrl3:
        top_n = st.slider(
            "Show N Players", min_value=5, max_value=50, value=25, step=5, key="bar_top_n",
        )

    with ctrl4:
        ascending = st.toggle(
            "↑ Asc", value=False, key="bar_ascending",
            help="Controls display order only. Rankings always show top N by highest value.",
        )

    # ── Row 2：Position Filter（multiselect，从实际数据提取）──
    if "primary_position" in df.columns:
        all_positions = sorted(df["primary_position"].dropna().unique().tolist())
        selected_positions = st.multiselect(
            "Position Filter  *(applied after ranking — target player always shown)*",
            options=all_positions,
            default=[],
            key="bar_position_filter_multi",
            help="Leave empty to show all positions. Target player is always included regardless.",
        )
        position_filter = selected_positions if selected_positions else None
    else:
        position_filter = None

    # ── 生成图表 ──────────────────────────────────
    fig = build_bar_ranking(
        all_df=df,
        metric=selected_metric,
        highlight_player_id=player_row["player_id"],
        position_filter=position_filter,
        min_minutes=int(min_min_bar),
        top_n=int(top_n),
        ascending=ascending,
    )
    st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────
# 欢迎页
# ─────────────────────────────────────────────

def _render_welcome():
    st.markdown("""
    <div style="text-align:center; padding: 60px 20px; color: #8b9bb4">
        <h2 style="font-size:2rem">⚽ Player Season Dashboard</h2>
        <p style="font-size:1rem">
            Select a competition, season, and player from the sidebar to begin.
        </p>
    </div>
    """, unsafe_allow_html=True)
