import json, requests, time

API_KEY = "3c2b2ba5c3a0ccad7f273e8ca96bba5f"
FIXTURES_FILE = "fixtures.json"
H2H_FILE = "h2h_and_odds.json"
OUTPUT_FILE = "h2h_form_combined.json"

headers = {"x-apisports-key": API_KEY}

def get_form_stats(team_id):
    """Fetch last 5 matches and compute form string, total points, and avg goals."""
    url = f"https://v3.football.api-sports.io/fixtures?team={team_id}&last=5&status=FT"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json().get("response", [])
        if not data:
            return {"points": 0, "avg_goals": 0, "form": "-----"}

        total_points = 0
        total_goals = 0
        form_str = ""

        for match in data:
            home_id = match["teams"]["home"]["id"]
            away_id = match["teams"]["away"]["id"]
            home_goals = match["goals"]["home"] or 0
            away_goals = match["goals"]["away"] or 0

            # Determine team perspective
            if team_id == home_id:
                scored, conceded = home_goals, away_goals
            else:
                scored, conceded = away_goals, home_goals

            total_goals += scored
            if scored > conceded:
                total_points += 3
                form_str += "W"
            elif scored == conceded:
                total_points += 1
                form_str += "D"
            else:
                form_str += "L"

        avg_goals = round(total_goals / len(data), 2)
        return {"points": total_points, "avg_goals": avg_goals, "form": form_str}

    except Exception as e:
        print(f"⚠️ Error fetching form for team {team_id}: {e}")
        return {"points": 0, "avg_goals": 0, "form": "-----"}


def main():
    with open(FIXTURES_FILE, "r") as f:
        fixtures = json.load(f)
    with open(H2H_FILE, "r") as f:
        h2h_data = json.load(f)

    combined = []

    for fx in fixtures:
        home = fx["home"]
        away = fx["away"]
        home_id = home["id"]
        away_id = away["id"]

        # Match existing H2H entry
        key = f"home_{home_id}_{away_id}"
        h2h = h2h_data.get(key) or h2h_data.get(f"home_{away_id}_{home_id}", {})

        # Get last 5 form for both teams
        home_form = get_form_stats(home_id)
        time.sleep(0.4)
        away_form = get_form_stats(away_id)
        time.sleep(0.4)

        combined.append({
            "matchup": f"{home['name']} vs {away['name']}",
            "home_logo": home["logo"],
            "away_logo": away["logo"],
            "h2h_home_avg_goals": h2h.get("avg_home", 0),
            "h2h_away_avg_goals": h2h.get("avg_away", 0),
            "h2h_total_avg": round(
                (h2h.get("avg_home", 0) or 0) + (h2h.get("avg_away", 0) or 0), 2
            ),
            "home_form_points": home_form["points"],
            "away_form_points": away_form["points"],
            "home_form_goals": home_form["avg_goals"],
            "away_form_goals": away_form["avg_goals"],
            "home_form_last5": home_form["form"],
            "away_form_last5": away_form["form"]
        })
        print(f"✅ Processed {home['name']} vs {away['name']}")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(combined, f, indent=2)

    print(f"\n✅ Saved {len(combined)} matchups to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()