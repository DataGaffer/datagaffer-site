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

def normalize_position(raw_pos, stats_list):
    """Normalize positions consistently."""
    pos = raw_pos
    if not pos:
        for st in stats_list:
            gp = (st.get("games") or {}).get("position")
            if gp:
                pos = gp
                break

    if pos in ("G", "Goalkeeper"): return "Goalkeeper"
    if pos in ("D", "Defender"): return "Defender"
    if pos in ("M", "Midfielder"): return "Midfielder"
    if pos in ("F", "Attacker", "Forward", "Striker"): return "Attacker"
    return pos

def gather_team_players(team_id):
    """Fetch ALL pages for a team & season."""
    headers = {"x-apisports-key": API_KEY}
    page = 1
    combined = []
    while True:
        url = f"https://v3.football.api-sports.io/players?team={team_id}&season={SEASON_ID}&page={page}"
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        combined.extend(data.get("response", []))

        paging = data.get("paging") or {}
        cur = paging.get("current") or 1
        tot = paging.get("total") or 1
        if cur >= tot:
            break
        page += 1
    return combined

for team in teams:
    team_id = team["id"]
    team_name = team["name"]

    print(f"\n📊 Fetching {team_name} (ID {team_id})...")

    items = gather_team_players(team_id)
    players_out = []

    for item in items:
        player = item["player"]
        stats_list = item.get("statistics", []) or []

        # ✅ Per-league deduplication: keep *only* block with max minutes
        league_best = {}
        for stat in stats_list:
            league_id = (stat.get("league") or {}).get("id")
            if league_id not in ALLOWED_LEAGUES:
                continue

            games = stat.get("games") or {}
            goals = stat.get("goals") or {}
            shots = stat.get("shots") or {}

            rec = {
                "appearances": (games.get("appearences") or games.get("appearances") or 0) or 0,
                "minutes": games.get("minutes") or 0,
                "goals": goals.get("total") or 0,
                "assists": goals.get("assists") or 0,
                "shots": shots.get("total") or 0,
                "shots_on_target": shots.get("on") or 0,
            }

            prev = league_best.get(league_id)
            if not prev or (rec["minutes"] > prev["minutes"]):
                league_best[league_id] = rec

        # ✅ Aggregate across deduped leagues
        agg = { "appearances": 0, "minutes": 0, "goals": 0, "assists": 0, "shots": 0, "shots_on_target": 0 }
        for rec in league_best.values():
            for k in agg:
                agg[k] += rec[k]

        # ✅ Normalize position
        position = normalize_position(player.get("position"), stats_list)

        # ✅ Fallback appearances if missing
        apps_final = agg["appearances"]
        if not apps_final and agg["minutes"]:
            apps_final = round(agg["minutes"] / 75)

        # ✅ Skip rules
        if position in ("Goalkeeper", "Defender"):
            continue
        if apps_final < 3:
            continue

        players_out.append({
            "id": player.get("id"),
            "team_id": team_id,
            "name": player.get("name"),
            "position": position,
            "appearances": int(apps_final),
            "minutes": int(agg["minutes"]),
            "goals": int(agg["goals"]),
            "assists": int(agg["assists"]),
            "shots": int(agg["shots"]),
            "shots_on_target": int(agg["shots_on_target"]),
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

