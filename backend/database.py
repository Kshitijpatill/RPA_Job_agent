from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime

# Creates a local SQLite file named agent_memory.db
SQLALCHEMY_DATABASE_URL = "sqlite:///./agent_memory.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Table 1: Your Master Vault (Stores Name, Skills, Github, etc.)
class UserProfile(Base):
    __tablename__ = "user_profile"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True) 
    value = Column(Text)

# Table 2: The Job Application Log
class JobLog(Base):
    __tablename__ = "job_logs"
    id = Column(Integer, primary_key=True, index=True)
    company = Column(String, index=True)
    role = Column(String)
    link = Column(String)
    status = Column(String, default="Applied")
    applied_on = Column(DateTime, default=datetime.datetime.utcnow)

# Generate the database tables
Base.metadata.create_all(bind=engine)