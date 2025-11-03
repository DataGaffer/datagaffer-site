import os
import json
import numpy as np
from tqdm import tqdm

# === CONFIG ===
DATA_FOLDER = "team_stats_api/2025"
NUM_SIMULATIONS = 10000

# Only simulate these leagues
TARGET_LEAGUES = {
    39: "Premier League",
    140: "La Liga",
    78: "Bundesliga",
    135: "Serie A",
    61: "Ligue 1",
    88: "Eredivisie",
    119: "Danish Superliga",
    207: "Swiss Super League"
}


def simulate_league(teams, league_name):
    """Simulate one league season many times, return ranked results."""
    team_ids = list(teams.keys())
    if len(team_ids) < 2:
        print(f"⚠️ Not enough teams in {league_name} to simulate.")
        return []

    for _ in tqdm(range(NUM_SIMULATIONS), desc=f"Simulating {league_name}"):
        points = {tid: 0 for tid in team_ids}

        # Every team plays every other twice
        for i, home_id in enumerate(team_ids):
            for j, away_id in enumerate(team_ids):
                if i == j:
                    continue

                home = teams[home_id]
                away = teams[away_id]

                # Expected goals
                home_exp = (home["attack"] + away["defense"]) / 2 + 0.25
                away_exp = (away["attack"] + home["defense"]) / 2

                # Simulate match
                home_goals = np.random.poisson(home_exp)
                away_goals = np.random.poisson(away_exp)

                # Points
                if home_goals > away_goals:
                    points[home_id] += 3
                elif home_goals == away_goals:
                    points[home_id] += 1
                    points[away_id] += 1
                else:
                    points[away_id] += 3

        # Determine league winner
        winner = max(points, key=points.get)
        teams[winner]["titles"] += 1

        # Aggregate points
        for tid in team_ids:
            teams[tid]["points"] += points[tid]

    # Aggregate results
    results = []
    for tid in team_ids:
        t = teams[tid]
        avg_points = t["points"] / NUM_SIMULATIONS
        win_pct = (t["titles"] / NUM_SIMULATIONS) * 100
        results.append({
            "team": t["name"],
            "predicted_points": round(avg_points, 1),
            "win_chance": round(win_pct, 2)
        })

    results.sort(key=lambda x: (-x["predicted_points"], -x["win_chance"]))
    return results


def main():
    leagues = {}

    # Load team data
    for filename in os.listdir(DATA_FOLDER):
        if not filename.endswith(".json"):
            continue

        with open(os.path.join(DATA_FOLDER, filename)) as f:
            data = json.load(f)

        league_id = data.get("league_id")
        if league_id not in TARGET_LEAGUES:
            continue  # skip leagues we don’t want

        team_id = data["team_id"]
        team_name = filename.replace(".json", "").replace("_", " ")

        home = data.get("home", {})
        away = data.get("away", {})

        home_gf = home.get("goals_for", 0) / max(home.get("matches", 1), 1)
        away_gf = away.get("goals_for", 0) / max(away.get("matches", 1), 1)
        home_ga = home.get("goals_against", 0) / max(home.get("matches", 1), 1)
        away_ga = away.get("goals_against", 0) / max(away.get("matches", 1), 1)

        attack = (home_gf + away_gf) / 2
        defense = (home_ga + away_ga) / 2
        league_name = TARGET_LEAGUES[league_id]

        if league_name not in leagues:
            leagues[league_name] = {}

        leagues[league_name][team_id] = {
            "name": team_name,
            "attack": attack,
            "defense": defense,
            "points": 0,
            "titles": 0
        }

    # Simulate each league
    all_results = {}
    for league_name, teams in leagues.items():
        print(f"\n🏆 Simulating {league_name} ({len(teams)} teams)")
        results = simulate_league(teams, league_name)
        all_results[league_name] = results

        # Quick summary
        print(f"\n🏆 {league_name} Predictions:")
        for r in results[:5]:
            print(f"  {r['team']:<20} {r['predicted_points']:>6.1f} pts | 🏆 {r['win_chance']:>5.2f}%")

    # Save all leagues into one JSON
    with open("league_predictions.json", "w") as f:
        json.dump(all_results, f, indent=2)

    print("\n💾 Saved all predictions → league_predictions.json")


if __name__ == "__main__":
    main()