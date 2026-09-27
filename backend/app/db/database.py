from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError

SQLALCHEMY_DATABASE_URL = "sqlite:///./advisor.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# SQLite ADD COLUMN is safe for existing tables; there's no Alembic here, so
# this is a deliberately minimal "add columns if missing" migration — not a
# general migration system.
# ponytail: additive ALTERs only, no version tracking, no rename/drop/backfill
# support — move to Alembic if a future change needs any of those.
def run_migrations(engine) -> None:
    statements = [
        "ALTER TABLE path_steps ADD COLUMN quiz_score INTEGER",
        "ALTER TABLE path_steps ADD COLUMN confidence_rating INTEGER",
        "ALTER TABLE path_steps ADD COLUMN time_spent_minutes INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN github_username VARCHAR",
        "ALTER TABLE journeys ADD COLUMN gap_report_json TEXT",
        "ALTER TABLE journeys ADD COLUMN hours_per_week INTEGER DEFAULT 10",
        "ALTER TABLE users ADD COLUMN leetcode_username VARCHAR",
        "ALTER TABLE users ADD COLUMN leetcode_stats_json TEXT",
        "ALTER TABLE competency_history ADD COLUMN leetcode_depth INTEGER",
        "ALTER TABLE path_steps ADD COLUMN subtopics_json TEXT DEFAULT '[]'",
        "ALTER TABLE path_steps ADD COLUMN roadmap_url VARCHAR DEFAULT ''",
    ]
    with engine.connect() as conn:
        for stmt in statements:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except OperationalError:
                conn.rollback()  # column already exists — fine
