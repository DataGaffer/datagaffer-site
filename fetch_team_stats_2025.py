# fetch_team_stats_2025.py
import os, json, time, requests

API_KEY = os.getenv("APISPORTS_KEY", "3c2b2ba5c3a0ccad7f273e8ca96bba5f")  # <- set env var in prod
SEASON = 2025

BASE = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

with open("teams.json", "r") as f:
    TEAMS = json.load(f)

with open("league_ids.json", "r") as f:
    LEAGUE_IDS = json.load(f)
ALLOWED_LEAGUES = set(LEAGUE_IDS.values())

def api_get(path, params):
    for attempt in range(3):
        r = requests.get(f"{BASE}{path}", headers=HEADERS, params=params, timeout=30)
        if r.status_code == 200:
            return r.json()
        time.sleep(1 + attempt)
    r.raise_for_status()

def find_domestic_league_id(team_id: int, season: int):
    data = api_get("/leagues", {"team": team_id, "season": season})
    for item in data.get("response", []):
        league = item.get("league", {})
        if league.get("type") == "League" and league.get("id") in ALLOWED_LEAGUES:
            return league.get("id")
    return None

def pull_team_stats(team_id: int, league_id: int, season: int):
    data = api_get("/teams/statistics", {"team": team_id, "league": league_id, "season": season})
    resp = data.get("response") or {}
    fixtures = resp.get("fixtures", {}).get("played", {})
    gf = resp.get("goals", {}).get("for", {}).get("total", {})
    ga = resp.get("goals", {}).get("against", {}).get("total", {})
    if not fixtures:
        return None
    return {
        "team_id": team_id, "season": season, "league_id": league_id,
        "home": {
            "matches": fixtures.get("home", 0) or 0,
            "goals_for": gf.get("home", 0) or 0,
            "goals_against": ga.get("home", 0) or 0,
        },
        "away": {
            "matches": fixtures.get("away", 0) or 0,
            "goals_for": gf.get("away", 0) or 0,
            "goals_against": ga.get("away", 0) or 0,
        }
    }

def safe_name(s: str) -> str:
    for ch in ' /\\:*?"<>|':
        s = s.replace(ch, "_")
    return s

def main():
    out_dir = os.path.join("team_stats_api", str(SEASON))
    os.makedirs(out_dir, exist_ok=True)

    saved = skipped = 0
    for t in TEAMS:
        team_id, team_name = t["id"], t["name"]
        print(f"• {team_name} ({team_id}) … ", end="", flush=True)

        lid = find_domestic_league_id(team_id, SEASON)
        if not lid:
            print("skip (no domestic league)")
            skipped += 1
            continue

        payload = pull_team_stats(team_id, lid, SEASON)
        if not payload:
            print("skip (no stats)")
            skipped += 1
            continue

        with open(os.path.join(out_dir, f"{safe_name(team_name)}.json"), "w") as f:
            json.dump(payload, f, indent=2)
        print("saved")
        saved += 1
        time.sleep(0.35)

    print(f"\n✅ Done. Saved {saved}, skipped {skipped}.")

if __name__ == "__main__":
    main()