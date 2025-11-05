import json, os
from typing import Optional

# ============================================================
# ✅ Safe JSON loader (ALWAYS returns a dictionary or list)
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
# ✅ CONFIG FILE PATHS
# ============================================================
LEAGUE_COEFS_FILE  = "league_ratings.json"
TEAMS_FILE         = "teams.json"
XG_FILE            = "xg_stats.json"
TEAM_STATS_DIR     = "team_stats"
API2025_DIR        = "team_stats_api/2025"
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

# ------------------------------------------------------------
# ✅ Load league_id → league_name map
# ------------------------------------------------------------
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
# ✅ Build API (2025-only) GF/GA Lookup
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
            "home_gf": home_gf,
            "home_ga": home_ga,
            "away_gf": away_gf,
            "away_ga": away_ga,
            "league": league_by_id.get(league_id, "Unknown")
        }

    return out


api_2025 = read_api_2025(API2025_DIR)


def api_gf_ga_2025(team_id: str):
    row = api_2025.get(team_id)
    if not row:
        return 0.0, 0.0
    gf = (row["home_gf"] + row["away_gf"]) / 2
    ga = (row["home_ga"] + row["away_ga"]) / 2
    return gf, ga


# ============================================================
# ✅ Manual Stats Lookup
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
# ✅ Build XG lookup table
# ============================================================
xg_lookup = {}

for key, section in xg_all.items():
    if isinstance(section, dict) and "for" in section:
        for t in section["for"]:
            nm = norm_name(t.get("team"))
            if not nm:
                continue
            xg_lookup[nm] = {
                "xgf": safe_float(t.get("xg_for")),
                "xga": safe_float(t.get("xg_against"))
            }


# ============================================================
# ✅ Compute Rating for One Team
# ============================================================
def compute_team_rating(team):
    tid = str(team.get("id"))
    name = team.get("name") or team.get("team") or ""

    # League detection
    league = api_2025.get(tid, {}).get("league") or team.get("league", "Unknown")
    coef = float(league_coefs.get(league, 1.0))

    # GF/GA (2025-only)
    gf, ga = api_gf_ga_2025(tid)

    if gf == 0 and ga == 0:
        mrow = manual_stats.get(tid)
        if mrow:
            gf, ga = manual_fallback_gf_ga(mrow)

    # Expected xG
    xg_row = xg_lookup.get(norm_name(name), {})
    # Expected xG still loaded for luck metrics,
# but NOT used in core ratings.
    xgf = safe_float(xg_row.get("xgf"), gf)
    xga = safe_float(xg_row.get("xga"), ga)

# ✅ REAL-WORLD RATINGS (NO xG)
    offR = gf          # use ACTUAL scoring only
    defR = ga          # use ACTUAL defending only

    ORtg = offR * coef
    DRtg = defR / max(coef, 1e-9)
    DGR  = ORtg - DRtg

    # ✅ Apply booster multiplier
    booster = float(team_boosters.get(tid, 1.0))
    
    ORtg_b = ORtg * booster
    DRtg_b = DRtg / max(booster, 1e-9)
    DGR_b  = ORtg_b - DRtg_b

    # Luck metrics (negative values allowed)
    luck_off = gf - xgf
    luck_def = xga - ga
    bad_off  = xgf - gf
    bad_def  = ga - xga

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
        "bad_luck_offense": round(bad_off, 3),
        "bad_luck_defense": round(bad_def, 3),

        "booster": booster
    }




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
    json.dump(rows, f, ensure_ascii=False, indent=2)

print(f"✅ Wrote {len(rows)} teams → {OUTPUT_FILE}")
for r in rows[:10]:
    print(f"{r['rank']:>2}. {r['team']:<25}  DGR={r['DGRtg']}  OR={r['ORtg']}  DR={r['DRtg']}  coef={r['coef']} booster={r['booster']}")