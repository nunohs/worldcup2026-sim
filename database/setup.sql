-- Create matches table
CREATE TABLE IF NOT EXISTS matches (
    id SERIAL PRIMARY KEY,
    match_date DATE,
    home_team VARCHAR(100),
    away_team VARCHAR(100),
    home_score INTEGER,
    away_score INTEGER,
    tournament VARCHAR(100),
    city VARCHAR(100),
    country VARCHAR(100),
    neutral BOOLEAN
);

-- Create shootouts table
CREATE TABLE IF NOT EXISTS shootouts (
    id SERIAL PRIMARY KEY,
    match_date DATE,
    home_team VARCHAR(100),
    away_team VARCHAR(100),
    winner VARCHAR(100)
);

-- Create goalscorers table
CREATE TABLE IF NOT EXISTS goalscorers (
    id SERIAL PRIMARY KEY,
    match_date DATE,
    home_team VARCHAR(100),
    away_team VARCHAR(100),
    team VARCHAR(100),
    scorer VARCHAR(100),
    minute INTEGER,
    own_goal BOOLEAN,
    penalty BOOLEAN
);