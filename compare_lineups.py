import requests
from bs4 import BeautifulSoup
import difflib
from predict_lineup import predict_best_lineup
import os
import json
import unicodedata
import re
from urllib.parse import quote_plus

# ---------- Name Helpers ----------

def normalize_name(name):
    """Normalize and clean player names for fuzzy matching."""
    name = unicodedata.normalize("NFD", name)
    name = name.encode("ascii", "ignore").decode("utf-8")  # remove accents
    name = re.sub(r"[^a-zA-Z\s]", "", name)  # remove punctuation
    return name.lower().strip()

def compare_names(n1, n2):
    """Flexible name comparison (fuzzy + partial)."""
    n1n, n2n = normalize_name(n1), normalize_name(n2)
    ratio = difflib.SequenceMatcher(None, n1n, n2n).ratio()
    return ratio >= 0.6 or (n1n.split()[-1] in n2n)

# ---------- SportsMole Scraping ----------

def get_preview_page(home_team, away_team):
    """
    Search Google for the correct SportsMole preview page
    instead of using SportsMole's internal JS search.
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    query = f"site:sportsmole.co.uk {home_team} vs {away_team} prediction team news lineups"
    google_url = f"https://www.google.com/search?q={quote_plus(query)}"
    print(f"🔍 Google search for: {home_team} vs {away_team}")

    res = requests.get(google_url, headers=headers, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")

    preview_url = None
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # Google wraps URLs like "/url?q=<actual_link>&sa=..."
        if href.startswith("/url?q=") and "sportsmole.co.uk" in href:
            link = href.split("/url?q=")[1].split("&")[0]
            if "prediction-team-news-lineups" in link:
                preview_url = link
                break

    if preview_url:
        print(f"✅ Found preview: {preview_url}")
        return preview_url
    else:
        print(f"⚠️ No preview link found for {home_team} vs {away_team}")
        return None


def get_sportsmole_lineup(preview_url, team_name):
    """Extract 'possible starting lineup' section directly from SportsMole HTML."""
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(preview_url, headers=headers, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")

    players = []

    # Scan for bold tags mentioning "possible starting lineup"
    for tag in soup.find_all(["strong", "b"]):
        text = tag.get_text(" ", strip=True).lower()
        if team_name.lower() in text and "possible starting lineup" in text:
            print(f"\n=== Found lineup header for {team_name} ===")
            print(tag.get_text(strip=True))

            # Check up to 5 next siblings (handles p/div/br)
            next_elem = tag.find_parent().find_next_sibling()
            attempts = 0
            while next_elem and attempts < 5:
                next_text = next_elem.get_text(" ", strip=True) if hasattr(next_elem, "get_text") else ""
                if len(next_text) > 10 and (";" in next_text or "," in next_text):
                    print("\n🧩 Raw lineup text block:")
                    print(next_text)
                    raw_names = re.split(r"[;,]", next_text)
                    for n in raw_names:
                        n = n.strip()
                        if 1 < len(n) < 30:
                            players.append(n)
                    break
                next_elem = next_elem.find_next_sibling()
                attempts += 1
            break

    print(f"\n✅ Extracted players for {team_name}: {players}")
    return players[:11]


# ---------- Lineup Comparison ----------

def compare_lineups(team_file, team_name, preview_url):
    """Compare predicted vs simulated best lineup."""
    best_lineup = predict_best_lineup(team_file)
    best_players = [p["name"] for group in best_lineup.values() for p in group]

    sportsmole_players = get_sportsmole_lineup(preview_url, team_name)
    if not sportsmole_players:
        print(f"⚠️ Could not extract lineup for {team_name}")
        return 1.0  # assume full strength if missing

    matches = 0
    for best in best_players:
        for actual in sportsmole_players:
            if compare_names(best, actual):
                matches += 1
                break

    strength_ratio = round(matches / 11, 2)
    print(f"✅ {team_name}: {matches}/11 best players starting → Strength Ratio: {strength_ratio}")
    return strength_ratio


# ---------- Main ----------

if __name__ == "__main__":
    fixtures_path = "fixtures.json"
    if not os.path.exists(fixtures_path):
        print("⚠️ fixtures.json not found. Run fetch_fixtures.py first.")
        exit()

    with open(fixtures_path, "r") as f:
        fixtures = json.load(f)

    lineup_strengths = {}

    for fixture in fixtures:
        home_team = fixture["home"]["name"]
        away_team = fixture["away"]["name"]
        preview_url = get_preview_page(home_team, away_team)
        if not preview_url:
            continue

        for side in ["home", "away"]:
            team_name = fixture[side]["name"]
            team_id = fixture[side]["id"]
            safe_name = team_name.replace(" ", "_")
            team_file = os.path.join("players", f"{safe_name}.json")

            if not os.path.exists(team_file):
                print(f"⚠️ Missing player file for {team_name}")
                continue

            strength = compare_lineups(team_file, team_name, preview_url)
            lineup_strengths[str(team_id)] = strength

    with open("lineup_strength.json", "w") as f:
        json.dump(lineup_strengths, f, indent=2)

    print("\n💾 Saved lineup_strength.json successfully!")