import requests
import json
from datetime import datetime

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

    # --- Get H2H stats (last 5 meetings) ---
    h2h_url = f"https://v3.football.api-sports.io/fixtures/headtohead?h2h={home_id}-{away_id}&last=5"
    h2h_response = requests.get(h2h_url, headers=headers).json()
    try:
        h2h_matches = h2h_response["response"]
        home_wins = 0
        away_wins = 0
        draws = 0

        for match in h2h_matches:
            h_goals = match["goals"]["home"]
            a_goals = match["goals"]["away"]

            if h_goals is None or a_goals is None:
                continue

            if h_goals > a_goals:
                if match["teams"]["home"]["id"] == home_id:
                    home_wins += 1
                else:
                    away_wins += 1
            elif a_goals > h_goals:
                if match["teams"]["away"]["id"] == away_id:
                    away_wins += 1
                else:
                    home_wins += 1
            else:
                draws += 1

        h2h_stats = {
            "home_wins": home_wins,
            "away_wins": away_wins,
            "draws": draws
        }

    except Exception as e:
        print(f"⚠️ H2H error for {home['name']} vs {away['name']}: {e}")
        h2h_stats = {}

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
        "h2h_stats": h2h_stats
    })

# Save to fixtures.json
with open("fixtures.json", "w") as f:
    json.dump(valid_matches, f, indent=2)

# Save to h2h_and_odds.json
h2h_data = {}
for match in valid_matches:
    key = f"{match['home_id']}_{match['away_id']}"
    odds = match.get("book_odds", {})
    h2h = match.get("h2h_stats", {})

    h2h_data[key] = {
        "book_home_win": odds.get("home_win", 0),
        "book_draw": odds.get("draw", 0),
        "book_away_win": odds.get("away_win", 0),
        "h2h_home_wins": h2h.get("home_wins", 0),
        "h2h_away_wins": h2h.get("away_wins", 0),
        "h2h_draws": h2h.get("draws", 0)
    }

with open("h2h_and_odds.json", "w") as f:
    json.dump(h2h_data, f, indent=2)

print(f"✅ Saved {len(valid_matches)} fixture(s) to fixtures.json.")
print("✅ Saved h2h_and_odds.json.")





