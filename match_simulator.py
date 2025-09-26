import json
import numpy as np

# Load league coefficients
with open("league_coefficients.json") as f:
    league_coefficients = json.load(f)

# Load team-specific boosters (optional)
try:
    with open("team_boosters.json") as f:
        team_boosters = json.load(f)
except FileNotFoundError:
    team_boosters = {}


# Load team stats
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
        "europa_league.json",
    ]
    for file in leagues:
        with open(f"team_stats/{file}") as f:
            for team in json.load(f):
                stats[team["id"]] = team
    return stats

team_stats = load_team_stats()

# Load H2H + odds
try:
    with open("h2h_and_odds.json") as f:
        h2h_and_odds = json.load(f)
except FileNotFoundError:
    h2h_and_odds = {}

# Helper
def get_stat(team, side, stat_type):
    try:
        if side in team and stat_type in team[side]:
            return team[side][stat_type]

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
def simulate_match(home_id, away_id, fixture_id=None):
    home = team_stats.get(home_id)
    away = team_stats.get(away_id)

    if not home or not away:
        print(f"⚠️ Missing team stats for {home_id} vs {away_id}")
        return {
            "home_score": 0, "away_score": 0,
            "home_win_pct": 0, "draw_pct": 0, "away_win_pct": 0,
            "over_2_5_pct": 0, "btts_pct": 0,
            "home_o1_5_pct": 0, "away_o1_5_pct": 0,
            "home_corners": 0, "away_corners": 0, "total_corners": 0,
            "home_shots": 0, "away_shots": 0, "total_shots": 0
        }

    # Seed random generator (reproducible per fixture)
    if fixture_id:
        np.random.seed(fixture_id % (2**32 - 1))
    else:
        np.random.seed(42)

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

# --- Apply team boosters ---
    home_boost = team_boosters.get(str(home_id), 1.0)
    away_boost = team_boosters.get(str(away_id), 1.0)

    home_coef *= home_boost
    away_coef *= away_boost

    coef_ratio = home_coef / away_coef


    # Expected values
    exp_home = (home_avg + away_conc) / 2 + 0.25
    exp_away = (away_avg + home_conc) / 2
    exp_home_corners = (home_corners + away_corners_conc) / 2 + 0.3
    exp_away_corners = (away_corners + home_corners_conc) / 2
    exp_home_shots = (home_shots + away_shots_conc) / 2 + 1.2
    exp_away_shots = (away_shots + home_shots_conc) / 2

    # League strength boost
    exp_home *= coef_ratio
    exp_away /= coef_ratio
    exp_home_corners *= coef_ratio
    exp_away_corners /= coef_ratio
    exp_home_shots *= coef_ratio
    exp_away_shots /= coef_ratio

   # ---- H2H influence ----
    with open("h2h_and_odds.json") as f:
     h2h_and_odds = json.load(f)
   
    key = f"home_{home_id}_{away_id}"
    h2h_data = h2h_and_odds.get(key, {})
    h_avg = h2h_data.get("avg_home", None)
    a_avg = h2h_data.get("avg_away", None)

    num_matches = h2h_data.get("num_matches", 0)

    if h_avg is not None and a_avg is not None and num_matches > 0:
        max_weight = 0.40
        w = min(max_weight, 0.10 * num_matches)
        exp_home = exp_home * (1 - w) + h_avg * w
        exp_away = exp_away * (1 - w) + a_avg * w



    # --- Poisson simulations ---
    sims = 20000
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





