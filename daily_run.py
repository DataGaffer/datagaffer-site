import os
import subprocess

# Step 1: Run fetch_fixtures.py to get today's games
print("🔄 Fetching today's fixtures...")
subprocess.run(["python3", "fetch_fixtures.py"])

# Step 2: Run main.py to generate index.html with match projections
print("⚙️ Generating updated projection cards...")
subprocess.run(["python3", "main.py"])

# Step 3: Git add, commit, and push the updated index.html
print("📦 Committing updated index.html to GitHub...")
subprocess.run(["git", "add", "index.html"])
subprocess.run(["git", "commit", "-m", "🔁 Daily auto-update of projection cards"])
subprocess.run(["git", "push"])
