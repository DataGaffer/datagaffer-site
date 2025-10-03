import json
import glob
import os

# 🔹 Configurable weights
WEIGHT_2024 = 0.6   # use 60% from 2024
WEIGHT_2025 = 0.4   # use 40% from 2025

# 🔹 Paths to both seasons
TEAM_STATS_PATHS = {
    "2024": "team_stats_api/2024/*.json",
    "2025": "team_stats_api/2025/*.json"
}

def load_combined_team_stats():
    teams_data = {}

    for season, path in TEAM_STATS_PATHS.items():
        for file in glob.glob(path):
            with open(file, "r") as f:
                data = json.load(f)

            team_id = data["team_id"]
            team_name = os.path.splitext(os.path.basename(file))[0].replace("_", " ")

            # Initialize if first time seeing this team
            if team_id not in teams_data:
                teams_data[team_id] = {
                    "id": team_id,
                    "name": team_name,   # ✅ use filename as team name
                    "2024": {"gf": 0, "ga": 0, "matches": 0},
                    "2025": {"gf": 0, "ga": 0, "matches": 0}
                }

            # Average goals for/against
            gf = data["home"]["goals_for"] + data["away"]["goals_for"]
            ga = data["home"]["goals_against"] + data["away"]["goals_against"]
            matches = data["home"]["matches"] + data["away"]["matches"]

            teams_data[team_id][season]["gf"] += gf
            teams_data[team_id][season]["ga"] += ga
            teams_data[team_id][season]["matches"] += matches

    # Combine weighted stats
    combined = []
    for team in teams_data.values():
        gf_2024, ga_2024, m_2024 = team["2024"].values()
        gf_2025, ga_2025, m_2025 = team["2025"].values()

        if m_2024 == 0 and m_2025 == 0:
            continue

        # Weighted averages if both available, otherwise fall back
        if m_2024 > 0 and m_2025 > 0:
            gf = (gf_2024 / m_2024) * WEIGHT_2024 + (gf_2025 / m_2025) * WEIGHT_2025
            ga = (ga_2024 / m_2024) * WEIGHT_2024 + (ga_2025 / m_2025) * WEIGHT_2025
        elif m_2024 > 0:  # only 2024
            gf = gf_2024 / m_2024
            ga = ga_2024 / m_2024
        else:  # only 2025
            gf = gf_2025 / m_2025
            ga = ga_2025 / m_2025

        combined.append({
            "id": team["id"],
            "name": team["name"],
            "gf": gf,
            "ga": ga
        })

    return combined


def calculate_rankings(teams):
    rankings = { "btts": [], "over25": [], "team_total": [], "win": [] }

    for team in teams:
        gf, ga = team["gf"], team["ga"]

        # --- Simple proxy metrics ---
        btts_rate = (gf / (gf + 1)) * (ga / (ga + 1))
        over25_rate = (gf + ga) / 3.0
        team_total_rate = gf / 2.0
        win_rate = gf / (gf + ga + 1e-6)

        rankings["btts"].append({"team": team["name"], "id": team["id"], "rate": btts_rate})
        rankings["over25"].append({"team": team["name"], "id": team["id"], "rate": over25_rate})
        rankings["team_total"].append({"team": team["name"], "id": team["id"], "rate": team_total_rate})
        rankings["win"].append({"team": team["name"], "id": team["id"], "rate": win_rate})

    # Sort & rank top 30
    for key in rankings:
        rankings[key].sort(key=lambda x: x["rate"], reverse=True)
        for i, entry in enumerate(rankings[key][:30], start=1):
            entry["rank"] = i
            entry["value"] = f"{entry['rate']*100:.1f}%"
            del entry["rate"]

    return rankings


if __name__ == "__main__":
    teams = load_combined_team_stats()
    rankings = calculate_rankings(teams)

    os.makedirs("rankings", exist_ok=True)
    with open("rankings/rankings.json", "w") as f:
        json.dump(rankings, f, indent=2)

    print("✅ rankings/rankings.json updated (hybrid 2024 + 2025 stats)!")

