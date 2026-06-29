from sqlalchemy import create_engine

def get_engine():
    engine = create_engine(
        "postgresql+psycopg2://postgres:igaBakar385@localhost:5432/worldcup2026"
    )
    return engine