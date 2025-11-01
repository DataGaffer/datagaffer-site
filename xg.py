import json

TEAMS_FILE = "teams.json"
OUTPUT_FILE = "xg_stats.json"

# ✅ Known league mappings (same as before)
LEAGUE_MAP = {
    "Premier League": [
        "Arsenal", "Aston Villa", "Bournemouth", "Brentford", "Brighton", "Burnley",
        "Chelsea", "Crystal Palace", "Everton", "Fulham", "Leeds", "Liverpool",
        "Manchester City", "Manchester United", "Newcastle", "Nottingham Forest",
        "Tottenham", "West Ham", "Wolves"
    ],
    "La Liga": [
        "Athletic Club", "Atletico Madrid", "Barcelona", "Celta Vigo", "Real Madrid",
        "Real Betis", "Real Sociedad", "Sevilla", "Valencia", "Villarreal", "Girona",
        "Rayo Vallecano", "Osasuna", "Alaves", "Getafe", "Espanyol", "Mallorca",
        "Levante", "Elche", "Oviedo"
    ],
    "Serie A": [
        "AC Milan", "Inter", "AS Roma", "Juventus", "Atalanta", "Lazio", "Bologna",
        "Lecce", "Cagliari", "Napoli", "Como", "Parma", "Cremonese", "Pisa",
        "Fiorentina", "Sassuolo", "Genoa", "Torino", "Verona", "Udinese"
    ],
    "Bundesliga": [
        "Bayern München", "Bayer Leverkusen", "Borussia Dortmund", "Eintracht Frankfurt",
        "SC Freiburg", "FSV Mainz 05", "RB Leipzig", "Werder Bremen", "VfB Stuttgart",
        "Borussia Mönchengladbach", "VfL Wolfsburg", "FC Augsburg", "Union Berlin",
        "1899 Hoffenheim", "FC St. Pauli", "1. FC Heidenheim", "1.FC Köln", "Hamburger SV"
    ],
    "Ligue 1": [
        "Paris Saint Germain", "Marseille", "Monaco", "Rennes", "Nice", "Lens", "Lille",
        "Lyon", "Nantes", "Toulouse", "Strasbourg", "Lorient", "Metz", "Le Havre",
        "Stade Brestois 29", "Auxerre", "Paris FC", "Angers"
    ],
    "Eredivisie": [
        "Ajax", "PSV Eindhoven", "Feyenoord", "AZ Alkmaar", "Twente", "Utrecht",
        "Heerenveen", "Sparta Rotterdam", "Fortuna Sittard", "NEC Nijmegen",
        "GO Ahead Eagles", "Excelsior", "PEC Zwolle", "FC Volendam", "Heracles",
        "Groningen", "NAC Breda", "Telstar"
    ]
}

def main():
    with open(TEAMS_FILE, "r") as f:
        teams = json.load(f)

    # Initialize structure
    xg_data = {
        league.lower().replace(" ", "_"): {"for": [], "against": []}
        for league in LEAGUE_MAP.keys()
    }

    for team in teams:
        team_name = team["name"].strip()

        for league, league_teams in LEAGUE_MAP.items():
            if team_name in league_teams:
                league_key = league.lower().replace(" ", "_")
                entry = {
                    "team": team_name,
                    "logo": team.get("logo", ""),
                    "xg_for": "",
                    "xg_against": ""
                }
                xg_data[league_key]["for"].append(entry)
                xg_data[league_key]["against"].append(entry.copy())
                break

    # Sort alphabetically
    for league_key in xg_data:
        xg_data[league_key]["for"].sort(key=lambda x: x["team"])
        xg_data[league_key]["against"].sort(key=lambda x: x["team"])

    # Save file
    with open(OUTPUT_FILE, "w") as f:
        json.dump(xg_data, f, indent=2)

    print("\n✅ xg_stats.json created with 'xg_for' and 'xg_against' fields!\n")
    for league, data in xg_data.items():
        print(f"{league.title().replace('_', ' ')}: {len(data['for'])} teams")

if __name__ == "__main__":
    main()