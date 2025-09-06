import requests
import json
from datetime import datetime
import os

# Replace this with your actual API key
API_KEY = "3c2b2ba5c3a0ccad7f273e8ca96bba5f"

# Load your team list from teams.json
with open("teams.json", "r") as f:
    known_teams = json.load(f)

# Get today's date in YYYY-MM-DD format
today = datetime.now().strftime("%Y-%m-%d")

# Set up the API request
url = f"https://v3.football.api-sports.io/fixtures?date={today}"

headers = {
    "x-apisports-key": API_KEY
}

response = requests.get(url, headers=headers)
data = response.json()

# Parse fixtures
valid_matches = []
for fixture in data["response"]:
    home = fixture["teams"]["home"]["name"]
    away = fixture["teams"]["away"]["name"]

    if home in known_teams and away in known_teams:
        valid_matches.append({
            "home": home,
            "away": away,
            "date": today
        })

# Save to fixtures.json
with open("fixtures.json", "w") as f:
    json.dump(valid_matches, f, indent=2)

print(f"Saved {len(valid_matches)} fixture(s) to fixtures.json.")
