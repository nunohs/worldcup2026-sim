import pandas as pd
from db_connect import get_engine

def load_csv_to_db():
    engine = get_engine()

    # Load matches
    print("Loading matches...")
    matches = pd.read_csv("../data/raw/results.csv")
    matches.rename(columns={"date": "match_date"}, inplace=True)
    matches["match_date"] = pd.to_datetime(matches["match_date"])
    matches.to_sql("matches", engine, if_exists="replace", index=False)
    print(f"Loaded {len(matches)} matches")

    # Load shootouts
    print("Loading shootouts...")
    shootouts = pd.read_csv("../data/raw/shootouts.csv")
    shootouts.rename(columns={"date": "match_date"}, inplace=True)
    shootouts["match_date"] = pd.to_datetime(shootouts["match_date"])
    shootouts.to_sql("shootouts", engine, if_exists="replace", index=False)
    print(f"Loaded {len(shootouts)} shootouts")

    # Load goalscorers
    print("Loading goalscorers...")
    goalscorers = pd.read_csv("../data/raw/goalscorers.csv")
    goalscorers.rename(columns={"date": "match_date"}, inplace=True)
    goalscorers["match_date"] = pd.to_datetime(goalscorers["match_date"])
    goalscorers.to_sql("goalscorers", engine, if_exists="replace", index=False)
    print(f"Loaded {len(goalscorers)} goalscorers")

    # Load former names
    print("Loading former names...")
    former_names = pd.read_csv("../data/raw/former_names.csv")
    former_names.to_sql("former_names", engine, if_exists="replace", index=False)
    print(f"Loaded {len(former_names)} former names")

    print("\nAll data loaded successfully!")

if __name__ == "__main__":
    load_csv_to_db()