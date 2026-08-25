"""Migration helper is idempotent and adds the expected columns."""
import sqlalchemy as sa
from sqlalchemy import create_engine

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
    assert "github_username" in user_cols
    assert {"gap_report_json", "hours_per_week"} <= journey_cols
    assert "github_evidence" in inspector.get_table_names()
