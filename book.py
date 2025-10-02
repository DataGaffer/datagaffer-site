import requests
import json

API_KEY = "3c2b2ba5c3a0ccad7f273e8ca96bba5f"

fixture_id = 1451192  # put any real fixture ID here

url = f"https://v3.football.api-sports.io/odds?fixture={fixture_id}&bookmaker=8"
headers = {"x-apisports-key": API_KEY}

resp = requests.get(url, headers=headers).json()

# Show all bets Bet365 offers for this match
for bookmaker in resp.get("response", []):
    for bet in bookmaker["bookmakers"][0]["bets"]:
        print(f"{bet['id']} → {bet['name']}")