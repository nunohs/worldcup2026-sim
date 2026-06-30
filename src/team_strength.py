import pandas as pd
from db_connect import get_engine

# Tournaments we consider competitive (no friendlies)
COMPETITIVE = [
    'FIFA World Cup',
    'FIFA World Cup qualification',
    'UEFA Euro',
    'UEFA Euro qualification',
    'Copa América',
    'Africa Cup of Nations',
    'AFC Asian Cup',
    'CONCACAF Gold Cup',
    'UEFA Nations League',
    'CONMEBOL-UEFA Cup of Champions'
]

# Map from group stage names to dataset names
TEAM_NAME_MAP = {
    "USA": "United States",
    "Czechia": "Czech Republic",
}

# Reverse map — dataset name to group stage name
REVERSE_NAME_MAP = {v: k for k, v in TEAM_NAME_MAP.items()}
# Default ratings for teams with insufficient data
DEFAULT_RATINGS = {
    "New Zealand": {
        "matches_played": 0,
        "avg_scored": 0.6,
        "avg_conceded": 1.4,
        "attack_rating": 0.6 / 1.377,
        "defence_rating": 1.4 / 1.377
    }
}

def get_team_rating(team_name, ratings_df):
    """
    Get rating for a team, falling back to default if not in database.
    Also handles name mapping between group stage names and dataset names.
    """
    # Check name map first
    mapped_name = TEAM_NAME_MAP.get(team_name, team_name)
    
    # Look up in ratings dataframe
    row = ratings_df[ratings_df["team"] == mapped_name]
    
    if len(row) > 0:
        return {
            "team": team_name,
            "attack_rating": row.iloc[0]["attack_rating"],
            "defence_rating": row.iloc[0]["defence_rating"]
        }
    
    # Fall back to defaults
    if team_name in DEFAULT_RATINGS:
        pass
        return {"team": team_name, **DEFAULT_RATINGS[team_name]}
    
    # Last resort — truly unknown team gets average ratings
    
    return {
        "team": team_name,
        "attack_rating": 1.0,
        "defence_rating": 1.0
    }

def get_team_ratings():
    engine = get_engine()

    # Pull all competitive matches from 2018 onwards with real scores
    query = """
        SELECT match_date, home_team, away_team, home_score, away_score
        FROM matches
        WHERE match_date >= '2018-01-01'
        AND tournament = ANY(%(tournaments)s)
        AND home_score IS NOT NULL
        AND away_score IS NOT NULL
    """
    df = pd.read_sql(query, engine, params={"tournaments": COMPETITIVE})
    print(f"Loaded {len(df)} competitive matches from 2018 onwards")

    # Build a view where each row is one team's performance in one match
    home = df[["match_date", "home_team", "away_team", "home_score", "away_score"]].copy()
    home.columns = ["match_date", "team", "opponent", "scored", "conceded"]
    home["venue"] = "home"

    away = df[["match_date", "away_team", "home_team", "away_score", "home_score"]].copy()
    away.columns = ["match_date", "team", "opponent", "scored", "conceded"]
    away["venue"] = "away"

    all_matches = pd.concat([home, away], ignore_index=True)

    # Weight recent matches more heavily
    # Matches in the last 2 years get full weight
    # Matches 2-4 years ago get 50% weight
    # Matches 4+ years ago get 25% weight
    latest_date = all_matches["match_date"].max()
    
    def recency_weight(date):
        days_ago = (latest_date - date).days
        if days_ago <= 730:    # last 2 years
            return 1.0
        elif days_ago <= 1460: # 2-4 years ago
            return 0.5
        else:                  # 4+ years ago
            return 0.25

    all_matches["weight"] = all_matches["match_date"].apply(recency_weight)
    all_matches["weighted_scored"] = all_matches["scored"] * all_matches["weight"]
    all_matches["weighted_conceded"] = all_matches["conceded"] * all_matches["weight"]

    # Calculate weighted league averages
    avg_scored = all_matches["weighted_scored"].sum() / all_matches["weight"].sum()
    avg_conceded = all_matches["weighted_conceded"].sum() / all_matches["weight"].sum()

    # Calculate per-team weighted averages
    team_stats = all_matches.groupby("team").apply(
        lambda x: pd.Series({
            "matches_played": len(x),
            "avg_scored": x["weighted_scored"].sum() / x["weight"].sum(),
            "avg_conceded": x["weighted_conceded"].sum() / x["weight"].sum()
        })
    ).reset_index()

    # Only include teams with at least 15 matches
    team_stats = team_stats[team_stats["matches_played"] >= 15]

    # Calculate attack and defence ratings
    # Attack rating > 1 means team scores more than average
    # Defence rating < 1 means team concedes less than average (better defence)
    team_stats["attack_rating"] = team_stats["avg_scored"] / avg_scored
    team_stats["defence_rating"] = team_stats["avg_conceded"] / avg_conceded

    # Sort by attack rating
    team_stats = team_stats.sort_values("attack_rating", ascending=False).reset_index(drop=True)

    # Save to PostgreSQL
    team_stats.to_sql("team_ratings", engine, if_exists="replace", index=False)
    print(f"\nRatings calculated for {len(team_stats)} teams")
    print("\nTop 10 teams by attack rating:")
    print(team_stats[["team", "matches_played", "attack_rating", "defence_rating"]].head(10).to_string(index=False))

    return team_stats

if __name__ == "__main__":
    get_team_ratings()