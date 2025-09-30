import requests
import json

API_KEY = "3c2b2ba5c3a0ccad7f273e8ca96bba5f"
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

OUTPUT_FILE = "national_teams.json"

TEAM_IDS = [
    25, 773, 771, 1102, 15, 5, 1091, 1111, 21, 1117, 1108, 1100,
    2, 772, 18, 1096, 9, 777, 1104, 1103, 27, 769, 776, 1094,
    1118, 24, 1099, 1097, 775, 774, 1112, 1113, 1106, 1115,
    768, 1090, 1116, 1101, 1114, 1, 767, 16061, 1095, 1107,
    10, 14, 778, 1092, 1110, 3, 770, 1109, 1098, 1093,
    5529, 16, 2384, 26, 6, 12, 17, 2382, 8, 2379, 2380, 2381, 30, 7, 2383
]

COMP_IDS = [5, 13]  # Nations League, WC Qualifiers

def safe_float(val):
    """Convert API string/None to float safely."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return None

def fetch_team_stats(team_id):
    url = f"{BASE_URL}/teams/statistics"
    params = {"team": team_id, "season": 2024, "league": COMP_IDS[0]}
    response = requests.get(url, headers=HEADERS, params=params).json()

    if not response.get("response"):
        params["league"] = COMP_IDS[1]  # fallback
        response = requests.get(url, headers=HEADERS, params=params).json()

    if not response.get("response"):
        print(f"⚠️ No stats for team {team_id}")
        return None

    stats = response["response"]

    # Clean numbers
    gf = safe_float(stats["goals"]["for"]["average"]["total"])
    ga = safe_float(stats["goals"]["against"]["average"]["total"])

    shots = safe_float(stats.get("shots", {}).get("total", {}).get("average"))
    shots_conceded = safe_float(stats.get("shots", {}).get("against", {}).get("average"))
    corners = safe_float(stats.get("corners", {}).get("average"))
    corners_conceded = safe_float(stats.get("corners", {}).get("against", {}).get("average"))

    # Auto-fill if missing
    if shots is None: shots = gf * 10
    if shots_conceded is None: shots_conceded = ga * 10
    if corners is None: corners = gf * 3
    if corners_conceded is None: corners_conceded = ga * 3

    return {
        "id": team_id,
        "league": "National Teams",
        "goals_for": gf,
        "goals_against": ga,
        "shots": round(shots, 2),
        "shots_conceded": round(shots_conceded, 2),
        "corners": round(corners, 2),
        "corners_conceded": round(corners_conceded, 2)
    }

def main():
    results = []
    for tid in TEAM_IDS:
        print(f"Fetching {tid}...")
        stats = fetch_team_stats(tid)
        if stats:
            results.append(stats)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print(f"✅ Saved {len(results)} national teams to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()