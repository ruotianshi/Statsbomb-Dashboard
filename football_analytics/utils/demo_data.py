"""
demo_data.py
------------
在没有 StatsBomb 付费账户时，生成随机 Demo 数据供界面测试使用
数据结构与真实 API 返回完全一致
"""

import numpy as np
import pandas as pd


# ─────────────────────────────────────────────
# 固定种子，保证每次生成相同数据
# ─────────────────────────────────────────────
RNG = np.random.default_rng(42)

# Demo 赛事 / 赛季信息
DEMO_COMPETITIONS = pd.DataFrame([
    {"competition_id": 9999, "competition_name": "Demo League",
     "season_id": 1, "season_name": "2023/2024",
     "competition_gender": "male", "country_name": "Demo Country"},
])

# Demo 位置列表
_POSITIONS = [
    "Goalkeeper", "Center Back", "Right Back", "Left Back",
    "Defensive Midfield", "Center Midfield", "Attacking Midfield",
    "Right Wing", "Left Wing", "Center Forward",
]

# Demo 球队名单（10 支）
_TEAMS = [
    (1001, "Alpha FC"),   (1002, "Beta United"),  (1003, "Gamma City"),
    (1004, "Delta Town"), (1005, "Epsilon SC"),    (1006, "Zeta Athletic"),
    (1007, "Eta Rovers"), (1008, "Theta Rangers"), (1009, "Iota Wanderers"),
    (1010, "Kappa Villa"),
]

# Demo 球员名字库
_FIRST_NAMES = ["James", "Carlos", "Luca", "Marco", "David",
                "Tomás", "André", "Kenji", "Yusuf", "Olivier",
                "Sven", "Pablo", "Antoine", "Rafaël", "Hiroshi"]
_LAST_NAMES  = ["Silva", "Müller", "García", "Rossi", "Nakamura",
                "Dubois", "Santos", "Weber", "Mäkinen", "Okafor",
                "Johansson", "Petrov", "Hernandez", "Costa", "Kim"]


def _rand_name():
    f = RNG.choice(_FIRST_NAMES)
    l = RNG.choice(_LAST_NAMES)
    return f"{f} {l}", f, l


def _rand_val(lo, hi, decimals=3):
    return round(float(RNG.uniform(lo, hi)), decimals)


# ─────────────────────────────────────────────
# 生成 Demo 球员赛季数据
# ─────────────────────────────────────────────

def make_demo_player_season_stats(n_players: int = 120) -> pd.DataFrame:
    """生成 n_players 名球员的 Demo 赛季数据"""
    rows = []
    for i in range(n_players):
        team_id, team_name = _TEAMS[i % len(_TEAMS)]
        name, first, last = _rand_name()
        primary_pos   = _POSITIONS[i % len(_POSITIONS)]
        is_gk         = primary_pos == "Goalkeeper"
        is_defender   = "Back" in primary_pos or "Defensive" in primary_pos
        minutes       = int(RNG.integers(200, 3200))

        row = {
            "player_id":              10000 + i,
            "player_name":            name,
            "player_first_name":      first,
            "player_last_name":       last,
            "player_known_name":      name,
            "team_id":                team_id,
            "team_name":              team_name,
            "competition_id":         9999,
            "competition_name":       "Demo League",
            "season_id":              1,
            "season_name":            "2023/2024",
            "birth_date":             f"{int(RNG.integers(1990,2003))}-{int(RNG.integers(1,13)):02d}-{int(RNG.integers(1,28)):02d}",
            "player_height":          round(float(RNG.uniform(165, 200)), 1),
            "player_weight":          round(float(RNG.uniform(60, 95)), 1),
            "primary_position":       primary_pos,
            "secondary_position":     _POSITIONS[(i + 1) % len(_POSITIONS)] if RNG.random() > 0.5 else "",
            "player_season_minutes":  minutes,
            "player_season_appearances": int(minutes // 75),
            "player_season_average_minutes": round(float(minutes / max(1, minutes // 75)), 1),
            "player_season_90s_played": round(minutes / 90, 2),
            # 进攻
            "player_season_goals_90":            0.0 if is_gk else _rand_val(0, 0.9),
            "player_season_npg_90":              0.0 if is_gk else _rand_val(0, 0.7),
            "player_season_np_xg_90":            0.0 if is_gk else _rand_val(0, 0.7),
            "player_season_np_xg_per_shot":      0.0 if is_gk else _rand_val(0.05, 0.25),
            "player_season_np_shots_90":         0.0 if is_gk else _rand_val(0.5, 4.5),
            "player_season_shot_on_target_ratio": 0.0 if is_gk else _rand_val(0.2, 0.7),
            "player_season_conversion_ratio":    0.0 if is_gk else _rand_val(0.05, 0.35),
            "player_season_xa_90":               0.0 if is_gk else _rand_val(0, 0.5),
            "player_season_op_xa_90":            0.0 if is_gk else _rand_val(0, 0.4),
            "player_season_assists_90":          0.0 if is_gk else _rand_val(0, 0.4),
            "player_season_op_assists_90":       0.0 if is_gk else _rand_val(0, 0.3),
            "player_season_key_passes_90":       _rand_val(0, 2.5),
            "player_season_op_key_passes_90":    _rand_val(0, 2.0),
            "player_season_touches_inside_box_90": 0.0 if is_gk or is_defender else _rand_val(0, 4.0),
            "player_season_passes_into_box_90":  _rand_val(0, 3.0),
            "player_season_op_passes_into_box_90": _rand_val(0, 2.5),
            "player_season_through_balls_90":    _rand_val(0, 0.8),
            "player_season_deep_progressions_90": _rand_val(0, 3.0),
            "player_season_deep_completions_90": _rand_val(0, 3.0),
            "player_season_npxgxa_90":           0.0 if is_gk else _rand_val(0, 1.2),
            "player_season_shots_key_passes_90": _rand_val(0, 5.0),
            "player_season_sp_xa_90":            _rand_val(0, 0.2),
            "player_season_penalty_wins_90":     _rand_val(0, 0.15),
            "player_season_crosses_90":          _rand_val(0, 3.0),
            "player_season_crossing_ratio":      _rand_val(0.1, 0.5),
            # 防守
            "player_season_tackles_90":          _rand_val(0.2, 5.0),
            "player_season_interceptions_90":    _rand_val(0.1, 3.5),
            "player_season_tackles_and_interceptions_90": _rand_val(0.5, 7.0),
            "player_season_padj_tackles_90":     _rand_val(0.3, 5.5),
            "player_season_padj_interceptions_90": _rand_val(0.2, 4.0),
            "player_season_padj_tackles_and_interceptions_90": _rand_val(0.5, 8.0),
            "player_season_challenge_ratio":     _rand_val(0.3, 0.9),
            "player_season_clearance_90":        1.5 if not is_defender else _rand_val(2.0, 9.0),
            "player_season_padj_clearances_90":  _rand_val(0.5, 7.0),
            "player_season_aerial_wins_90":      _rand_val(0.1, 4.0),
            "player_season_aerial_ratio":        _rand_val(0.3, 0.8),
            "player_season_blocks_per_shot":     _rand_val(0.0, 0.4),
            "player_season_dribbled_past_90":    _rand_val(0.1, 3.0),
            "player_season_fouls_90":            _rand_val(0.2, 3.5),
            "player_season_fouls_won_90":        _rand_val(0.2, 3.0),
            "player_season_defensive_action_regains_90": _rand_val(0.5, 6.0),
            "player_season_defensive_actions_90": _rand_val(1.0, 10.0),
            # 传球
            "player_season_op_passes_90":        _rand_val(10, 60),
            "player_season_passing_ratio":       _rand_val(0.6, 0.95),
            "player_season_forward_pass_proportion": _rand_val(0.25, 0.55),
            "player_season_backward_pass_proportion": _rand_val(0.1, 0.35),
            "player_season_sideways_pass_proportion": _rand_val(0.1, 0.4),
            "player_season_op_f3_passes_90":     _rand_val(1, 15),
            "player_season_op_f3_forward_pass_proportion": _rand_val(0.3, 0.7),
            "player_season_long_ball_ratio":     _rand_val(0.05, 0.35),
            "player_season_long_balls_90":       _rand_val(1, 12),
            "player_season_pass_length":         _rand_val(10, 35),
            "player_season_pressured_passing_ratio": _rand_val(0.5, 0.9),
            "player_season_passes_pressed_ratio": _rand_val(0.1, 0.5),
            # 逼抢
            "player_season_pressures_90":        _rand_val(3, 20),
            "player_season_padj_pressures_90":   _rand_val(3, 20),
            "player_season_pressure_regains_90": _rand_val(0.5, 5.0),
            "player_season_counterpressures_90": _rand_val(1, 8),
            "player_season_counterpressure_regains_90": _rand_val(0.2, 3.0),
            "player_season_aggressive_actions_90": _rand_val(2, 15),
            "player_season_fhalf_pressures_90":  _rand_val(1, 10),
            "player_season_fhalf_pressures_ratio": _rand_val(0.1, 0.6),
            "player_season_fhalf_counterpressures_90": _rand_val(0.5, 5),
            # 持球/过人
            "player_season_dribbles_90":         _rand_val(0.1, 4.0),
            "player_season_total_dribbles_90":   _rand_val(0.5, 6.0),
            "player_season_dribble_ratio":       _rand_val(0.3, 0.85),
            "player_season_failed_dribbles_90":  _rand_val(0.1, 2.5),
            "player_season_dispossessions_90":   _rand_val(0.2, 4.0),
            "player_season_turnovers_90":        _rand_val(0.5, 5.0),
            "player_season_carries_90":          _rand_val(5, 35),
            "player_season_carry_ratio":         _rand_val(0.3, 0.9),
            "player_season_carry_length":        _rand_val(3, 15),
            "player_season_ball_recoveries_90":  _rand_val(1, 10),
            # OBV
            "player_season_obv_90":                    _rand_val(-0.05, 0.15),
            "player_season_obv_pass_90":               _rand_val(-0.03, 0.12),
            "player_season_obv_shot_90":               _rand_val(-0.02, 0.08),
            "player_season_obv_defensive_action_90":   _rand_val(-0.02, 0.06),
            "player_season_obv_dribble_carry_90":      _rand_val(-0.02, 0.06),
            "player_season_obv_gk_90":                 _rand_val(-0.05, 0.1) if is_gk else 0.0,
            # xG 链条
            "player_season_xgchain_90":          _rand_val(0.05, 0.8),
            "player_season_op_xgchain_90":       _rand_val(0.05, 0.7),
            "player_season_xgbuildup_90":        _rand_val(0.02, 0.4),
            "player_season_op_xgbuildup_90":     _rand_val(0.02, 0.35),
            # 门将
            "player_season_save_ratio":          _rand_val(0.55, 0.85) if is_gk else None,
            "player_season_gsaa_90":             _rand_val(-0.3, 0.4)  if is_gk else None,
            "player_season_gsaa_ratio":          _rand_val(-0.1, 0.15) if is_gk else None,
            "player_season_xs_ratio":            _rand_val(0.65, 0.85) if is_gk else None,
            "player_season_shots_faced_90":      _rand_val(2, 7)       if is_gk else None,
            "player_season_np_xg_faced_90":      _rand_val(0.5, 2.5)   if is_gk else None,
            "player_season_np_psxg_faced_90":    _rand_val(0.4, 2.2)   if is_gk else None,
            "player_season_clcaa":               _rand_val(-5, 10)     if is_gk else None,
            # 综合
            "player_season_positive_outcome_90": _rand_val(0.3, 1.2),
            "player_season_over_under_performance_90": _rand_val(-0.2, 0.2),
        }
        rows.append(row)

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────
# 生成 Demo 比赛列表
# ─────────────────────────────────────────────

def make_demo_matches(n_matches_per_team: int = 10) -> pd.DataFrame:
    """生成 Demo 比赛列表（每队约 10 场）"""
    rows = []
    match_id = 5000
    dates = pd.date_range("2023-08-12", periods=38, freq="7D")

    for week, date in enumerate(dates[:20], 1):
        # 简单的循环赛对阵
        for i in range(0, len(_TEAMS) - 1, 2):
            h_id, h_name = _TEAMS[i]
            a_id, a_name = _TEAMS[i + 1]
            h_score = int(RNG.integers(0, 4))
            a_score = int(RNG.integers(0, 4))
            rows.append({
                "match_id":    match_id,
                "match_date":  date,
                "match_week":  week,
                "competition": {"competition_id": 9999, "competition_name": "Demo League"},
                "season":      {"season_id": 1, "season_name": "2023/2024"},
                "home_team":   {"home_team_id": h_id, "home_team_name": h_name},
                "away_team":   {"away_team_id": a_id, "away_team_name": a_name},
                "home_score":  h_score,
                "away_score":  a_score,
                "attendance":  int(RNG.integers(15000, 60000)),
                "stadium":     {"name": f"{h_name} Stadium"},
                "referee":     {"name": "Demo Referee"},
                "home_managers": [{"name": f"Manager {h_id}"}],
                "away_managers": [{"name": f"Manager {a_id}"}],
                "competition_stage": {"name": f"Matchweek {week}"},
            })
            match_id += 1

    return pd.DataFrame(rows)
