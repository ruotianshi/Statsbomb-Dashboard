"""
data_loader.py
--------------
封装所有 StatsBomb API 调用，使用 @st.cache_data 缓存数据
支持 open data（无需 creds）和 付费 API（需要 creds）

凭证配置方式：在 .streamlit/secrets.toml 中添加：
    [statsbomb]
    user   = "your_email@example.com"
    passwd = "your_password"

若未配置凭证，player_season_stats 等付费端点将自动回退到 Demo 数据。
"""

import streamlit as st
import pandas as pd
from statsbombpy import sb


# ─────────────────────────────────────────────
# 凭证管理
# ─────────────────────────────────────────────

def get_creds() -> dict | None:
    """
    从 Streamlit secrets 读取 StatsBomb 凭证
    若未配置则返回 None（open data 模式）
    """
    try:
        user   = st.secrets["statsbomb"]["user"]
        passwd = st.secrets["statsbomb"]["passwd"]
        # 防止用户填了占位符但没有替换
        if user == "your_email@example.com" or not user or not passwd:
            return None
        return {"user": user, "passwd": passwd}
    except Exception:
        return None


def has_credentials() -> bool:
    """检查是否已配置有效凭证"""
    return get_creds() is not None


def render_credentials_warning():
    """
    在页面顶部显示凭证缺失的警告框
    包含配置方法说明
    """
    st.warning(
        "**StatsBomb credentials not configured.** "
        "Player / Team aggregated season stats require a paid API account.\n\n"
        "**How to add credentials:**\n"
        "1. Open (or create) `.streamlit/secrets.toml` in the project root\n"
        "2. Add the following:\n"
        "```toml\n[statsbomb]\nuser   = \"your_email@example.com\"\npasswd = \"your_password\"\n```\n"
        "3. Restart the app\n\n"
        "👇 **Demo mode is active below** — showing synthetic data so you can explore the UI.",
        icon="🔑",
    )


# ─────────────────────────────────────────────
# 赛事 / 赛季
# ─────────────────────────────────────────────

@st.cache_data(ttl=86400, show_spinner=False)
def load_competitions() -> pd.DataFrame:
    """
    加载所有可用赛事列表
    返回 DataFrame: competition_id, competition_name, season_id, season_name
    """
    try:
        creds = get_creds()
        if creds:
            df = sb.competitions(creds=creds)
        else:
            df = sb.competitions()
        return df.sort_values(["competition_name", "season_name"])
    except Exception as e:
        st.error(f"Failed to load competitions: {e}")
        return pd.DataFrame()


def get_unique_competitions(comps_df: pd.DataFrame) -> dict:
    """从 competitions DataFrame 提取唯一赛事 {competition_name: competition_id}"""
    if comps_df.empty:
        return {}
    unique = comps_df[["competition_id", "competition_name"]].drop_duplicates()
    return dict(zip(unique["competition_name"], unique["competition_id"]))


def get_seasons_for_competition(comps_df: pd.DataFrame, competition_id: int) -> dict:
    """获取某赛事下的所有赛季 {season_name: season_id}"""
    if comps_df.empty:
        return {}
    filtered = comps_df[comps_df["competition_id"] == competition_id]
    filtered = filtered.sort_values("season_name", ascending=False)
    return dict(zip(filtered["season_name"], filtered["season_id"]))


# ─────────────────────────────────────────────
# 比赛列表
# ─────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def load_matches(competition_id: int, season_id: int) -> pd.DataFrame:
    """加载某赛事赛季下的所有比赛"""
    try:
        creds = get_creds()
        if creds:
            df = sb.matches(competition_id=competition_id, season_id=season_id, creds=creds)
        else:
            df = sb.matches(competition_id=competition_id, season_id=season_id)
        # 统一日期格式
        if "match_date" in df.columns:
            df["match_date"] = pd.to_datetime(df["match_date"])
        return df.sort_values("match_date")
    except Exception as e:
        st.error(f"Failed to load matches: {e}")
        return pd.DataFrame()


# ─────────────────────────────────────────────
# 球员赛季统计
# ─────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def load_player_season_stats(competition_id: int, season_id: int) -> pd.DataFrame:
    """加载球员赛季统计数据"""
    try:
        creds = get_creds()
        if creds:
            df = sb.player_season_stats(
                competition_id=competition_id,
                season_id=season_id,
                creds=creds,
            )
        else:
            df = sb.player_season_stats(
                competition_id=competition_id,
                season_id=season_id,
            )
        # 统一 birth_date 格式
        if "birth_date" in df.columns:
            df["birth_date"] = pd.to_datetime(df["birth_date"], errors="coerce")
        return df
    except Exception as e:
        st.error(f"Failed to load player season stats: {e}")
        return pd.DataFrame()


# ─────────────────────────────────────────────
# 球队赛季统计
# ─────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def load_team_season_stats(competition_id: int, season_id: int) -> pd.DataFrame:
    """加载球队赛季统计数据"""
    try:
        creds = get_creds()
        if creds:
            df = sb.team_season_stats(
                competition_id=competition_id,
                season_id=season_id,
                creds=creds,
            )
        else:
            df = sb.team_season_stats(
                competition_id=competition_id,
                season_id=season_id,
            )
        return df
    except Exception as e:
        st.error(f"Failed to load team season stats: {e}")
        return pd.DataFrame()


# ─────────────────────────────────────────────
# 比赛级别统计
# ─────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def load_team_match_stats(match_id: int) -> pd.DataFrame:
    """加载单场比赛的球队统计数据"""
    try:
        creds = get_creds()
        if creds:
            df = sb.team_match_stats(match_id=match_id, creds=creds)
        else:
            df = sb.team_match_stats(match_id=match_id)
        return df
    except Exception as e:
        st.error(f"Failed to load team match stats: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def load_player_match_stats(match_id: int) -> pd.DataFrame:
    """加载单场比赛的球员统计数据"""
    try:
        creds = get_creds()
        if creds:
            df = sb.player_match_stats(match_id=match_id, creds=creds)
        else:
            df = sb.player_match_stats(match_id=match_id)
        return df
    except Exception as e:
        st.error(f"Failed to load player match stats: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def load_lineups(match_id: int) -> dict:
    """加载单场比赛的双方阵容（返回 dict，key 为球队名）"""
    try:
        creds = get_creds()
        if creds:
            return sb.lineups(match_id=match_id, creds=creds)
        else:
            return sb.lineups(match_id=match_id)
    except Exception as e:
        st.error(f"Failed to load lineups: {e}")
        return {}


@st.cache_data(ttl=3600, show_spinner=False)
def load_events(match_id: int) -> pd.DataFrame:
    """加载单场比赛事件数据，用于换人等事件级可视化。"""
    try:
        creds = get_creds()
        if creds:
            df = sb.events(match_id=match_id, creds=creds)
        else:
            df = sb.events(match_id=match_id)
        return df if isinstance(df, pd.DataFrame) else pd.DataFrame()
    except Exception as e:
        st.error(f"Failed to load events: {e}")
        return pd.DataFrame()


# ─────────────────────────────────────────────
# 辅助：从 matches 计算球队赛季战绩
# ─────────────────────────────────────────────

def compute_team_record(matches_df: pd.DataFrame, team_id: int) -> dict:
    """
    从 matches DataFrame 计算指定球队的赛季战绩
    兼容三种数据结构：扁平列、dict 嵌套、字符串队名
    返回: {played, won, drawn, lost, gf, ga, gd, points}
    """
    if matches_df.empty:
        return {}

    # 检测列结构
    has_flat = "home_team_id" in matches_df.columns
    has_dict = (not has_flat and "home_team" in matches_df.columns and
                isinstance(matches_df["home_team"].dropna().iloc[0]
                           if not matches_df.empty else None, dict))
    is_str   = (not has_flat and not has_dict and "home_team" in matches_df.columns)

    # 字符串模式：反查队名
    target_name = None
    if is_str:
        all_names = set()
        for _, row in matches_df.iterrows():
            for side in ("home_team", "away_team"):
                v = row.get(side, "")
                if isinstance(v, str) and v:
                    all_names.add(v)
        id_to_name = {abs(hash(n)) % 1_000_000: n for n in all_names}
        target_name = id_to_name.get(team_id)
        if not target_name:
            return {}

    results = []
    for _, row in matches_df.iterrows():
        try:
            # 判断主客场
            if has_flat:
                h_id = int(row["home_team_id"]) if pd.notna(row.get("home_team_id")) else None
                a_id = int(row["away_team_id"]) if pd.notna(row.get("away_team_id")) else None
                is_home = (h_id == team_id)
                is_away = (a_id == team_id)
            elif has_dict:
                ht = row.get("home_team", {})
                at = row.get("away_team", {})
                h_id = int(ht.get("home_team_id")) if isinstance(ht, dict) and ht.get("home_team_id") else None
                a_id = int(at.get("away_team_id")) if isinstance(at, dict) and at.get("away_team_id") else None
                is_home = (h_id == team_id)
                is_away = (a_id == team_id)
            else:  # str
                is_home = (str(row.get("home_team", "")) == target_name)
                is_away = (str(row.get("away_team", "")) == target_name)

            h_score = row.get("home_score")
            a_score = row.get("away_score")
            if pd.isna(h_score) or pd.isna(a_score):
                continue

            if is_home:
                gf, ga = int(h_score), int(a_score)
            elif is_away:
                gf, ga = int(a_score), int(h_score)
            else:
                continue

            result = "W" if gf > ga else ("D" if gf == ga else "L")
            results.append({"result": result, "gf": gf, "ga": ga})
        except Exception:
            continue

    if not results:
        return {}

    combined = pd.DataFrame(results)
    won   = int((combined["result"] == "W").sum())
    drawn = int((combined["result"] == "D").sum())
    lost  = int((combined["result"] == "L").sum())
    gf    = int(combined["gf"].sum())
    ga    = int(combined["ga"].sum())

    return {
        "played": won + drawn + lost,
        "won":    won,
        "drawn":  drawn,
        "lost":   lost,
        "gf":     gf,
        "ga":     ga,
        "gd":     gf - ga,
        "points": won * 3 + drawn,
    }


def compute_points_timeline(matches_df: pd.DataFrame, team_id: int) -> pd.DataFrame:
    """
    计算球队赛季逐场积分走势
    返回 DataFrame: match_week, match_date, opponent, result, gf, ga,
                    points_gained, cumulative_points
    """
    if matches_df.empty:
        return pd.DataFrame()

    rows = []
    for _, row in matches_df.sort_values("match_date").iterrows():
        # 判断主客场
        h_id = row["home_team"].get("home_team_id") if isinstance(row["home_team"], dict) else None
        a_id = row["away_team"].get("away_team_id") if isinstance(row["away_team"], dict) else None

        if h_id == team_id:
            gf = row["home_score"]
            ga = row["away_score"]
            opp = row["away_team"].get("away_team_name", "") if isinstance(row["away_team"], dict) else ""
            venue = "H"
        elif a_id == team_id:
            gf = row["away_score"]
            ga = row["home_score"]
            opp = row["home_team"].get("home_team_name", "") if isinstance(row["home_team"], dict) else ""
            venue = "A"
        else:
            continue

        if gf > ga:
            result = "W"; pts = 3
        elif gf == ga:
            result = "D"; pts = 1
        else:
            result = "L"; pts = 0

        rows.append({
            "match_id":    row["match_id"],
            "match_week":  row.get("match_week", len(rows) + 1),
            "match_date":  row["match_date"],
            "opponent":    opp,
            "venue":       venue,
            "result":      result,
            "gf":          gf,
            "ga":          ga,
            "points_gained": pts,
        })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["cumulative_points"] = df["points_gained"].cumsum()
    df["match_number"] = range(1, len(df) + 1)
    return df
