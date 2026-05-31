from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(160), nullable=False)
    email = Column(String(240), unique=True, nullable=False, index=True)
    password_hash = Column(String(300), nullable=False)
    role = Column(String(20), nullable=False)  # candidate, company
    plan = Column(String(40), default="free")
    plan_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    candidate_profile = relationship("CandidateProfile", back_populates="user", uselist=False, lazy="selectin")
    company_profile = relationship("CompanyProfile", back_populates="user", uselist=False, lazy="selectin")


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    desired_title = Column(String(200), default="")
    skills = Column(Text, default="")
    level = Column(String(50), default="Junior")
    address = Column(String(300), default="")
    latitude = Column(Float, default=-23.5505)
    longitude = Column(Float, default=-46.6333)
    resume = Column(Text, default="")
    experience = Column(Text, default="")
    interest_area = Column(String(160), default="")

    user = relationship("User", back_populates="candidate_profile", lazy="selectin")


class CompanyProfile(Base):
    __tablename__ = "company_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    company_name = Column(String(200), nullable=False)
    description = Column(Text, default="")
    website = Column(String(300), default="")
    address = Column(String(300), default="")

    user = relationship("User", back_populates="company_profile", lazy="selectin")
    jobs = relationship("Job", back_populates="company", lazy="selectin")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("company_profiles.id"), nullable=False)
    title = Column(String(300), nullable=False)
    location = Column(String(200), default="Sao Paulo, SP")
    address = Column(String(300), default="")
    latitude = Column(Float, default=-23.5505)
    longitude = Column(Float, default=-46.6333)
    description = Column(Text, default="")
    skills = Column(Text, default="")
    level = Column(String(50), default="")
    job_type = Column(String(50), default="CLT")
    modality = Column(String(50), default="Presencial")
    salary = Column(String(80), default="")
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())

    company = relationship("CompanyProfile", back_populates="jobs", lazy="selectin")
    likes = relationship("Like", back_populates="job", lazy="selectin")
    matches = relationship("Match", back_populates="job", lazy="selectin")


class Like(Base):
    __tablename__ = "likes"
    __table_args__ = (UniqueConstraint("candidate_id", "job_id", "actor", name="uq_like_actor"),)

    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidate_profiles.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    actor = Column(String(20), nullable=False)  # candidate, company, auto_agent
    created_at = Column(DateTime, server_default=func.now())

    candidate = relationship("CandidateProfile", lazy="selectin")
    job = relationship("Job", back_populates="likes", lazy="selectin")


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (UniqueConstraint("candidate_id", "job_id", name="uq_match_candidate_job"),)

    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidate_profiles.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("company_profiles.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    candidate = relationship("CandidateProfile", lazy="selectin")
    company = relationship("CompanyProfile", lazy="selectin")
    job = relationship("Job", back_populates="matches", lazy="selectin")
    messages = relationship("Message", back_populates="match", order_by="Message.created_at", lazy="selectin")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    match = relationship("Match", back_populates="messages")
    sender = relationship("User", lazy="selectin")


class AdEvent(Base):
    __tablename__ = "ad_events"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    placement = Column(String(80), default="navigation")
    campaign = Column(String(160), default="")
    created_at = Column(DateTime, server_default=func.now())


class CrawlerLog(Base):
    __tablename__ = "crawler_logs"

    id = Column(Integer, primary_key=True)
    message = Column(Text, nullable=False)
    level = Column(String(20), default="INFO")
    source = Column(String(100), default="system")
    timestamp = Column(DateTime, server_default=func.now())
