# Football Analytics Dashboard

Streamlit-based football data visualisation app powered by the StatsBomb API.

## Project Structure

```
football_analytics/
├── app.py                        # Main entry point & routing
├── requirements.txt
├── .streamlit/
│   └── config.toml               # Dark theme configuration
│
├── views/                        # Page-level view modules (each has render())
│   ├── player_season.py          # ✅ Player Season Dashboard
│   ├── team_season.py            # 🚧 Team Season Dashboard (next)
│   ├── match_dashboard.py        # 🚧 Match Dashboard (next)
│   └── player_match.py           # 🚧 Player Match Stats (next)
│
├── components/                   # Reusable chart components
│   ├── radar_chart.py            # ✅ Attribute radar (Plotly Scatterpolar)
│   ├── bar_ranking.py            # ✅ League ranking bar + OBV breakdown
│   └── pitch_viz.py              # 🚧 Pitch visualisations (mplsoccer)
│
├── utils/
│   ├── metrics_config.py         # ✅ Metric labels, groups, colours
│   ├── data_loader.py            # ✅ StatsBomb API calls (cached)
│   ├── normalize.py              # ✅ Percentile rank & min-max normalisation
│   └── image_helper.py           # ✅ Local image loading with placeholder fallback
│
└── assets/
    ├── players/                  # {player_id}.png  (or .jpg/.webp)
    └── teams/                    # {team_id}.png
```

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

## StatsBomb Credentials

For paid API access, create `.streamlit/secrets.toml`:

```toml
[statsbomb]
user   = "your_email@example.com"
passwd = "your_password"
```

Without credentials the app falls back to StatsBomb open data.

## Modules (Phase 1 complete)

### ✅ Player Season Dashboard
- Profile card: photo, team badge, bio, season summary
- Attribute radar chart with percentile rank normalisation & player comparison
- OBV breakdown bar chart with league average reference
- Key stats metrics row (with delta vs league average)
- League ranking bar chart: any metric, position filter, min minutes, top-N

### 🚧 Coming next
- **Team Season Dashboard** — team profile, points timeline, league ranking
- **Match Dashboard** — match header, team stats, lineup pitch visualisation
- **Player Match Stats** — shot/pass/dribble/defensive action pitch maps
