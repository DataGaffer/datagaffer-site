# dg_ratings.py
import json, os
from typing import Optional

# ============================================================
# ✅ Safe JSON loader
# ============================================================
def load_json(path, default=None):
    if default is None:
        default = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read().strip()
            if not text:
                return default
            return json.loads(text)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


# ============================================================
# ✅ CONFIG PATHS
# ============================================================
LEAGUE_COEFS_FILE  = "league_ratings.json"
TEAMS_FILE         = "teams.json"
XG_FILE            = "xg_stats.json"
TEAM_STATS_DIR     = "team_stats"
API2025_DIR        = "team_stats_api/2025"
EURO2025_DIR       = "team_stats_api/europe_2025"
TEAM_BOOSTERS_FILE = "team_boosters.json"
LEAGUE_ID_MAP_FILE = "league_ids.json"
OUTPUT_FILE        = "dg_ratings.json"


# ============================================================
# ✅ Load main inputs
# ============================================================
league_coefs  = load_json(LEAGUE_COEFS_FILE, {})
teams         = load_json(TEAMS_FILE, [])
xg_all        = load_json(XG_FILE, {})
team_boosters = load_json(TEAM_BOOSTERS_FILE, {})

league_id_map_raw = load_json(LEAGUE_ID_MAP_FILE, {})
league_by_id = {int(v): k for k, v in league_id_map_raw.items()}


# ============================================================
# ✅ Helpers
# ============================================================
def norm_name(s: str) -> str:
    return "".join(ch for ch in (s or "").lower() if ch.isalnum())

def safe_float(x, default=0.0):
    try:
        return float(x)
    except:
        return default

def per_match_from_api_block(block: dict):
    m  = float(block.get("matches") or 0)
    gf = float(block.get("goals_for") or 0)
    ga = float(block.get("goals_against") or 0)
    m = max(m, 1.0)
    return gf / m, ga / m


# ============================================================
# ✅ Load Domestic API Stats (2025)
# ============================================================
def read_api_2025(dir_path: str):
    out = {}
    if not os.path.isdir(dir_path):
        return out

    for fname in os.listdir(dir_path):
        if not fname.endswith(".json"):
            continue
        data = load_json(os.path.join(dir_path, fname), {})

        tid = data.get("team_id")
        league_id = data.get("league_id")

        if tid is None:
            continue

        home_gf, home_ga = per_match_from_api_block(data.get("home", {}))
        away_gf, away_ga = per_match_from_api_block(data.get("away", {}))

        out[str(tid)] = {
            "gf": (data["home"]["goals_for"] + data["away"]["goals_for"]),
            "ga": (data["home"]["goals_against"] + data["away"]["goals_against"]),
            "matches": (data["home"]["matches"] + data["away"]["matches"]),
            "league": league_by_id.get(league_id, "Unknown")
        }

    return out

api_2025 = read_api_2025(API2025_DIR)


# ============================================================
# ✅ Load European Stats (UCL/UEL)
# ============================================================
def read_europe_2025(dir_path: str):
    out = {}
    if not os.path.isdir(dir_path):
        return out

    for fname in os.listdir(dir_path):
        if not fname.endswith(".json"):
            continue

        data = load_json(os.path.join(dir_path, fname), {})
        tid = str(data.get("team_id"))
        if not tid:
            continue

        matches_home = data.get("home", {}).get("matches", 0)
        matches_away = data.get("away", {}).get("matches", 0)

        total_gf = data.get("home", {}).get("goals_for", 0) + data.get("away", {}).get("goals_for", 0)
        total_ga = data.get("home", {}).get("goals_against", 0) + data.get("away", {}).get("goals_against", 0)

        out[tid] = {
            "matches": matches_home + matches_away,
            "gf": total_gf,
            "ga": total_ga
        }

    return out

europe_2025 = read_europe_2025(EURO2025_DIR)


# ============================================================
# ✅ Manual Fallback Stats
# ============================================================
manual_stats = {}
if os.path.isdir(TEAM_STATS_DIR):
    for fname in os.listdir(TEAM_STATS_DIR):
        if fname.endswith(".json"):
            arr = load_json(os.path.join(TEAM_STATS_DIR, fname), [])
            if isinstance(arr, list):
                for t in arr:
                    tid = t.get("id")
                    if tid is not None:
                        manual_stats[str(tid)] = t

def manual_fallback_gf_ga(team_row):
    if "home" in team_row and "away" in team_row:
        gf = (safe_float(team_row["home"].get("goals_for")) +
              safe_float(team_row["away"].get("goals_for"))) / 2
        ga = (safe_float(team_row["home"].get("goals_against")) +
              safe_float(team_row["away"].get("goals_against"))) / 2
    else:
        gf = safe_float(team_row.get("scored"))
        ga = safe_float(team_row.get("conceded"))
    return gf, ga


# ============================================================
# ✅ XG Lookup (for luck only — NOT used in ratings)
# ============================================================
xg_lookup = {}

for key, section in xg_all.items():
    if isinstance(section, dict) and "for" in section:
        for t in section["for"]:
            nm = norm_name(t.get("team"))
            xg_lookup[nm] = {
                "xgf": safe_float(t.get("xg_for")),
                "xga": safe_float(t.get("xg_against"))
            }


# ============================================================
# ✅ Compute Rating
# ============================================================
def compute_team_rating(team):
    tid = str(team.get("id"))
    name = team.get("name")

    league = api_2025.get(tid, {}).get("league") or team.get("league", "Unknown")
    coef = float(league_coefs.get(league, 1.0))

    # --------------------------
    # ✅ Domestic stats
    # --------------------------
    dom = api_2025.get(tid, {})
    dom_matches = dom.get("matches", 0)
    dom_gf = dom.get("gf", 0)
    dom_ga = dom.get("ga", 0)

    # --------------------------
    # ✅ Europe stats
    # --------------------------
    eu = europe_2025.get(tid, {})
    eu_matches = eu.get("matches", 0)
    eu_gf = eu.get("gf", 0)
    eu_ga = eu.get("ga", 0)

    # --------------------------
    # ✅ Weighted 80% Domestic, 20% Europe
    # --------------------------
    if dom_matches > 0:
        dom_gf_per = dom_gf / dom_matches
        dom_ga_per = dom_ga / dom_matches
    else:
        dom_gf_per = dom_ga_per = 0

    if eu_matches > 0:
        eu_gf_per = eu_gf / eu_matches
        eu_ga_per = eu_ga / eu_matches
    else:
        eu_gf_per = eu_ga_per = 0

    # ✅ FINAL GF/GA per match
    if dom_matches > 0 and eu_matches > 0:
        gf = 0.80 * dom_gf_per + 0.20 * eu_gf_per
        ga = 0.80 * dom_ga_per + 0.20 * eu_ga_per
    else:
        # If no Europe stats, 100% domestic
        gf = dom_gf_per
        ga = dom_ga_per

    # --------------------------
    # ✅ xG (luck only)
    # --------------------------
    xr = xg_lookup.get(norm_name(name), {})
    xgf = safe_float(xr.get("xgf"), gf)
    xga = safe_float(xr.get("xga"), ga)

    # --------------------------
    # ✅ Real-world ratings
    # --------------------------
    ORtg = gf * coef
    DRtg = ga / max(coef, 1e-9)
    DGR  = ORtg - DRtg

    # --------------------------
    # ✅ Booster
    # --------------------------
    booster = float(team_boosters.get(tid, 1.0))
    ORtg_b = ORtg * booster
    DRtg_b = DRtg / max(booster, 1e-9)
    DGR_b  = ORtg_b - DRtg_b

    # --------------------------
    # ✅ Luck
    # --------------------------
    luck_off = gf - xgf
    luck_def = xga - ga

    return {
        "team": name,
        "league": league,
        "coef": round(coef, 3),

        "ORtg": round(ORtg_b, 3),
        "DRtg": round(DRtg_b, 3),
        "DGRtg": round(DGR_b, 3),

        "gf_per": round(gf, 3),
        "ga_per": round(ga, 3),

        "xgf": round(xgf, 3),
        "xga": round(xga, 3),

        "luck_offense": round(luck_off, 3),
        "luck_defense": round(luck_def, 3),

        "bad_luck_offense": round(xgf - gf, 3),
        "bad_luck_defense": round(ga - xga, 3),

        "booster": booster
    }


# ============================================================
# ✅ Build full table
# ============================================================
rows = []

for t in teams:
    try:
        rows.append(compute_team_rating(t))
    except Exception as e:
        rows.append({
            "team": t.get("name"),
            "league": t.get("league", ""),
            "error": str(e)
        })

rows = sorted(rows, key=lambda r: r.get("DGRtg", -9999), reverse=True)

for i, r in enumerate(rows, start=1):
    r["rank"] = i


with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(rows, f, indent=2)

print(f"✅ Wrote {len(rows)} teams → {OUTPUT_FILE}")
for r in rows[:10]:
    print(f"{r['rank']:>2}. {r['team']:<25}  DGR={r['DGRtg']}  OR={r['ORtg']}  DR={r['DRtg']} coef={r['coef']}")