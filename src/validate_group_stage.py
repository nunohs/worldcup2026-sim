import pandas as pd
import numpy as np
from scipy.stats import poisson
from db_connect import get_engine
from team_strength import get_team_ratings, get_team_rating, TEAM_NAME_MAP

# All 12 groups with exact team names matching our database
GROUPS = {
    'A': ['Mexico', 'South Korea', 'South Africa', 'Czech Republic'],
    'B': ['Canada', 'Switzerland', 'Bosnia and Herzegovina', 'Qatar'],
    'C': ['Brazil', 'Morocco', 'Scotland', 'Haiti'],
    'D': ['United States', 'Turkey', 'Australia', 'Paraguay'],
    'E': ['Germany', 'Ivory Coast', 'Ecuador', 'Curaçao'],
    'F': ['Netherlands', 'Japan', 'Sweden', 'Tunisia'],
    'G': ['Belgium', 'Egypt', 'Iran', 'New Zealand'],
    'H': ['Spain', 'Uruguay', 'Saudi Arabia', 'Cape Verde'],
    'I': ['France', 'Senegal', 'Norway', 'Iraq'],
    'J': ['Argentina', 'Austria', 'Algeria', 'Jordan'],
    'K': ['Portugal', 'Colombia', 'DR Congo', 'Uzbekistan'],
    'L': ['England', 'Croatia', 'Ghana', 'Panama'],
}

ACTUAL_RESULTS = {
    'A': {'1st': 'Mexico',         '2nd': 'South Africa'},
    'B': {'1st': 'Switzerland',    '2nd': 'Canada'},
    'C': {'1st': 'Brazil',         '2nd': 'Morocco'},
    'D': {'1st': 'United States',  '2nd': 'Australia'},
    'E': {'1st': 'Germany',        '2nd': 'Ivory Coast'},
    'F': {'1st': 'Netherlands',    '2nd': 'Japan'},
    'G': {'1st': 'Belgium',        '2nd': 'Egypt'},
    'H': {'1st': 'Spain',          '2nd': 'Cape Verde'},
    'I': {'1st': 'France',         '2nd': 'Norway'},
    'J': {'1st': 'Argentina',      '2nd': 'Austria'},
    'K': {'1st': 'Colombia',       '2nd': 'Portugal'},
    'L': {'1st': 'England',        '2nd': 'Croatia'},
}

def simulate_match(team_a, team_b, ratings_df, n_sims=10000):
    """Simulate a match n times, return win probabilities"""
    rating_a = get_team_rating(team_a, ratings_df)
    rating_b = get_team_rating(team_b, ratings_df)

    # Base rate - average goals per match
    base_rate = 1.377

    # Expected goals for each team
    exp_goals_a = base_rate * rating_a['attack_rating'] * rating_b['defence_rating']
    exp_goals_b = base_rate * rating_b['attack_rating'] * rating_a['defence_rating']

    # Draw goals from Poisson distribution
    goals_a = poisson.rvs(exp_goals_a, size=n_sims)
    goals_b = poisson.rvs(exp_goals_b, size=n_sims)

    wins_a = np.sum(goals_a > goals_b) / n_sims
    draws = np.sum(goals_a == goals_b) / n_sims
    wins_b = np.sum(goals_b > goals_a) / n_sims

    return {
        'exp_goals_a': round(exp_goals_a, 2),
        'exp_goals_b': round(exp_goals_b, 2),
        'win_prob_a': round(wins_a, 3),
        'draw_prob': round(draws, 3),
        'win_prob_b': round(wins_b, 3),
    }

def simulate_group(group_name, teams, ratings_df, n_sims=10000):
    """Simulate a full group n times, return average finish probabilities"""
    finish_counts = {team: {1: 0, 2: 0, 3: 0, 4: 0} for team in teams}

    for _ in range(n_sims):
        points = {team: 0 for team in teams}
        gd = {team: 0 for team in teams}
        gs = {team: 0 for team in teams}

        # Play all 6 matches
        for i in range(len(teams)):
            for j in range(i+1, len(teams)):
                team_a = teams[i]
                team_b = teams[j]
                rating_a = get_team_rating(team_a, ratings_df)
                rating_b = get_team_rating(team_b, ratings_df)

                base_rate = 1.377
                exp_a = base_rate * rating_a['attack_rating'] * rating_b['defence_rating']
                exp_b = base_rate * rating_b['attack_rating'] * rating_a['defence_rating']

                g_a = poisson.rvs(exp_a)
                g_b = poisson.rvs(exp_b)

                # Update points
                if g_a > g_b:
                    points[team_a] += 3
                elif g_b > g_a:
                    points[team_b] += 3
                else:
                    points[team_a] += 1
                    points[team_b] += 1

                # Update goal difference and goals scored
                gd[team_a] += g_a - g_b
                gd[team_b] += g_b - g_a
                gs[team_a] += g_a
                gs[team_b] += g_b

        # Rank teams by points, then GD, then GS
        standings = sorted(teams,
            key=lambda t: (points[t], gd[t], gs[t]),
            reverse=True)

        for pos, team in enumerate(standings, 1):
            finish_counts[team][pos] += 1

    # Convert to probabilities
    results = []
    for team in teams:
        results.append({
            'team': team,
            '1st_%': round(finish_counts[team][1] / n_sims * 100, 1),
            '2nd_%': round(finish_counts[team][2] / n_sims * 100, 1),
            '3rd_%': round(finish_counts[team][3] / n_sims * 100, 1),
            '4th_%': round(finish_counts[team][4] / n_sims * 100, 1),
        })

    return sorted(results, key=lambda x: x['1st_%'], reverse=True)

def validate():
    ratings_df = get_team_ratings()
    print("\n" + "="*70)
    print("GROUP STAGE VALIDATION")
    print("="*70)

    correct_top2 = 0
    total_top2 = 0
    correct_winner = 0

    for group, teams in GROUPS.items():
        print(f"\nGROUP {group}: {' | '.join(teams)}")
        print("-"*50)

        results = simulate_group(group, teams, ratings_df, n_sims=5000)

        # Print predictions
        print(f"{'Team':<30} {'1st%':>6} {'2nd%':>6} {'3rd%':>6} {'4th%':>6}")
        for r in results:
            print(f"{r['team']:<30} {r['1st_%']:>6} {r['2nd_%']:>6} {r['3rd_%']:>6} {r['4th_%']:>6}")

        # Compare to actual
        actual_1st = ACTUAL_RESULTS[group]['1st']
        actual_2nd = ACTUAL_RESULTS[group]['2nd']
        predicted_top2 = [r['team'] for r in results[:2]]
        predicted_winner = results[0]['team']

        print(f"\nActual:    1st={actual_1st}, 2nd={actual_2nd}")
        print(f"Predicted: 1st={predicted_winner}, Top2={predicted_top2}")

        # Score it
        actual_top2 = {actual_1st, actual_2nd}
        if actual_1st == predicted_winner:
            correct_winner += 1
            print("✓ Correct winner!")
        if actual_top2 == set(predicted_top2):
            correct_top2 += 1
            print("✓ Correct top 2!")
        total_top2 += 1

    print("\n" + "="*70)
    print(f"FINAL SCORE")
    print(f"Correct winners predicted: {correct_winner}/12 ({correct_winner/12*100:.0f}%)")
    print(f"Correct top 2 predicted:   {correct_top2}/12 ({correct_top2/12*100:.0f}%)")
    print("="*70)

if __name__ == "__main__":
    validate()