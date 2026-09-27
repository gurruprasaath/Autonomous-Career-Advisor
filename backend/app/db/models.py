from sqlalchemy import Boolean, Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    github_username = Column(String, nullable=True)
    leetcode_username = Column(String, nullable=True)
    leetcode_stats_json = Column(Text, nullable=True)

    journeys = relationship("LearningJourney", back_populates="user")

class LearningJourney(Base):
    __tablename__ = "journeys"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    target_role = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    gap_report_json = Column(Text, nullable=True)
    hours_per_week = Column(Integer, default=10)

    user = relationship("User", back_populates="journeys")
    steps = relationship("PathStep", back_populates="journey")

class PathStep(Base):
    __tablename__ = "path_steps"
    id = Column(Integer, primary_key=True, index=True)
    journey_id = Column(Integer, ForeignKey("journeys.id"))
    order = Column(Integer)
    skill_id = Column(String)
    skill_name = Column(String)
    objective = Column(String)
    milestone = Column(String)
    estimated_weeks = Column(Float)
    status = Column(String, default="pending") # pending, in_progress, struggling, completed
    resources_json = Column(Text, default="[]") # JSON string of resources
    subtopics_json = Column(Text, default="[]")  # JSON list of {id, name, level}
    roadmap_url = Column(String, default="")
    quiz_score = Column(Integer, nullable=True)
    confidence_rating = Column(Integer, nullable=True)
    time_spent_minutes = Column(Integer, default=0)

    journey = relationship("LearningJourney", back_populates="steps")


class GithubEvidence(Base):
    __tablename__ = "github_evidence"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    skill_id = Column(String)
    repo_name = Column(String)
    repo_language = Column(String)
    last_pushed_at = Column(DateTime, nullable=True)
    detected_at = Column(DateTime, default=datetime.datetime.utcnow)

class CompetencyHistory(Base):
    __tablename__ = "competency_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    skill_id = Column(String)
    depth_score = Column(Integer)
    quiz_score = Column(Integer, nullable=True)
    confidence_rating = Column(Integer, nullable=True)
    has_github_evidence = Column(Boolean, default=False)
    leetcode_depth = Column(Integer, nullable=True)
    rationale = Column(String)
    recorded_at = Column(DateTime, default=datetime.datetime.utcnow)

class AnalyzedRepo(Base):
    __tablename__ = "analyzed_repos"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    username = Column(String)
    repo_name = Column(String)
    file_count = Column(Integer, default=0)
    analyzed_at = Column(DateTime, default=datetime.datetime.utcnow)

