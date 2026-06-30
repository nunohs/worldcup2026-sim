import pandas as pd
import numpy as np
from db_connect import get_engine

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

TEAM_NAME_MAP = {
    "USA": "United States",
    "Czechia": "Czech Republic",
}

DEFAULT_RATINGS = {
    "New Zealand": {
        "matches_played": 0,
        "attack_rating": 0.6 / 1.377,
        "defence_rating": 1 / 1.377
    }
}

def load_match_data():
    """Load and prepare match data, return long-format dataframe (one row per team per match)"""
    engine = get_engine()
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

    home = df[["match_date", "home_team", "away_team", "home_score", "away_score"]].copy()
    home.columns = ["match_date", "team", "opponent", "scored", "conceded"]

    away = df[["match_date", "away_team", "home_team", "away_score", "home_score"]].copy()
    away.columns = ["match_date", "team", "opponent", "scored", "conceded"]

    all_matches = pd.concat([home, away], ignore_index=True)

    # Recency weighting
    latest_date = all_matches["match_date"].max()
    def recency_weight(date):
        days_ago = (latest_date - date).days
        if days_ago <= 730:
            return 1.0
        elif days_ago <= 1460:
            return 0.5
        else:
            return 0.25
    all_matches["recency_weight"] = all_matches["match_date"].apply(recency_weight)

    return all_matches


def calculate_iterative_ratings(all_matches, n_iterations=8, min_matches=15):
    """
    Calculate attack/defence ratings using iterative opponent-strength weighting.
    Each round, a team's rating is recalculated using the opponent's rating from
    the previous round - so beating a strong team counts more than beating a weak one.
    """
    teams = all_matches["team"].unique()

    # Filter to teams with enough matches
    match_counts = all_matches.groupby("team").size()
    valid_teams = match_counts[match_counts >= min_matches].index.tolist()
    all_matches = all_matches[
        all_matches["team"].isin(valid_teams) & all_matches["opponent"].isin(valid_teams)
    ].copy()

    print(f"Teams with sufficient data: {len(valid_teams)}")

    # Initialize all teams at neutral rating (1.0 attack, 1.0 defence)
    ratings = {team: {"attack": 1.0, "defence": 1.0} for team in valid_teams}

    league_avg_goals = (all_matches["scored"] * all_matches["recency_weight"]).sum() / all_matches["recency_weight"].sum()

    for iteration in range(n_iterations):
        new_ratings = {}

        for team in valid_teams:
            team_matches = all_matches[all_matches["team"] == team]
            if len(team_matches) == 0:
                new_ratings[team] = ratings[team]
                continue

            # Opponent strength multiplier: stronger opponent defence = goal counts for more
            # We use the opponent's CURRENT (previous iteration) defence rating
            opp_defence = team_matches["opponent"].map(lambda o: ratings.get(o, {"defence": 1.0})["defence"])
            opp_attack = team_matches["opponent"].map(lambda o: ratings.get(o, {"attack": 1.0})["attack"])

            weights = team_matches["recency_weight"]

            # Attack rating: goals scored, weighted up if opponent has strong (low) defence rating
            # A low defence_rating means hard to score against, so scoring there is impressive
            # We divide by opponent defence rating - scoring 2 vs a defence rating of 0.5 (elite) counts double
            adjusted_scored = team_matches["scored"] / opp_defence.replace(0, 0.1)
            attack_rating = (adjusted_scored * weights).sum() / weights.sum() / league_avg_goals

            # Defence rating: goals conceded, weighted up if opponent has strong (high) attack rating
            # Conceding 2 to a weak attack (rating 0.5) is worse than conceding 2 to a strong attack (rating 2.0)
            adjusted_conceded = team_matches["conceded"] / opp_attack.replace(0, 0.1)
            defence_rating = (adjusted_conceded * weights).sum() / weights.sum() / league_avg_goals

            new_ratings[team] = {"attack": attack_rating, "defence": defence_rating}

        ratings = new_ratings
        print(f"Iteration {iteration + 1}/{n_iterations} complete")

    return ratings


def get_team_ratings():
    """Main entry point - returns a dataframe of team, attack_rating, defence_rating"""
    all_matches = load_match_data()
    ratings = calculate_iterative_ratings(all_matches)

    rows = []
    match_counts = all_matches.groupby("team").size().to_dict()
    for team, r in ratings.items():
        rows.append({
            "team": team,
            "matches_played": match_counts.get(team, 0),
            "attack_rating": r["attack"],
            "defence_rating": r["defence"]
        })

    team_stats = pd.DataFrame(rows).sort_values("attack_rating", ascending=False).reset_index(drop=True)

    engine = get_engine()
    team_stats.to_sql("team_ratings", engine, if_exists="replace", index=False)

    print(f"\nIterative ratings calculated for {len(team_stats)} teams")
    print("\nTop 15 teams by attack rating:")
    print(team_stats[["team", "matches_played", "attack_rating", "defence_rating"]].head(15).to_string(index=False))

    return team_stats


def get_team_rating(team_name, ratings_df):
    """Get rating for a team, with name mapping and defaults for missing teams"""
    mapped_name = TEAM_NAME_MAP.get(team_name, team_name)
    row = ratings_df[ratings_df["team"] == mapped_name]

    if len(row) > 0:
        return {
            "team": team_name,
            "attack_rating": row.iloc[0]["attack_rating"],
            "defence_rating": row.iloc[0]["defence_rating"]
        }

    if team_name in DEFAULT_RATINGS:
        return {"team": team_name, **DEFAULT_RATINGS[team_name]}

    return {"team": team_name, "attack_rating": 1.0, "defence_rating": 1.0}


if __name__ == "__main__":
    get_team_ratings()