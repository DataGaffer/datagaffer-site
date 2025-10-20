import json
import glob
import os

# 🔹 Configurable weights
WEIGHT_2024 = 0.5
WEIGHT_2025 = 0.5

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

            if team_id not in teams_data:
                teams_data[team_id] = {
                    "id": team_id,
                    "name": team_name,
                    "2024": {"gf": 0, "ga": 0, "matches": 0},
                    "2025": {"gf": 0, "ga": 0, "matches": 0}
                }

            gf = data["home"]["goals_for"] + data["away"]["goals_for"]
            ga = data["home"]["goals_against"] + data["away"]["goals_against"]
            matches = data["home"]["matches"] + data["away"]["matches"]

            teams_data[team_id][season]["gf"] += gf
            teams_data[team_id][season]["ga"] += ga
            teams_data[team_id][season]["matches"] += matches

    combined = []
    for team in teams_data.values():
        gf_2024, ga_2024, m_2024 = team["2024"].values()
        gf_2025, ga_2025, m_2025 = team["2025"].values()

        if m_2024 == 0 and m_2025 == 0:
            continue

        if m_2024 > 0 and m_2025 > 0:
            gf = (gf_2024 / m_2024) * WEIGHT_2024 + (gf_2025 / m_2025) * WEIGHT_2025
            ga = (ga_2024 / m_2024) * WEIGHT_2024 + (ga_2025 / m_2025) * WEIGHT_2025
        elif m_2024 > 0:
            gf = gf_2024 / m_2024
            ga = ga_2024 / m_2024
        else:
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
    rankings = {"btts": [], "over25": [], "under25": [], "team_total": [], "win": []}

    for team in teams:
        gf, ga = team["gf"], team["ga"]
        total_goals = gf + ga

        # --- Metrics ---
        btts_rate = (gf / (gf + 1)) * (ga / (ga + 1))
        over25_rate = total_goals / 3.0
        team_total_rate = gf / 2.0
        win_rate = gf / (gf + ga + 1e-6)

        # ✅ Under 2.5: inverse of total goals, clamped to [0,1]
        under25_rate = max(0.0, (3.0 - total_goals) / 3.0)

        rankings["btts"].append({"team": team["name"], "id": team["id"], "rate": btts_rate})
        rankings["over25"].append({"team": team["name"], "id": team["id"], "rate": over25_rate})
        rankings["team_total"].append({"team": team["name"], "id": team["id"], "rate": team_total_rate})
        rankings["win"].append({"team": team["name"], "id": team["id"], "rate": win_rate})
        rankings["under25"].append({"team": team["name"], "id": team["id"], "rate": under25_rate})

    # Sort & rank top 30 (all DESC — higher value = stronger for that market)
    for key in rankings:
        rankings[key].sort(key=lambda x: x["rate"], reverse=True)
        for i, entry in enumerate(rankings[key][:30], start=1):
            entry["rank"] = i
            entry["value"] = f"{entry['rate']*100:.1f}%"
            del entry["rate"]

    return rankings


import copy

def compare_rank_changes(new_rankings, old_rankings):
    """Add change/direction info comparing new vs old."""
    for key in new_rankings.keys():
        old_map = {t["id"]: t.get("rank", None) for t in old_rankings.get(key, []) if "id" in t}

        for entry in new_rankings[key]:
            old_rank = old_map.get(entry["id"], None)
            new_rank = entry.get("rank", None)

            if old_rank is None or new_rank is None:
                entry["change"] = 0
                entry["direction"] = "new"
                continue

            diff = old_rank - new_rank
            if diff > 0:
                entry["change"] = diff
                entry["direction"] = "up"
            elif diff < 0:
                entry["change"] = abs(diff)
                entry["direction"] = "down"
            else:
                entry["change"] = 0
                entry["direction"] = "same"

    return new_rankings


if __name__ == "__main__":
    teams = load_combined_team_stats()
    rankings = calculate_rankings(teams)

    os.makedirs("rankings", exist_ok=True)
    old_rankings_path = "rankings/rankings_prev.json"
    old_rankings = {}

    # 🔹 Load previous if it exists
    if os.path.exists(old_rankings_path):
        with open(old_rankings_path, "r") as f:
            old_rankings = json.load(f)

    # 🔹 Compare + add movement metadata
    updated_rankings = compare_rank_changes(copy.deepcopy(rankings), old_rankings)

    # 🔹 Save new rankings with arrows & labels
    with open("rankings/rankings.json", "w") as f:
        json.dump(updated_rankings, f, indent=2)

    # 🔹 Archive this version as the next "previous"
    with open(old_rankings_path, "w") as f:
        json.dump(rankings, f, indent=2)

    print("✅ rankings/rankings.json updated with movement indicators!")
