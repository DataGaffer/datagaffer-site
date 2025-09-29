import requests
import json
import time

NAME_FIXES = {
    "Bayer Leverkusen": "Leverkusen",
    "FC St. Pauli": "St. Pauli",
    "1899 Hoffenheim": "TSG Hoffenheim",
    "1. FC Heidenheim": "Heidenheim",
    "1.FC Köln": "Köln",
    "AC Milan": "Milan",
    "AS Roma": "Roma",
    "Stade Brestois 29": "Brest",
    "Paris FC": "Paris",
    "AZ Alkmaar": "AZ",
    "PSV Eindhoven": "PSV",
    "Bodo/Glimt": "FK Bodø/Glimt",
    "Bodø/Glimt": "FK Bodø/Glimt",
    "Club Brugge KV": "Club Brugge",
    "FC Copenhagen": "København",
    "Kairat Almaty": "Kairat",
    "Olympiakos Piraeus": "Olympiakos",
    "Union St. Gilloise": "Union Saint-Gilloise",
    "FC Basel 1893": "Basel",
    "SC Braga": "Braga",
    "FK Crvena Zvezda": "Crvena Zvezda",
    "Ferencvarosi TC": "Ferencváros",
    "FC Porto": "Porto",
    "Red Bull Salzburg": "Salzburg",
    "BSC Young Boys": "Young Boys",
    "Celta Vigo": "Celta de Vigo"
}

API_TOKEN = "aQV0CBhWCbafRJCjdNM52T1umWERV1Km8hAF1axSKajXA8umDeHarmYaTBaL"

# Load your existing API-Football teams.json
with open("teams.json", "r") as f:
    teams = json.load(f)

sportmonks_teams = []

for team in teams:
    team_name = team["name"]
    league = team.get("league", "Unknown")

    from urllib.parse import quote
   
    search_name = NAME_FIXES.get(team_name, team_name)
    search_endcoded = quote(search_name)

    url = f"https://api.sportmonks.com/v3/football/teams/search/{search_name}?api_token={API_TOKEN}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get("data"):
            sm_team = data["data"][0]  # first result
            sm_id = sm_team["id"]

            sportmonks_teams.append({
                "name": team_name,
                "id": sm_id,
                "league": league
            })
            print(f"✅ Matched {team_name} → {sm_id} (searched as {search_name})")
        else:
            print(f"⚠️ No Sportmonks match for {team_name} (searched as {search_name})")
    except Exception as e:
        print(f"❌ Error fetching {team_name}: {e}")

    time.sleep(1)  # avoid rate limits

# Save Sportmonks IDs
with open("teams_sportmonks.json", "w") as f:
    json.dump(sportmonks_teams, f, indent=2)

print(f"🎉 Saved {len(sportmonks_teams)} teams to teams_sportmonks.json")

