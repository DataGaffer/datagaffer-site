import requests
import json
from datetime import datetime
from match_simulator import simulate_match

API_KEY = "3c2b2ba5c3a0ccad7f273e8ca96bba5f"

# Load known team names from teams.json
with open("teams.json", "r") as f:
    known_teams = json.load(f)
known_names = {team["name"] for team in known_teams}

# Today's date in UTC
today = datetime.utcnow().strftime("%Y-%m-%d")

url = f"https://v3.football.api-sports.io/fixtures?date={today}"
headers = {"x-apisports-key": API_KEY}
response = requests.get(url, headers=headers)
data = response.json()

valid_matches = []

for fixture in data["response"]:
    home = fixture["teams"]["home"]
    away = fixture["teams"]["away"]
    fixture_id = fixture["fixture"]["id"]
    home_id = home["id"]
    away_id = away["id"]

    # Skip teams not in teams.json
    if home["name"] not in known_names or away["name"] not in known_names:
        continue

    # --- Get book odds (1X2) from Bet365 ---
    odds_url = f"https://v3.football.api-sports.io/odds?fixture={fixture_id}&bookmaker=8&bet=1"
    odds_response = requests.get(odds_url, headers=headers).json()
    try:
        odds_data = odds_response["response"][0]["bookmakers"][0]["bets"][0]["values"]
        book_odds = {
            "home_win": float(odds_data[0]["odd"]),
            "draw": float(odds_data[1]["odd"]),
            "away_win": float(odds_data[2]["odd"])
        }
    except (IndexError, KeyError, ValueError):
        book_odds = {}

       # --- Run our simulation (goals, corners, shots) ---
    try:
        sim = simulate_match(home_id, away_id)
        sim_stats = {
            "xg": {
                "home": f"{sim['home_score']:.2f}",
                "away": f"{sim['away_score']:.2f}",
                "total": f"{(sim['home_score'] + sim['away_score']):.2f}"
            },
            "corners": {
                "home": f"{sim['home_corners']:.1f}",
                "away": f"{sim['away_corners']:.1f}",
                "total": f"{sim['total_corners']:.1f}"
            },
            "shots": {
                "home": f"{sim['home_shots']:.1f}",
                "away": f"{sim['away_shots']:.1f}",
                "total": f"{sim['total_shots']:.1f}"
            }
        }


    except Exception as e:
        print(f"⚠️ Simulation error for {home['name']} vs {away['name']}: {e}")
        sim_stats = {"xg": {}, "corners": {}, "shots": {}}

    # --- Save this fixture ---
    valid_matches.append({
        "fixture_id": fixture_id,
        "home": home,
        "away": away,
        "home_id": home_id,
        "away_id": away_id,
        "home_logo": home["logo"],
        "away_logo": away["logo"],
        "date": fixture["fixture"]["date"],
        "book_odds": book_odds,
        "sim_stats": sim_stats
    })

# Save to fixtures.json
with open("fixtures.json", "w") as f:
    json.dump(valid_matches, f, indent=2)

print(f"✅ Saved {len(valid_matches)} fixture(s) to fixtures.json with simulation stats.")

