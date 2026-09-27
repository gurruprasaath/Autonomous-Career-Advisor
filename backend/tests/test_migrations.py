"""Migration helper is idempotent and adds the expected columns."""
import sqlalchemy as sa
from sqlalchemy import create_engine, text

from app.db.database import run_migrations
from app.db import models


def test_migrations_add_columns_and_are_idempotent():
    engine = create_engine("sqlite:///:memory:")
    models.Base.metadata.create_all(bind=engine)

    run_migrations(engine)
    run_migrations(engine)  # must not raise on second run

    inspector = sa.inspect(engine)
    path_step_cols = {c["name"] for c in inspector.get_columns("path_steps")}
    user_cols = {c["name"] for c in inspector.get_columns("users")}
    journey_cols = {c["name"] for c in inspector.get_columns("journeys")}

    assert {"quiz_score", "confidence_rating", "time_spent_minutes"} <= path_step_cols
    assert {"subtopics_json", "roadmap_url"} <= path_step_cols
    assert "github_username" in user_cols
    assert {"leetcode_username", "leetcode_stats_json"} <= user_cols
    history_cols = {c["name"] for c in inspector.get_columns("competency_history")}
    assert "leetcode_depth" in history_cols
    assert {"gap_report_json", "hours_per_week"} <= journey_cols
    assert "github_evidence" in inspector.get_table_names()


def test_legacy_subtopics_columns_get_real_alter_defaults():
    """`create_all` would create subtopics_json/roadmap_url for free even if the
    ALTER statements were wrong or missing — so this builds a pre-R1 table by
    hand (no subtopics_json/roadmap_url) and checks run_migrations actually
    backfills them with the right defaults on an existing row."""
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE path_steps (
                id INTEGER PRIMARY KEY,
                journey_id INTEGER,
                "order" INTEGER,
                skill_id VARCHAR,
                skill_name VARCHAR,
                objective VARCHAR,
                milestone VARCHAR,
                estimated_weeks FLOAT,
                status VARCHAR,
                resources_json TEXT,
                quiz_score INTEGER,
                confidence_rating INTEGER,
                time_spent_minutes INTEGER
            )
        """))
        conn.execute(text("""
            INSERT INTO path_steps
                (id, journey_id, "order", skill_id, skill_name, objective, milestone,
                 estimated_weeks, status, resources_json, quiz_score, confidence_rating,
                 time_spent_minutes)
            VALUES (1, 1, 1, 'python', 'Python', 'Learn it', 'Ship it',
                    2.0, 'pending', '[]', NULL, NULL, 0)
        """))
        conn.commit()

    run_migrations(engine)

    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT subtopics_json, roadmap_url FROM path_steps WHERE id = 1"
        )).fetchone()
    assert row.subtopics_json == "[]"
    assert row.roadmap_url == ""
