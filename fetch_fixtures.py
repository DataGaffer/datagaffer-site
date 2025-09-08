import requests
import json
from datetime import datetime

API_KEY = "3c2b2ba5c3a0ccad7f273e8ca96bba5f"

# Load team names (dict of team names only)
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
    date_str = fixture["fixture"]["date"].split("T")[0]

    if home["name"] in known_names and away["name"] in known_names:
        valid_matches.append({
    "home": home,
    "away": away,
    "home_id": fixture["teams"]["home"]["id"],
    "away_id": fixture["teams"]["away"]["id"],
    "home_logo": fixture["teams"]["home"]["logo"],
    "away_logo": fixture["teams"]["away"]["logo"],
    "date": fixture["fixture"]["date"]
})


# Save it
with open("fixtures.json", "w") as f:
    json.dump(valid_matches, f, indent=2)

print(f"✅ Saved {len(valid_matches)} fixture(s) to fixtures.json.")



