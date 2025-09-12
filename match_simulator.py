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

# Helper to safely get goal stat
def get_stat(team, side, stat_type):
    try:
        if side in team and stat_type in team[side]:
            return team[side][stat_type]
        elif stat_type == "goals_for":
            return team.get("scored", 0)
        elif stat_type == "goals_against":
            return team.get("conceded", 0)
        else:
            return 0
    except:
        return 0

# Simulate one match
def simulate_match(home_id, away_id):
    home = team_stats[home_id]
    away = team_stats[away_id]

    # Get goal stats
    home_avg = get_stat(home, "home", "goals_for")
    home_conc = get_stat(home, "home", "goals_against")
    away_avg = get_stat(away, "away", "goals_for")
    away_conc = get_stat(away, "away", "goals_against")

    # League coefficients
    home_coef = league_coefficients.get(home["league"], 1.0)
    away_coef = league_coefficients.get(away["league"], 1.0)
    coef_ratio = home_coef / away_coef

    # Base expected goals
    exp_home = (home_avg + away_conc) / 2
    exp_away = (away_avg + home_conc) / 2

    # Home advantage
    exp_home += 0.25

    # League strength boost
    exp_home *= coef_ratio
    exp_away /= coef_ratio

    # Inject H2H average goals (if available)
    fixture_key = f"{home_id}_{away_id}"
    h2h_data = h2h_and_odds.get(fixture_key, {})
    if "h2h_avg_home" in h2h_data and "h2h_avg_away" in h2h_data:
        exp_home = (exp_home * 0.85) + (h2h_data["h2h_avg_home"] * 0.15)
        exp_away = (exp_away * 0.85) + (h2h_data["h2h_avg_away"] * 0.15)

    # Book odds influence (slight goal boost for favorite)
    if "book_home_win" in h2h_data and "book_away_win" in h2h_data:
        try:
            ratio = h2h_data["book_away_win"] / h2h_data["book_home_win"]
            if ratio > 1.2:
                exp_home *= 1.05
            elif ratio < 0.8:
                exp_away *= 1.05
        except ZeroDivisionError:
            pass

    # Elite matchup cap
    if home_coef > 0.9 and away_coef > 0.9:
        exp_home = min(exp_home, 2.8)
        exp_away = min(exp_away, 2.5)

    # Cap weak team scoring when away
    if away_coef < 0.75:
        exp_away *= 0.85

    # Downgrade weak defense vs elite
    if home_coef > 0.9 and away_coef < 0.7:
        exp_home *= 1.15

    # Poisson simulation
    home_goals = [np.random.poisson(exp_home) for _ in range(1000)]
    away_goals = [np.random.poisson(exp_away) for _ in range(1000)]

    # Outcome probabilities
    home_wins = sum(h > a for h, a in zip(home_goals, away_goals)) / 10
    draws = sum(h == a for h, a in zip(home_goals, away_goals)) / 10
    away_wins = sum(h < a for h, a in zip(home_goals, away_goals)) / 10

    over_2_5 = sum((h + a) > 2 for h, a in zip(home_goals, away_goals)) / 10
    btts = sum((h > 0 and a > 0) for h, a in zip(home_goals, away_goals)) / 10
    home_o1_5 = sum(h > 1 for h in home_goals) / 10
    away_o1_5 = sum(a > 1 for a in away_goals) / 10

    return {
        "home": home["name"],
        "away": away["name"],
        "home_logo": home["logo"],
        "away_logo": away["logo"],
        "home_score": round(np.mean(home_goals), 2),
        "away_score": round(np.mean(away_goals), 2),
        "home_win_pct": round(home_wins, 1),
        "draw_pct": round(draws, 1),
        "away_win_pct": round(away_wins, 1),
        "over_2_5_pct": round(over_2_5, 1),
        "btts_pct": round(btts, 1),
        "home_o1_5_pct": round(home_o1_5, 1),
        "away_o1_5_pct": round(away_o1_5, 1),
    }


