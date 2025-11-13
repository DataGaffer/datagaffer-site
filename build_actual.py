import os
import json

INPUT_FOLDER = "team_stats_api/2025"
OUTPUT_FILE = "team_actuals.json"

all_actuals = {}

for filename in os.listdir(INPUT_FOLDER):
    if not filename.endswith(".json"):
        continue

    team_name = filename.replace(".json", "").replace("_", " ")

    with open(os.path.join(INPUT_FOLDER, filename), "r") as f:
        data = json.load(f)

    home = data.get("home", {})
    away = data.get("away", {})

    home_matches = home.get("matches", 0)
    away_matches = away.get("matches", 0)
    total_matches = (home_matches + away_matches) or 1

    gf_total = home.get("goals_for", 0) + away.get("goals_for", 0)
    ga_total = home.get("goals_against", 0) + away.get("goals_against", 0)

    gf_avg = round(gf_total / total_matches, 2)
    ga_avg = round(ga_total / total_matches, 2)

    all_actuals[team_name] = {
        "goals_for": gf_avg,
        "goals_against": ga_avg
    }

with open(OUTPUT_FILE, "w") as f:
    json.dump(all_actuals, f, indent=2)

print("✔ team_actuals.json has been created!")