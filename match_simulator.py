# match_simulator.py

import json
import numpy as np

# Load league coefficients
with open("league_coefficients.json") as f:
    league_coefficients = json.load(f)

# Load team stats (across all leagues)
def load_team_stats():
    stats = {}
    leagues = [
        "premier_league.json",
        "la_liga.json",
        "bundesliga.json",
        "serie_a.json",
        "ligue_1.json",
        "eredivisie.json",
        "champions_league.json",
        "europa_league.json"
    ]
    for file in leagues:
        with open(f"team_stats/{file}") as f:
            for team in json.load(f):
                stats[team["id"]] = team
    return stats

team_stats = load_team_stats()

# Load H2H and odds
try:
    with open("h2h_and_odds.json") as f:
        h2h_and_odds = json.load(f)
except FileNotFoundError:
    h2h_and_odds = {}

# Helper to safely get stat (works for both formats)
def get_stat(team, side, stat_type):
    try:
        # --- Format A (home/away split) ---
        if side in team and stat_type in team[side]:
            return team[side][stat_type]

        # --- Format B (overall stats) ---
        if stat_type == "goals_for":
            return team.get("scored", 0)
        elif stat_type == "goals_against":
            return team.get("conceded", 0)
        elif stat_type == "corners":
            return team.get("corners", 0)
        elif stat_type == "corners_against":
            return team.get("corners_conceded", 0)
        elif stat_type == "shots":
            return team.get("shots", 0)
        elif stat_type == "shots_against":
            return team.get("shots_conceded", 0)

        return 0
    except:
        return 0

# Simulate one match
def simulate_match(home_id, away_id):
    home = team_stats[home_id]
    away = team_stats[away_id]

    # --- Goals ---
    home_avg = get_stat(home, "home", "goals_for")
    home_conc = get_stat(home, "home", "goals_against")
    away_avg = get_stat(away, "away", "goals_for")
    away_conc = get_stat(away, "away", "goals_against")

    # --- Corners ---
    home_corners = get_stat(home, "home", "corners")
    home_corners_conc = get_stat(home, "home", "corners_against")
    away_corners = get_stat(away, "away", "corners")
    away_corners_conc = get_stat(away, "away", "corners_against")

    # --- Shots ---
    home_shots = get_stat(home, "home", "shots")
    home_shots_conc = get_stat(home, "home", "shots_against")
    away_shots = get_stat(away, "away", "shots")
    away_shots_conc = get_stat(away, "away", "shots_against")

    # League coefficients
    home_coef = league_coefficients.get(home["league"], 1.0)
    away_coef = league_coefficients.get(away["league"], 1.0)
    coef_ratio = home_coef / away_coef

    # Base expected goals
    exp_home = (home_avg + away_conc) / 2
    exp_away = (away_avg + home_conc) / 2

    # Base expected corners
    exp_home_corners = (home_corners + away_corners_conc) / 2
    exp_away_corners = (away_corners + home_corners_conc) / 2

    # Base expected shots
    exp_home_shots = (home_shots + away_shots_conc) / 2
    exp_away_shots = (away_shots + home_shots_conc) / 2

    # Home advantage
    exp_home += 0.25
    exp_home_corners += 0.3
    exp_home_shots += 1.2

    # League strength boost
    exp_home *= coef_ratio
    exp_away /= coef_ratio
    exp_home_corners *= coef_ratio
    exp_away_corners /= coef_ratio
    exp_home_shots *= coef_ratio
    exp_away_shots /= coef_ratio

    # ---- H2H goal averages influence (25%) ----
    fixture_key = f"{home_id}_{away_id}"
    h2h_data = h2h_and_odds.get(fixture_key, {})
    h_avg = h2h_data.get("h2h_avg_home", None)
    a_avg = h2h_data.get("h2h_avg_away", None)
    if isinstance(h_avg, (int, float)) and isinstance(a_avg, (int, float)):
        w = 0.15  # 15% weight from H2H goal averages
        exp_home = exp_home * (1 - w) + h_avg * w
        exp_away = exp_away * (1 - w) + a_avg * w

    # --- Poisson simulations ---
    sims = 5000
    home_goals = np.random.poisson(exp_home, sims)
    away_goals = np.random.poisson(exp_away, sims)
    home_corners = np.random.poisson(exp_home_corners, sims)
    away_corners = np.random.poisson(exp_away_corners, sims)
    home_shots = np.random.poisson(exp_home_shots, sims)
    away_shots = np.random.poisson(exp_away_shots, sims)

    # Outcome probabilities
    home_wins = np.mean(home_goals > away_goals) * 100
    draws = np.mean(home_goals == away_goals) * 100
    away_wins = np.mean(home_goals < away_goals) * 100

    over_2_5 = np.mean((home_goals + away_goals) > 2) * 100
    btts = np.mean((home_goals > 0) & (away_goals > 0)) * 100
    home_o1_5 = np.mean(home_goals > 1) * 100
    away_o1_5 = np.mean(away_goals > 1) * 100

    return {
        "home": home["name"],
        "away": away["name"],
        "home_logo": home["logo"],
        "away_logo": away["logo"],

        # --- Goals ---
        "home_score": round(np.mean(home_goals), 2),
        "away_score": round(np.mean(away_goals), 2),
        "home_win_pct": round(home_wins, 1),
        "draw_pct": round(draws, 1),
        "away_win_pct": round(away_wins, 1),
        "over_2_5_pct": round(over_2_5, 1),
        "btts_pct": round(btts, 1),
        "home_o1_5_pct": round(home_o1_5, 1),
        "away_o1_5_pct": round(away_o1_5, 1),

        # --- Corners ---
        "home_corners": round(np.mean(home_corners), 2),
        "away_corners": round(np.mean(away_corners), 2),
        "total_corners": round(np.mean(home_corners + away_corners), 2),

        # --- Shots ---
        "home_shots": round(np.mean(home_shots), 2),
        "away_shots": round(np.mean(away_shots), 2),
        "total_shots": round(np.mean(home_shots + away_shots), 2),
    }




