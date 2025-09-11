import os
import json
import random
from datetime import datetime

# Load today's fixtures
with open("fixtures.json", "r") as f:
    fixtures = json.load(f)

today = datetime.today().strftime("%Y-%m-%d")

# Load team list to get team IDs
with open("teams.json", "r") as f:
    all_teams = json.load(f)

team_id_to_name = {team["id"]: team["name"] for team in all_teams}

# Folder where player stats live
PLAYER_STATS_FOLDER = "player_stats"
SIM_OUTPUT_FOLDER = "player_simulations"
os.makedirs(SIM_OUTPUT_FOLDER, exist_ok=True)

# Simulation parameters
SIMULATIONS = 5000

def simulate_player_goals(player, team_avg_goals):
    goals_per_appearance = player["goals"] / player["appearances"] if player["appearances"] > 0 else 0
    player_chance = min(goals_per_appearance / team_avg_goals if team_avg_goals > 0 else 0, 1.0)

    goals = 0
    for _ in range(SIMULATIONS):
        if random.random() < player_chance:
            goals += 1

    return round(goals / SIMULATIONS, 3)

# Go through each fixture
for fixture in fixtures:
    if fixture["date"] != today:
        continue

    for side in ["home_team", "away_team"]:
        team = fixture[side]
        team_id = team["id"]
        team_name = team["name"]
        team_goals = fixture["home_score"] if side == "home_team" else fixture["away_score"]

        stats_path = os.path.join(PLAYER_STATS_FOLDER, f"{team_id}.json")
        if not os.path.exists(stats_path):
            print(f"⚠️ No player stats found for {team_name}")
            continue

        with open(stats_path, "r") as f:
            players = json.load(f)

        simulated_players = []
        for player in players:
            sim_goals = simulate_player_goals(player, team_goals)
            if sim_goals > 0:
                player_result = {
                    "name": player["name"],
                    "position": player["position"],
                    "goals_per90_simulated": sim_goals,
                    "appearances": player["appearances"],
                    "goals": player["goals"],
                    "assists": player["assists"],
                    "shots": player["shots"],
                    "shots_on_target": player["shots_on_target"]
                }
                simulated_players.append(player_result)

        if simulated_players:
            output_file = os.path.join(SIM_OUTPUT_FOLDER, f"{team_name.replace(' ', '_')}.json")
            with open(output_file, "w") as f:
                json.dump(simulated_players, f, indent=2)

            print(f"✅ Simulated {len(simulated_players)} players for {team_name}")
        else:
            print(f"❌ No valid players found for {team_name}")


