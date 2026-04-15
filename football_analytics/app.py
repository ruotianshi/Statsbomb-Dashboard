"""
app.py
------
Football Analytics Dashboard - 主入口
负责页面配置、侧边栏模块导航、页面路由
"""

import streamlit as st

# ─────────────────────────────────────────────
# 页面基础配置（必须是第一个 Streamlit 调用）
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Football Analytics",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# 全局 CSS 注入（增强暗色主题细节）
# ─────────────────────────────────────────────

st.markdown("""
<style>
    /* 隐藏 Streamlit 默认页脚和汉堡菜单 */
    #MainMenu { visibility: hidden; }
    footer    { visibility: hidden; }

    /* 侧边栏样式 */
    [data-testid="stSidebar"] {
        background-color: #1a1d2e;
        border-right: 1px solid #2a2d3e;
    }
    [data-testid="stSidebar"] .stRadio label {
        font-size: 0.9rem;
    }

    /* Metric 卡片 */
    [data-testid="stMetric"] {
        background-color: #1a1d2e;
        border: 1px solid #2a2d3e;
        border-radius: 8px;
        padding: 10px 14px;
    }
    [data-testid="stMetricLabel"]  { font-size: 0.75rem !important; color: #8b9bb4 !important; }
    [data-testid="stMetricValue"]  { font-size: 1.1rem  !important; color: #ffffff  !important; }
    [data-testid="stMetricDelta"]  { font-size: 0.75rem !important; }

    /* Tab 样式 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background-color: #1a1d2e;
        border-radius: 8px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px;
        padding: 6px 16px;
        font-size: 0.85rem;
    }
    .stTabs [aria-selected="true"] {
        background-color: #00d4aa !important;
        color: #0e1117 !important;
        font-weight: 600;
    }

    /* 按钮 */
    .stButton > button {
        border: 1px solid #00d4aa;
        color: #00d4aa;
        background: transparent;
        border-radius: 6px;
    }
    .stButton > button:hover {
        background: #00d4aa;
        color: #0e1117;
    }

    /* 分割线 */
    hr { border-color: #2a2d3e; }

    /* Plotly 图表容器 */
    [data-testid="stPlotlyChart"] {
        border-radius: 8px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Session State 初始化
# ─────────────────────────────────────────────

_defaults = {
    "active_module":       "Player Season",
    "ps_competition_id":   None,
    "ps_season_id":        None,
    "ps_player_id":        None,
    "ps_min_minutes":      500,
    "ts_competition_id":   None,
    "ts_season_id":        None,
    "ts_team_id":          None,
    "md_match_id":         None,
    "pms_match_id":        None,
    "pms_player_id":       None,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────
# 侧边栏：模块导航
# ─────────────────────────────────────────────

MODULE_ICONS = {
    "Player Season":      "👤",
    "Team Season":        "🏟️",
    "Match Dashboard":    "⚽",
    "Player Match Stats": "📊",
}

with st.sidebar:
    st.markdown("""
    <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px">
        <span style="font-size:1.8rem">⚽</span>
        <span style="font-size:1.1rem; font-weight:700; color:#ffffff">Football Analytics</span>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<hr style="border:1px solid #2a2d3e; margin:8px 0 16px 0">', unsafe_allow_html=True)

    module_labels = [f"{icon}  {name}" for name, icon in MODULE_ICONS.items()]
    module_names  = list(MODULE_ICONS.keys())

    # 保持上次选中模块
    current_idx = module_names.index(st.session_state["active_module"]) \
        if st.session_state["active_module"] in module_names else 0

    selected_label = st.radio(
        "Navigation",
        module_labels,
        index=current_idx,
        key="nav_radio",
        label_visibility="collapsed",
    )
    active_module = module_names[module_labels.index(selected_label)]
    st.session_state["active_module"] = active_module

    st.markdown('<hr style="border:1px solid #2a2d3e; margin:16px 0 8px 0">', unsafe_allow_html=True)

    # 各模块动态 sidebar 内容由对应 view 的 render() 自行追加


# ─────────────────────────────────────────────
# 跨模块跳转辅助（供其他模块调用）
# ─────────────────────────────────────────────

def navigate_to(module: str, **kwargs):
    """
    跳转到指定模块并设置 session_state 参数
    例: navigate_to("Match Dashboard", md_match_id=12345)
    """
    st.session_state["active_module"] = module
    for k, v in kwargs.items():
        st.session_state[k] = v
    st.rerun()


# ─────────────────────────────────────────────
# 路由：加载对应模块视图
# ─────────────────────────────────────────────

if active_module == "Player Season":
    from views.player_season import render
    render()

elif active_module == "Team Season":
    try:
        from views.team_season import render
        render()
    except ImportError:
        st.info("🚧 Team Season Dashboard — coming soon.")

elif active_module == "Match Dashboard":
    try:
        from views.match_dashboard import render
        render()
    except ImportError:
        st.info("🚧 Match Dashboard — coming soon.")

elif active_module == "Player Match Stats":
    try:
        from views.player_match import render
        render()
    except ImportError:
        st.info("🚧 Player Match Stats — coming soon.")
