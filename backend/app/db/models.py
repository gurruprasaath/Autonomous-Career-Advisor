from sqlalchemy import Boolean, Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    
    journeys = relationship("LearningJourney", back_populates="user")

class LearningJourney(Base):
    __tablename__ = "journeys"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    target_role = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
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
    
    journey = relationship("LearningJourney", back_populates="steps")
