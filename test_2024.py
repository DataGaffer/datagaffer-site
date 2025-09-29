import requests
import json
import os

API_KEY = "3c2b2ba5c3a0ccad7f273e8ca96bba5f"
SEASON_ID = 2024   # last season

# ✅ Load allowed league IDs
with open("league_ids.json", "r") as f:
    league_ids = json.load(f)
ALLOWED_LEAGUES = set(league_ids.values())

# ✅ Load teams.json
with open("teams.json", "r") as f:
    teams = json.load(f)

# ✅ Separate folder for last season
os.makedirs("players_2024", exist_ok=True)

for team in teams:
    team_id = team["id"]
    team_name = team["name"]

    # ✅ Safe filename first
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
    filepath = os.path.join("players_2024", f"{safe_name}.json")

    # ✅ Skip if already saved
    if os.path.exists(filepath):
        print(f"⏩ Skipping {team_name}, already saved → {filepath}")
        continue

    print(f"\n📊 Fetching 2024/25 stats for {team_name} (ID {team_id})...")

    # Step 1: get current squad (2025) to know which players exist
    squad_url = f"https://v3.football.api-sports.io/players/squads?team={team_id}"
    headers = {"x-apisports-key": API_KEY}
    squad_resp = requests.get(squad_url, headers=headers)
    squad_resp.raise_for_status()
    squad_data = squad_resp.json()

    players_out = []

    for p in squad_data.get("response", [])[0].get("players", []):
        player_id = p.get("id")
        player_name = p.get("name")

        # Step 2: fetch their stats for SEASON_ID = 2024
        url = f"https://v3.football.api-sports.io/players?id={player_id}&season={SEASON_ID}"
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        if not data.get("response"):
            continue

        item = data["response"][0]
        stats_list = item.get("statistics", [])
        league_best = {}

        for stat in stats_list:
            league = stat.get("league", {})
            league_id = league.get("id")
            if league_id not in ALLOWED_LEAGUES:
                continue

            games = stat.get("games", {})
            goals = stat.get("goals", {})
            shots = stat.get("shots", {})

            apps = games.get("appearences") or 0
            mins = games.get("minutes") or 0

            # Skip useless records
            if apps == 0 and mins == 0:
                continue

            record = {
                "appearances": apps,
                "minutes": mins,
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

        # ✅ Position
        position = item["player"].get("position")
        if not position and stats_list:
            position = stats_list[0].get("games", {}).get("position")

        # ✅ Skip GKs + <5 apps
        if position == "Goalkeeper":
            continue
        if agg["appearances"] < 5:
            continue

        players_out.append({
            "id": player_id,
            "team_id": team_id,
            "name": player_name,
            "position": position,
            **agg
        })

    with open(filepath, "w") as f:
        json.dump(players_out, f, indent=2)

    print(f"✅ Saved {len(players_out)} players → {filepath}")