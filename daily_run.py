import subprocess
import sys
from datetime import datetime

LOG_FILE = "daily_log.txt"

def log(message):
    """Append timestamped message to daily_log.txt and print it."""
    timestamp = datetime.utcnow().strftime("[%Y-%m-%d %H:%M:%S UTC]")
    line = f"{timestamp} {message}\n"
    print(line.strip())
    with open(LOG_FILE, "a") as f:
        f.write(line)

def run_script(script):
    log(f"▶️ Running {script} ...")
    try:
        subprocess.run([sys.executable, script], check=True)
        log(f"✅ {script} completed successfully.")
    except subprocess.CalledProcessError as e:
        log(f"❌ {script} failed: {e}")
        sys.exit(1)

def main():
    log("🚀 Starting daily run...")

    # Step 1: Fetch fixtures + simulations (xG, corners, shots)
    run_script("fetch_fixtures.py")

    # Step 2: Generate Sim Cards
    run_script("sim_cards.py")

    log("🎉 Daily run finished — fixtures.json and sim_cards.json updated.\n")

if __name__ == "__main__":
    main()
