import requests
from bs4 import BeautifulSoup
import re

def get_sportsmole_lineup(url, team_name):
    """Extract possible starting lineup for a given team from a SportsMole preview."""
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")

    players = []

    # Find the bold text that mentions the lineup
    for tag in soup.find_all(["strong", "b"]):
        text = tag.get_text(" ", strip=True).lower()
        if team_name.lower() in text and "possible starting lineup" in text:
            print(f"\n=== Found lineup header for {team_name} ===")
            print(tag.get_text(strip=True))

            # Check multiple possible next elements (p, div, br)
            next_elem = tag.find_parent().find_next_sibling()
            attempts = 0
            while next_elem and attempts < 5:
                next_text = next_elem.get_text(" ", strip=True) if hasattr(next_elem, "get_text") else ""
                if len(next_text) > 10 and (";" in next_text or "," in next_text):
                    print("\n🧩 Raw lineup text block:")
                    print(next_text)

                    # Split by semicolons or commas
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


if __name__ == "__main__":
    url = "https://www.sportsmole.co.uk/football/chelsea/league-cup/preview/wolves-vs-chelsea-prediction-team-news-lineups_584497.html"
    get_sportsmole_lineup(url, "Chelsea")