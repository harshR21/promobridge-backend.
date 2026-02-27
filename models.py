# backend/models.py
"""
Promobridge Database Models
SQLAlchemy ORM Models matching the PostgreSQL schema
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

# =====================================================
# USER MODEL
# =====================================================
class User(Base):
    __tablename__ = "users"
    
    user_id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # 'brand', 'influencer', 'admin'
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    influencer = relationship("Influencer", back_populates="user", uselist=False)
    brand = relationship("Brand", back_populates="user", uselist=False)
    
    __table_args__ = (
        CheckConstraint("role IN ('brand', 'influencer', 'admin')", name='check_user_role'),
    )

# =====================================================
# INFLUENCER MODEL
# =====================================================
class Influencer(Base):
    __tablename__ = "influencers"
    
    influencer_id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey('users.user_id', ondelete='CASCADE'))
    full_name = Column(String(255), nullable=False)
    handle = Column(String(100), unique=True, nullable=False)
    platform = Column(String(50), nullable=False)  # 'instagram', 'youtube', 'tiktok', 'twitter'
    niche = Column(String(100))
    bio = Column(Text)
    location = Column(String(255))
    
    # Metrics
    followers_count = Column(Integer, default=0)
    following_count = Column(Integer, default=0)
    posts_count = Column(Integer, default=0)
    avg_likes = Column(Float, default=0.0)
    avg_comments = Column(Float, default=0.0)
    avg_shares = Column(Float, default=0.0)
    engagement_rate = Column(Float, default=0.0)
    
    # Verification
    is_verified = Column(Boolean, default=False)
    verification_status = Column(String(20), default='pending')
    
    # Fraud Detection
    fraud_score = Column(Float, default=0.0)
    is_flagged = Column(Boolean, default=False)
    
    # Profile
    profile_picture_url = Column(Text)
    social_media_links = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="influencer")
    posts = relationship("PostMetric", back_populates="influencer")
    matches = relationship("Match", back_populates="influencer")
    fraud_flags = relationship("FraudFlag", back_populates="influencer")
    
    __table_args__ = (
        CheckConstraint("platform IN ('instagram', 'youtube', 'tiktok', 'twitter')", name='check_platform'),
        CheckConstraint("verification_status IN ('pending', 'approved', 'rejected')", name='check_verification_status'),
    )

# =====================================================
# BRAND MODEL
# =====================================================
class Brand(Base):
    __tablename__ = "brands"
    
    brand_id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey('users.user_id', ondelete='CASCADE'))
    brand_name = Column(String(255), nullable=False)
    company_name = Column(String(255))
    industry = Column(String(100))
    website = Column(String(255))
    description = Column(Text)
    logo_url = Column(Text)
    location = Column(String(255))
    company_size = Column(String(50))
    is_verified = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="brand")
    campaigns = relationship("Campaign", back_populates="brand")

# =====================================================
# CAMPAIGN MODEL
# =====================================================
class Campaign(Base):
    __tablename__ = "campaigns"
    
    campaign_id = Column(String, primary_key=True, default=generate_uuid)
    brand_id = Column(String, ForeignKey('brands.brand_id', ondelete='CASCADE'))
    
    title = Column(String(255), nullable=False)
    description = Column(Text)
    objectives = Column(Text)
    
    # Campaign Details
    niche = Column(String(100))
    platform = Column(String(50))
    content_type = Column(String(50))
    
    # Budget
    budget = Column(Float)
    min_followers = Column(Integer)
    max_followers = Column(Integer)
    
    # Timeline
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    deadline = Column(DateTime)
    
    # Status
    status = Column(String(20), default='draft')
    
    # Requirements
    deliverables = Column(Text)
    target_audience = Column(Text)
    dos_and_donts = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    brand = relationship("Brand", back_populates="campaigns")
    matches = relationship("Match", back_populates="campaign")
    
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'active', 'paused', 'completed', 'cancelled')", name='check_campaign_status'),
    )

# =====================================================
# POST METRICS MODEL
# =====================================================
class PostMetric(Base):
    __tablename__ = "posts_metrics"
    
    post_id = Column(String, primary_key=True, default=generate_uuid)
    influencer_id = Column(String, ForeignKey('influencers.influencer_id', ondelete='CASCADE'))
    
    platform = Column(String(50))
    post_url = Column(Text)
    post_type = Column(String(50))
    
    # Engagement Metrics
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    shares_count = Column(Integer, default=0)
    views_count = Column(Integer, default=0)
    saves_count = Column(Integer, default=0)
    
    # Calculated
    engagement_rate = Column(Float)
    reach = Column(Integer)
    
    posted_at = Column(DateTime)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    influencer = relationship("Influencer", back_populates="posts")

# =====================================================
# MATCH MODEL
# =====================================================
class Match(Base):
    __tablename__ = "matches"
    
    match_id = Column(String, primary_key=True, default=generate_uuid)
    campaign_id = Column(String, ForeignKey('campaigns.campaign_id', ondelete='CASCADE'))
    influencer_id = Column(String, ForeignKey('influencers.influencer_id', ondelete='CASCADE'))
    
    # Matching Scores
    overall_score = Column(Float, default=0.0)
    niche_match_score = Column(Float, default=0.0)
    engagement_score = Column(Float, default=0.0)
    audience_overlap_score = Column(Float, default=0.0)
    fraud_penalty = Column(Float, default=0.0)
    
    # Pricing
    suggested_price = Column(Float)
    
    # Status
    match_status = Column(String(20), default='pending')
    
    # Recommendation Reason
    recommendation_reason = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    campaign = relationship("Campaign", back_populates="matches")
    influencer = relationship("Influencer", back_populates="matches")
    
    __table_args__ = (
        CheckConstraint("match_status IN ('pending', 'accepted', 'rejected', 'completed')", name='check_match_status'),
    )

# =====================================================
# FRAUD FLAG MODEL
# =====================================================
class FraudFlag(Base):
    __tablename__ = "fraud_flags"
    
    flag_id = Column(String, primary_key=True, default=generate_uuid)
    influencer_id = Column(String, ForeignKey('influencers.influencer_id', ondelete='CASCADE'))
    
    flag_type = Column(String(50))
    severity = Column(String(20))
    description = Column(Text)
    detected_at = Column(DateTime, default=datetime.utcnow)
    
    # Admin Action
    reviewed_by = Column(String, ForeignKey('users.user_id'))
    review_status = Column(String(20), default='pending')
    reviewed_at = Column(DateTime)
    admin_notes = Column(Text)
    
    # Relationships
    influencer = relationship("Influencer", back_populates="fraud_flags")
    
    __table_args__ = (
        CheckConstraint("flag_type IN ('fake_followers', 'bot_engagement', 'sudden_spike', 'low_quality_audience')", name='check_flag_type'),
        CheckConstraint("severity IN ('low', 'medium', 'high')", name='check_severity'),
        CheckConstraint("review_status IN ('pending', 'confirmed', 'false_positive')", name='check_review_status'),
    )

# =====================================================
# NOTIFICATION MODEL
# =====================================================
class Notification(Base):
    __tablename__ = "notifications"
    
    notification_id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey('users.user_id', ondelete='CASCADE'))
    
    title = Column(String(255))
    message = Column(Text)
    notification_type = Column(String(50))
    is_read = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
