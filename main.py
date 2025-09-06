import json
from datetime import date

# Load team list
with open("teams.json") as f:
    selected_teams = set(json.load(f))

# Load fixtures
with open("fixtures.json") as f:
    fixtures = json.load(f)

# Filter today's fixtures by selected teams
today = date.today().isoformat()
matches_today = [match for match in fixtures if match["home"] in selected_teams or match["away"] in selected_teams]

# Generate HTML output
html = "<html><head><title>Today’s Projections</title></head><body><h1>Projection Cards</h1>"
for match in matches_today:
    html += f"<div><strong>{match['home']} vs {match['away']}</strong></div>"
html += "</body></html>"

# Save to HTML file
with open("projections.html", "w") as f:
    f.write(html)

print(f"Generated {len(matches_today)} match card(s).")