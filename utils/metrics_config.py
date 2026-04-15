"""
metrics_config.py
-----------------
所有指标的显示名称映射、雷达图分组、柱状图分组和颜色配置
"""

# ─────────────────────────────────────────────
# 指标显示名称映射（变量名 → 可读标签）
# ─────────────────────────────────────────────
METRIC_LABELS = {
    # 进攻
    "player_season_goals_90":                          "Goals p90",
    "player_season_npg_90":                            "NP Goals p90",
    "player_season_np_xg_90":                          "NP xG p90",
    "player_season_np_xg_per_shot":                    "NP xG per Shot",
    "player_season_np_shots_90":                       "NP Shots p90",
    "player_season_shot_on_target_ratio":              "Shot on Target %",
    "player_season_conversion_ratio":                  "Conversion Rate",
    "player_season_xa_90":                             "xA p90",
    "player_season_op_xa_90":                          "OP xA p90",
    "player_season_assists_90":                        "Assists p90",
    "player_season_op_assists_90":                     "OP Assists p90",
    "player_season_key_passes_90":                     "Key Passes p90",
    "player_season_op_key_passes_90":                  "OP Key Passes p90",
    "player_season_touches_inside_box_90":             "Touches in Box p90",
    "player_season_passes_into_box_90":                "Passes into Box p90",
    "player_season_op_passes_into_box_90":             "OP Passes into Box p90",
    "player_season_deep_progressions_90":              "Deep Progressions p90",
    "player_season_deep_completions_90":               "Deep Completions p90",
    "player_season_through_balls_90":                  "Through Balls p90",
    "player_season_npxgxa_90":                         "NP xG+xA p90",
    "player_season_sp_xa_90":                          "SP xA p90",
    "player_season_shots_key_passes_90":               "Shots + Key Passes p90",
    "player_season_penalty_wins_90":                   "Penalty Wins p90",
    # 防守
    "player_season_tackles_90":                        "Tackles p90",
    "player_season_interceptions_90":                  "Interceptions p90",
    "player_season_tackles_and_interceptions_90":      "Tackles + Int p90",
    "player_season_padj_tackles_90":                   "PAdj Tackles p90",
    "player_season_padj_interceptions_90":             "PAdj Interceptions p90",
    "player_season_padj_tackles_and_interceptions_90": "PAdj T+I p90",
    "player_season_challenge_ratio":                   "Tackle Success %",
    "player_season_clearance_90":                      "Clearances p90",
    "player_season_padj_clearances_90":                "PAdj Clearances p90",
    "player_season_aerial_wins_90":                    "Aerial Wins p90",
    "player_season_aerial_ratio":                      "Aerial Win %",
    "player_season_blocks_per_shot":                   "Blocks per Shot",
    "player_season_dribbled_past_90":                  "Dribbled Past p90",
    "player_season_fouls_90":                          "Fouls p90",
    "player_season_fouls_won_90":                      "Fouls Won p90",
    "player_season_defensive_action_regains_90":       "Def Action Regains p90",
    "player_season_defensive_actions_90":              "Defensive Actions p90",
    # 传球
    "player_season_op_passes_90":                      "OP Passes p90",
    "player_season_passing_ratio":                     "Pass Completion %",
    "player_season_forward_pass_proportion":           "Forward Pass %",
    "player_season_backward_pass_proportion":          "Backward Pass %",
    "player_season_sideways_pass_proportion":          "Sideways Pass %",
    "player_season_op_f3_passes_90":                   "OP Final 3rd Passes p90",
    "player_season_op_f3_forward_pass_proportion":     "OP F3 Forward Pass %",
    "player_season_long_ball_ratio":                   "Long Ball %",
    "player_season_long_balls_90":                     "Long Balls p90",
    "player_season_crosses_90":                        "Crosses p90",
    "player_season_crossing_ratio":                    "Cross Completion %",
    "player_season_pass_length":                       "Avg Pass Length",
    "player_season_pressured_passing_ratio":           "Pressured Pass Completion %",
    "player_season_passes_pressed_ratio":              "Passes Under Pressure %",
    # 逼抢
    "player_season_pressures_90":                      "Pressures p90",
    "player_season_padj_pressures_90":                 "PAdj Pressures p90",
    "player_season_pressure_regains_90":               "Pressure Regains p90",
    "player_season_counterpressures_90":               "Counterpressures p90",
    "player_season_counterpressure_regains_90":        "Counterpressure Regains p90",
    "player_season_aggressive_actions_90":             "Aggressive Actions p90",
    "player_season_fhalf_pressures_90":                "F-Half Pressures p90",
    "player_season_fhalf_pressures_ratio":             "F-Half Pressure %",
    "player_season_fhalf_counterpressures_90":         "F-Half Counterpressures p90",
    # 持球 / 过人
    "player_season_dribbles_90":                       "Successful Dribbles p90",
    "player_season_total_dribbles_90":                 "Total Dribbles p90",
    "player_season_dribble_ratio":                     "Dribble Success %",
    "player_season_failed_dribbles_90":                "Failed Dribbles p90",
    "player_season_dispossessions_90":                 "Dispossessions p90",
    "player_season_turnovers_90":                      "Turnovers p90",
    "player_season_carries_90":                        "Carries p90",
    "player_season_carry_ratio":                       "Progressive Carry %",
    "player_season_carry_length":                      "Avg Carry Length",
    "player_season_ball_recoveries_90":                "Ball Recoveries p90",
    # OBV
    "player_season_obv_90":                            "OBV p90",
    "player_season_obv_pass_90":                       "OBV Pass p90",
    "player_season_obv_shot_90":                       "OBV Shot p90",
    "player_season_obv_defensive_action_90":           "OBV Def Action p90",
    "player_season_obv_dribble_carry_90":              "OBV Dribble & Carry p90",
    "player_season_obv_gk_90":                         "OBV GK p90",
    # xG 链条
    "player_season_xgchain_90":                        "xG Chain p90",
    "player_season_op_xgchain_90":                     "OP xG Chain p90",
    "player_season_xgbuildup_90":                      "xG Buildup p90",
    "player_season_op_xgbuildup_90":                   "OP xG Buildup p90",
    # 门将
    "player_season_save_ratio":                        "Save Ratio",
    "player_season_gsaa_90":                           "GSaA p90",
    "player_season_gsaa_ratio":                        "GSaA Ratio",
    "player_season_xs_ratio":                          "xSave Ratio",
    "player_season_shots_faced_90":                    "Shots Faced p90",
    "player_season_np_xg_faced_90":                    "NP xG Faced p90",
    "player_season_np_psxg_faced_90":                  "NP PSxG Faced p90",
    "player_season_clcaa":                             "CLCAA",
    # 综合
    "player_season_positive_outcome_90":               "Positive Outcome p90",
    "player_season_90s_played":                        "90s Played",
    "player_season_appearances":                       "Appearances",
    "player_season_average_minutes":                   "Avg Minutes",
}

# ─────────────────────────────────────────────
# 雷达图预设指标组
# ─────────────────────────────────────────────
RADAR_PRESET_GROUPS = {
    "Attacking": [
        "player_season_np_xg_90",
        "player_season_xa_90",
        "player_season_np_shots_90",
        "player_season_key_passes_90",
        "player_season_touches_inside_box_90",
        "player_season_deep_progressions_90",
        "player_season_dribbles_90",
        "player_season_npxgxa_90",
    ],
    "Defending": [
        "player_season_padj_tackles_90",
        "player_season_padj_interceptions_90",
        "player_season_pressures_90",
        "player_season_pressure_regains_90",
        "player_season_aerial_wins_90",
        "player_season_clearance_90",
        "player_season_defensive_action_regains_90",
        "player_season_blocks_per_shot",
    ],
    "Passing": [
        "player_season_op_passes_90",
        "player_season_passing_ratio",
        "player_season_deep_completions_90",
        "player_season_op_xa_90",
        "player_season_op_key_passes_90",
        "player_season_op_f3_passes_90",
        "player_season_through_balls_90",
        "player_season_crosses_90",
    ],
    "Pressing": [
        "player_season_pressures_90",
        "player_season_pressure_regains_90",
        "player_season_counterpressures_90",
        "player_season_counterpressure_regains_90",
        "player_season_aggressive_actions_90",
        "player_season_fhalf_pressures_90",
        "player_season_padj_pressures_90",
        "player_season_fhalf_pressures_ratio",
    ],
    "OBV": [
        "player_season_obv_90",
        "player_season_obv_pass_90",
        "player_season_obv_shot_90",
        "player_season_obv_defensive_action_90",
        "player_season_obv_dribble_carry_90",
    ],
    "Goalkeeper": [
        "player_season_save_ratio",
        "player_season_gsaa_90",
        "player_season_xs_ratio",
        "player_season_np_xg_faced_90",
        "player_season_clcaa",
        "player_season_obv_gk_90",
    ],
}

# ─────────────────────────────────────────────
# 柱状排名图指标分组
# ─────────────────────────────────────────────
BAR_METRIC_GROUPS = {
    "Attacking": [
        "player_season_np_xg_90",
        "player_season_goals_90",
        "player_season_xa_90",
        "player_season_assists_90",
        "player_season_key_passes_90",
        "player_season_touches_inside_box_90",
        "player_season_np_shots_90",
        "player_season_npxgxa_90",
        "player_season_deep_progressions_90",
        "player_season_passes_into_box_90",
        "player_season_shot_on_target_ratio",
        "player_season_conversion_ratio",
    ],
    "Defending": [
        "player_season_padj_tackles_90",
        "player_season_padj_interceptions_90",
        "player_season_padj_tackles_and_interceptions_90",
        "player_season_pressures_90",
        "player_season_pressure_regains_90",
        "player_season_defensive_action_regains_90",
        "player_season_aerial_wins_90",
        "player_season_aerial_ratio",
        "player_season_clearance_90",
        "player_season_challenge_ratio",
    ],
    "Passing": [
        "player_season_op_passes_90",
        "player_season_passing_ratio",
        "player_season_deep_completions_90",
        "player_season_op_xa_90",
        "player_season_op_key_passes_90",
        "player_season_op_f3_passes_90",
        "player_season_long_ball_ratio",
        "player_season_crosses_90",
        "player_season_crossing_ratio",
        "player_season_through_balls_90",
        "player_season_pressured_passing_ratio",
    ],
    "Pressing": [
        "player_season_pressures_90",
        "player_season_padj_pressures_90",
        "player_season_pressure_regains_90",
        "player_season_counterpressures_90",
        "player_season_aggressive_actions_90",
        "player_season_fhalf_pressures_90",
        "player_season_fhalf_pressures_ratio",
    ],
    "Dribbling & Carrying": [
        "player_season_dribbles_90",
        "player_season_dribble_ratio",
        "player_season_total_dribbles_90",
        "player_season_carries_90",
        "player_season_carry_ratio",
        "player_season_dispossessions_90",
        "player_season_turnovers_90",
        "player_season_ball_recoveries_90",
    ],
    "OBV": [
        "player_season_obv_90",
        "player_season_obv_pass_90",
        "player_season_obv_shot_90",
        "player_season_obv_defensive_action_90",
        "player_season_obv_dribble_carry_90",
    ],
    "xG Chain": [
        "player_season_xgchain_90",
        "player_season_op_xgchain_90",
        "player_season_xgbuildup_90",
        "player_season_op_xgbuildup_90",
    ],
    "Goalkeeper": [
        "player_season_save_ratio",
        "player_season_gsaa_90",
        "player_season_xs_ratio",
        "player_season_np_xg_faced_90",
        "player_season_clcaa",
        "player_season_obv_gk_90",
    ],
}

# ─────────────────────────────────────────────
# 位置筛选分组
# ─────────────────────────────────────────────
POSITION_GROUPS = {
    "All Positions": None,
    "Goalkeeper (GK)": ["Goalkeeper"],
    "Centre Back (CB)": ["Center Back"],
    "Full Back (FB)": [
        "Right Back", "Left Back",
        "Right Wing Back", "Left Wing Back",
    ],
    "Defensive / Central Mid (DM/CM)": [
        "Defensive Midfield", "Center Midfield",
        "Left Center Midfield", "Right Center Midfield",
    ],
    "Attacking Mid / Winger (AM/W)": [
        "Attacking Midfield", "Left Midfield", "Right Midfield",
        "Left Wing", "Right Wing",
    ],
    "Forward (ST)": [
        "Center Forward",
        "Left Center Forward", "Right Center Forward",
        "Secondary Striker",
    ],
}

# ─────────────────────────────────────────────
# 颜色配置（与 config.toml 主题保持一致）
# ─────────────────────────────────────────────
COLORS = {
    "primary":    "#00d4aa",   # 主色 - 青绿
    "secondary":  "#ff6b35",   # 辅色 - 橙红
    "accent":     "#4e9af1",   # 强调 - 蓝
    "warning":    "#f7d716",   # 警告 - 黄
    "danger":     "#ff3b3b",   # 危险 - 红
    "text":       "#ffffff",
    "muted":      "#8b9bb4",
    "bg_card":    "#1a1d2e",
    "bg_main":    "#0e1117",
    "grid":       "#2a2d3e",
}

# Plotly 通用布局基础配置
PLOTLY_BASE_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=COLORS["text"], family="Arial, sans-serif", size=12),
    colorway=[
        COLORS["primary"], COLORS["secondary"],
        COLORS["accent"],  COLORS["warning"],
    ],
    margin=dict(l=10, r=10, t=40, b=10),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        bordercolor=COLORS["grid"],
        borderwidth=1,
    ),
)

PLOTLY_AXIS_STYLE = dict(
    gridcolor=COLORS["grid"],
    linecolor=COLORS["grid"],
    tickcolor=COLORS["muted"],
    zerolinecolor=COLORS["grid"],
)
