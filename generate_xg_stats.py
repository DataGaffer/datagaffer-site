import json

# Load all fixtures
with open("fixtures.json", "r") as f:
    fixtures = json.load(f)

# Start HTML structure
html = """
<html>
<head>
  <title>xG Stats</title>
  <style>
    body { font-family: Arial, sans-serif; padding: 20px; background: #f9f9f9; }
    h1 { text-align: center; }
    .buttons { text-align: center; margin-bottom: 20px; }
    .buttons button { margin: 0 10px; padding: 10px 20px; font-size: 16px; cursor: pointer; }
    table { width: 100%; max-width: 900px; margin: auto; border-collapse: collapse; background: white; }
    th, td { padding: 10px; text-align: center; border: 1px solid #ccc; }
    th { background: #222; color: white; }
    img { width: 25px; height: 25px; vertical-align: middle; }
  </style>
</head>
<body>
  <h1>xG, Corners & Shots Stats</h1>

  <div class="buttons">
    <button onclick="showTable('xg')">Expected Goals</button>
    <button onclick="showTable('corners')">Expected Corners</button>
    <button onclick="showTable('shots')">Expected Shots</button>
  </div>

  <div id="xg" class="table-section">
    <table>
      <tr>
        <th></th>
        <th>Home Team</th>
        <th>Home xG</th>
        <th>Total xG</th>
        <th>Away xG</th>
        <th>Away Team</th>
        <th></th>
      </tr>
"""

# Add xG rows from all fixtures
for match in fixtures:
    home = match["home"]
    away = match["away"]
    home_logo = match.get("home_logo", "")
    away_logo = match.get("away_logo", "")
    home_xg = match.get("home_xg", 0)
    away_xg = match.get("away_xg", 0)
    total_xg = round(home_xg + away_xg, 2)

    html += f"""
      <tr>
        <td><img src="{home_logo}" alt="{home}"></td>
        <td>{home}</td>
        <td>{home_xg}</td>
        <td>{total_xg}</td>
        <td>{away_xg}</td>
        <td>{away}</td>
        <td><img src="{away_logo}" alt="{away}"></td>
      </tr>
    """

html += """
    </table>
  </div>

  <div id="corners" class="table-section" style="display:none;">
    <p style="text-align:center;">(Coming soon)</p>
  </div>

  <div id="shots" class="table-section" style="display:none;">
    <p style="text-align:center;">(Coming soon)</p>
  </div>

  <script>
    function showTable(id) {
      document.getElementById('xg').style.display = 'none';
      document.getElementById('corners').style.display = 'none';
      document.getElementById('shots').style.display = 'none';
      document.getElementById(id).style.display = 'block';
    }
  </script>
</body>
</html>
"""

# Save the file
with open("xg_stats.html", "w") as f:
    f.write(html)

print("✅ xG Stats page generated as xg_stats.html")
