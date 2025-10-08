import json
import numpy as np
import os

# --- Load league coefficients ---
with open("league_coefficients.json") as f:
    league_coefficients = json.load(f)

# --- Load team boosters (optional) ---
try:
    with open("team_boosters.json") as f:
        team_boosters = json.load(f)
except FileNotFoundError:
    team_boosters = {}

# --- Load national team stats ---
def load_nation_stats():
    stats = {}
    with open("team_stats/national_teams.json") as f:
        for team in json.load(f):
            stats[team["id"]] = team
    return stats

team_stats = load_nation_stats()

# --- Load H2H + Odds ---
try:
    with open("h2h_and_odds.json") as f:
        h2h_and_odds = json.load(f)
except FileNotFoundError:
    h2h_and_odds = {}

# --- Simulate Nations Match ---
def simulate_nations_match(home_id, away_id, fixture_id=None):
    home = team_stats.get(home_id)
    away = team_stats.get(away_id)

    if not home or not away:
        print(f"⚠️ Missing national stats for {home_id} vs {away_id}")
        return {
            "home_score": 0, "away_score": 0,
            "home_win_pct": 0, "draw_pct": 0, "away_win_pct": 0,
            "over_2_5_pct": 0, "btts_pct": 0,
            "home_o1_5_pct": 0, "away_o1_5_pct": 0,
            "home_corners": 0, "away_corners": 0, "total_corners": 0,
            "home_shots": 0, "away_shots": 0, "total_shots": 0
        }

    if fixture_id:
        np.random.seed(fixture_id % (2**32 - 1))
    else:
        np.random.seed(42)

    # --- Goals (use averages directly) ---
    home_avg = home.get("goals_for", 1.0)
    home_conc = home.get("goals_against", 1.0)
    away_avg = away.get("goals_for", 1.0)
    away_conc = away.get("goals_against", 1.0)

    # --- Corners & Shots (manual) ---
    home_corners = home.get("corners", 0)
    home_corners_conc = home.get("corners_conceded", 0)
    away_corners = away.get("corners", 0)
    away_corners_conc = away.get("corners_conceded", 0)

    home_shots = home.get("shots", 0)
    home_shots_conc = home.get("shots_conceded", 0)
    away_shots = away.get("shots", 0)
    away_shots_conc = away.get("shots_conceded", 0)

    # --- Coefficients ---
    home_coef = league_coefficients.get(home["league"], 1.0)
    away_coef = league_coefficients.get(away["league"], 1.0)

    home_boost = team_boosters.get(str(home_id), 1.0)
    away_boost = team_boosters.get(str(away_id), 1.0)
    home_coef *= home_boost
    away_coef *= away_boost
    coef_ratio = home_coef / away_coef

    # --- Expected values (neutral weighting) ---
    exp_home = (home_avg + away_conc) / 2 + 0.15  # small home boost
    exp_away = (away_avg + home_conc) / 2
    exp_home_corners = (home_corners + away_corners_conc) / 2 + 0.3
    exp_away_corners = (away_corners + home_corners_conc) / 2
    exp_home_shots = (home_shots + away_shots_conc) / 2 + 1.0
    exp_away_shots = (away_shots + home_shots_conc) / 2

    exp_home *= coef_ratio
    exp_away /= coef_ratio
    exp_home_corners *= coef_ratio
    exp_away_corners /= coef_ratio
    exp_home_shots *= coef_ratio
    exp_away_shots /= coef_ratio

        # --- Combined H2H (both directions, fixed weight) ---
    key = f"home_{home_id}_{away_id}"
    reverse_key = f"home_{away_id}_{home_id}"

    h_avg, a_avg = None, None

    # Normal case
    if key in h2h_and_odds:
        data = h2h_and_odds[key]
        h_avg = data.get("avg_home")
        a_avg = data.get("avg_away")

    # Reverse matchup case (flip averages)
    elif reverse_key in h2h_and_odds:
        data = h2h_and_odds[reverse_key]
        # Reverse direction → swap averages
        h_avg = data.get("avg_away")
        a_avg = data.get("avg_home")

    # ✅ Constant H2H weight
    h2h_weight = 0.35

    if h_avg is not None and a_avg is not None:
        # sanity check: if one side has huge advantage but should be flipped
        if h_avg > 5 and a_avg < 1 and home_id > away_id:
            # likely reversed — swap them
            h_avg, a_avg = a_avg, h_avg

        exp_home = exp_home * (1 - h2h_weight) + h_avg * h2h_weight
        exp_away = exp_away * (1 - h2h_weight) + a_avg * h2h_weight
    # --- Simulations ---
    sims = 10000
    home_goals = np.random.poisson(exp_home, sims)
    away_goals = np.random.poisson(exp_away, sims)
    home_corners = np.random.poisson(exp_home_corners, sims)
    away_corners = np.random.poisson(exp_away_corners, sims)
    home_shots = np.random.poisson(exp_home_shots, sims)
    away_shots = np.random.poisson(exp_away_shots, sims)

    return {
        "home_score": round(np.mean(home_goals), 2),
        "away_score": round(np.mean(away_goals), 2),
        "home_win_pct": round(np.mean(home_goals > away_goals) * 100, 1),
        "draw_pct": round(np.mean(home_goals == away_goals) * 100, 1),
        "away_win_pct": round(np.mean(home_goals < away_goals) * 100, 1),
        "over_2_5_pct": round(np.mean((home_goals + away_goals) > 2) * 100, 1),
        "btts_pct": round(np.mean((home_goals > 0) & (away_goals > 0)) * 100, 1),
        "home_o1_5_pct": round(np.mean(home_goals > 1) * 100, 1),
        "away_o1_5_pct": round(np.mean(away_goals > 1) * 100, 1),
        "home_corners": round(np.mean(home_corners), 2),
        "away_corners": round(np.mean(away_corners), 2),
        "total_corners": round(np.mean(home_corners + away_corners), 2),
        "home_shots": round(np.mean(home_shots), 2),
        "away_shots": round(np.mean(away_shots), 2),
        "total_shots": round(np.mean(home_shots + away_shots), 2),
    }