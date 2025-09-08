import json
from datetime import date, datetime, timedelta

# Show tomorrow's matches (run at 6 PM to prep for next day)
today = date.today() + timedelta(days=1)

# Load selected team IDs
with open("teams.json") as f:
    selected_teams = set(team["id"] for team in json.load(f))

# Load today's fixtures from fixtures.json
with open("fixtures.json") as f:
    fixtures = json.load(f)

matches_today = []

# Filter fixtures for tomorrow and selected teams
for match in fixtures:
    fixture_date = datetime.fromisoformat(match["date"]).date()
    if fixture_date == today:
        if match["home_id"] in selected_teams or match["away_id"] in selected_teams:
            matches_today.append(match)

# Generate HTML
html = """
<html>
<head>
  <title>Projection Cards</title>
  <style>
    body { font-family: Arial, sans-serif; background: #f4f4f4; margin: 0; padding: 20px; }
    h1 { text-align: center; color: #054; }
    .grid { display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; margin-bottom: 40px; }
    .tile {
      background: white;
      padding: 10px 20px;
      border-radius: 12px;
      box-shadow: 0 2px 5px rgba(0,0,0,0.1);
      text-align: center;
      width: 130px;
    }
    .tile img { width: 30px; height: 30px; vertical-align: middle; }
    .tile a { text-decoration: none; color: #0066cc; font-weight: bold; display: block; margin-top: 5px; }

    .card {
      background: white;
      padding: 30px;
      margin: 30px auto;
      max-width: 600px;
      border-radius: 16px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      text-align: center;
    }
    .card img { width: 40px; height: 40px; margin: 0 8px; }
    .card h2 { font-size: 22px; margin: 16px 0; color: #003f2e; }
    .vs-line { font-weight: bold; font-size: 16px; margin-top: 8px; }
  </style>
</head>
<body>
  <h1>Projection Cards</h1>
  <div class="grid">
"""

# Match tiles
for i, match in enumerate(matches_today):
    home = match["home"]
    away = match["away"]
    home_logo = match.get("home_logo", "")
    away_logo = match.get("away_logo", "")
    html += f"""
    <div class="tile">
      <img src="{home_logo}" alt="{home}" /> vs <img src="{away_logo}" alt="{away}" />
      <a href="#card{i}">{home} vs {away}</a>
    </div>
    """

html += "</div>"

# Match cards
for i, match in enumerate(matches_today):
    home = match["home"]
    away = match["away"]
    home_logo = match.get("home_logo", "")
    away_logo = match.get("away_logo", "")
    html += f"""
    <div class="card" id="card{i}">
      <div>
        <img src="{home_logo}" alt="{home}" />
        <img src="{away_logo}" alt="{away}" />
      </div>
      <h2>{home} vs {away}</h2>
      <div class="vs-line">Detailed projection stats go here</div>
    </div>
    """

html += "</body></html>"

# Save to projections.html
with open("projections.html", "w") as f:
    f.write(html)

print(f"✅ Generated {len(matches_today)} match card(s).")



