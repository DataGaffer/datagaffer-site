import requests
import json
import os

API_KEY = "3c2b2ba5c3a0ccad7f273e8ca96bba5f"  # Replace with your actual API key

# Load fixtures
with open("fixtures.json") as f:
    fixtures = json.load(f)

headers = {
    "x-apisports-key": API_KEY
}

# Make sure cache folder exists
os.makedirs("h2h_cache", exist_ok=True)

for match in fixtures:
    home_id = match.get("home_id")
    away_id = match.get("away_id")

    if not home_id or not away_id:
        continue

    filename = f"h2h_cache/h2h_{home_id}_{away_id}.json"
    if os.path.exists(filename):
        print(f"Skipping {home_id} vs {away_id} (cached)")
        continue

    url = f"https://v3.football.api-sports.io/fixtures/headtohead?h2h={home_id}-{away_id}"
    response = requests.get(url, headers=headers)
    data = response.json()

    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Fetched H2H for {home_id} vs {away_id}")