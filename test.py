import requests
import json
import os

API_KEY = "3c2b2ba5c3a0ccad7f273e8ca96bba5f"
SEASON_ID = 2025

# ✅ Load allowed league IDs
with open("league_ids.json", "r") as f:
    league_ids = json.load(f)

ALLOWED_LEAGUES = set(league_ids.values())

# ✅ Load teams.json
with open("teams.json", "r") as f:
    teams = json.load(f)

os.makedirs("players", exist_ok=True)

for team in teams:
    team_id = team["id"]
    team_name = team["name"]

    print(f"\n📊 Fetching {team_name} (ID {team_id})...")

    url = f"https://v3.football.api-sports.io/players?team={team_id}&season={SEASON_ID}"
    headers = {"x-apisports-key": API_KEY}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()

    players_out = []

    for item in data.get("response", []):
        player = item["player"]
        stats_list = item["statistics"]

        league_best = {}

        for stat in stats_list:
            league_id = stat["league"]["id"]
            if league_id not in ALLOWED_LEAGUES:
                continue

            games = stat.get("games", {})
            goals = stat.get("goals", {})
            shots = stat.get("shots", {})

            record = {
                "appearances": games.get("appearences") or 0,
                "minutes": games.get("minutes") or 0,
                "goals": goals.get("total") or 0,
                "assists": goals.get("assists") or 0,
                "shots": shots.get("total") or 0,
                "shots_on_target": shots.get("on") or 0,
            }

            prev = league_best.get(league_id, {})
            if not prev or record["minutes"] > prev["minutes"]:
                league_best[league_id] = record

        # ✅ Aggregate totals
        agg = {
            "appearances": 0,
            "minutes": 0,
            "goals": 0,
            "assists": 0,
            "shots": 0,
            "shots_on_target": 0,
        }
        for rec in league_best.values():
            for k in agg:
                agg[k] += rec[k]

        # ✅ Get reliable position
        position = player.get("position")
        if not position and stats_list:
            position = stats_list[0].get("games", {}).get("position")

        # ✅ Skip goalkeepers + <5 apps
        if position == "Goalkeeper":
            continue
        if agg["appearances"] < 3:
            continue

        players_out.append({
            "id": player.get("id"),
            "team_id": team_id,
            "name": player.get("name"),
            "position": position,
            **agg
        })

    # ✅ Safe filename
    safe_name = (
        team_name.replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
        .replace("*", "_")
        .replace("?", "_")
        .replace('"', "_")
        .replace("<", "_")
        .replace(">", "_")
        .replace("|", "_")
    )
    filepath = os.path.join("players", f"{safe_name}.json")
    with open(filepath, "w") as f:
        json.dump(players_out, f, indent=2)

    print(f"✅ Saved {len(players_out)} players → {filepath}")