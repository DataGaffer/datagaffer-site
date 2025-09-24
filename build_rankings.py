import json
import glob
import os

# 🔹 Choose which league files to include
LEAGUES_TO_INCLUDE = [
    "bundesliga.json",
    "eredivisie.json",
    "la_liga.json",
    "ligue_1.json",
    "premier_league.json",
    "serie_a.json"
]

def load_selected_team_stats():
    stats = []
    for file in glob.glob("team_stats/*.json"):
        filename = os.path.basename(file)
        if filename in LEAGUES_TO_INCLUDE:   # only keep chosen leagues
            with open(file, "r") as f:
                stats.extend(json.load(f))
    return stats

def calculate_rankings(teams):
    rankings = {
        "btts": [],
        "over25": [],
        "team_total": [],
        "win": []
    }

    for team in teams:
        name = team["name"]
        team_id = team["id"]

        # --- Normalize overall vs split format ---
        if "scored" in team:  # overall format
            gf = team["scored"]
            ga = team["conceded"]
        else:  # home/away format
            gf = (team["home"]["goals_for"] + team["away"]["goals_for"]) / 2
            ga = (team["home"]["goals_against"] + team["away"]["goals_against"]) / 2

        # --- Probabilities from season averages ---
        btts_rate = (gf / (gf + 1)) * (ga / (ga + 1))   # rough BTTS proxy
        over25_rate = (gf + ga) / 3.0                   # relative to 2.5 goals
        team_total_rate = gf / 2.0                      # how often >1.5 goals
        win_rate = gf / (gf + ga + 1e-6)                # win share proxy

        rankings["btts"].append({"team": name, "id": team_id, "rate": btts_rate})
        rankings["over25"].append({"team": name, "id": team_id, "rate": over25_rate})
        rankings["team_total"].append({"team": name, "id": team_id, "rate": team_total_rate})
        rankings["win"].append({"team": name, "id": team_id, "rate": win_rate})

    # Sort each category high → low and assign ranks
    for key in rankings:
        rankings[key].sort(key=lambda x: x["rate"], reverse=True)
        for i, entry in enumerate(rankings[key][:30], start=1):  # 🔹 Top 20 only
            entry["rank"] = i
            entry["value"] = f"{entry['rate']*100:.1f}%"
            del entry["rate"]

    return rankings


if __name__ == "__main__":
    teams = load_selected_team_stats()
    rankings = calculate_rankings(teams)

    os.makedirs("rankings", exist_ok=True)
    with open("rankings/rankings.json", "w") as f:
        json.dump(rankings, f, indent=2)

    print("✅ rankings/rankings.json updated with top 20 teams per category (selected leagues only)!")

