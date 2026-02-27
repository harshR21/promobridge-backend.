# backend/main.py
"""
Promobridge Backend API
Main FastAPI application
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime
import uvicorn

from database import get_db, test_connection
from models import User, Influencer, Brand, Campaign, Match, PostMetric, FraudFlag
from auth import (
    hash_password,
    authenticate_user,
    create_user_token,
    get_current_active_user,
    require_role
)

# =====================================================
# FASTAPI APP
# =====================================================

app = FastAPI(
    title="Promobridge API",
    description="Smart Influencer-Brand Matching Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# PYDANTIC SCHEMAS (Request/Response Models)
# =====================================================

# User Schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str  # 'brand' or 'influencer'

class UserResponse(BaseModel):
    user_id: str
    email: str
    role: str
    is_verified: bool
    created_at: datetime
    
    class Config:
        orm_mode = True

# Influencer Schemas
class InfluencerCreate(BaseModel):
    full_name: str
    handle: str
    platform: str
    niche: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None

class InfluencerResponse(BaseModel):
    influencer_id: str
    full_name: str
    handle: str
    platform: str
    niche: Optional[str]
    followers_count: int
    engagement_rate: float
    is_verified: bool
    
    class Config:
        orm_mode = True

# Campaign Schemas
class CampaignCreate(BaseModel):
    title: str
    description: Optional[str] = None
    niche: Optional[str] = None
    platform: Optional[str] = None
    budget: Optional[float] = None
    min_followers: Optional[int] = None
    max_followers: Optional[int] = None

class CampaignResponse(BaseModel):
    campaign_id: str
    title: str
    description: Optional[str]
    niche: Optional[str]
    platform: Optional[str]
    budget: Optional[float]
    status: str
    created_at: datetime
    
    class Config:
        orm_mode = True

# Match Schema
class MatchResponse(BaseModel):
    match_id: str
    influencer_id: str
    campaign_id: str
    overall_score: float
    suggested_price: Optional[float]
    match_status: str
    
    class Config:
        orm_mode = True

# =====================================================
# ROOT & HEALTH CHECK
# =====================================================

@app.get("/")
def root():
    """Root endpoint - API information"""
    return {
        "name": "Promobridge API",
        "version": "1.0.0",
        "status": "active",
        "docs": "/docs",
        "description": "Smart Influencer-Brand Matching Platform"
    }

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    try:
        # Test database connection
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}"
        )

# =====================================================
# AUTHENTICATION ROUTES
# =====================================================

@app.post("/auth/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register new user (brand or influencer)"""
    
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Validate role
    if user_data.role not in ['brand', 'influencer']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be 'brand' or 'influencer'"
        )
    
    # Create new user
    new_user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role=user_data.role
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@app.post("/auth/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login endpoint - returns JWT token"""
    
    user = authenticate_user(db, form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return create_user_token(user)

@app.get("/auth/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current logged-in user information"""
    return current_user

# =====================================================
# INFLUENCER ROUTES
# =====================================================

@app.get("/influencers", response_model=List[InfluencerResponse])
def get_influencers(
    skip: int = 0,
    limit: int = 20,
    platform: Optional[str] = None,
    niche: Optional[str] = None,
    min_followers: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get list of influencers with filters"""
    
    query = db.query(Influencer)
    
    # Apply filters
    if platform:
        query = query.filter(Influencer.platform == platform)
    if niche:
        query = query.filter(Influencer.niche == niche)
    if min_followers:
        query = query.filter(Influencer.followers_count >= min_followers)
    
    # Get results with pagination
    influencers = query.offset(skip).limit(limit).all()
    
    return influencers

@app.get("/influencers/{influencer_id}", response_model=InfluencerResponse)
def get_influencer(influencer_id: str, db: Session = Depends(get_db)):
    """Get single influencer by ID"""
    
    influencer = db.query(Influencer).filter(
        Influencer.influencer_id == influencer_id
    ).first()
    
    if not influencer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Influencer not found"
        )
    
    return influencer

@app.post("/influencers", response_model=InfluencerResponse)
def create_influencer(
    influencer_data: InfluencerCreate,
    current_user: User = Depends(require_role("influencer")),
    db: Session = Depends(get_db)
):
    """Create influencer profile (influencers only)"""
    
    # Check if handle already exists
    existing = db.query(Influencer).filter(
        Influencer.handle == influencer_data.handle
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Handle already taken"
        )
    
    # Create influencer profile
    new_influencer = Influencer(
        user_id=current_user.user_id,
        **influencer_data.dict()
    )
    
    db.add(new_influencer)
    db.commit()
    db.refresh(new_influencer)
    
    return new_influencer

# =====================================================
# CAMPAIGN ROUTES
# =====================================================

@app.get("/campaigns", response_model=List[CampaignResponse])
def get_campaigns(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get list of campaigns"""
    
    query = db.query(Campaign)
    
    if status:
        query = query.filter(Campaign.status == status)
    
    campaigns = query.offset(skip).limit(limit).all()
    
    return campaigns

@app.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
def get_campaign(campaign_id: str, db: Session = Depends(get_db)):
    """Get campaign by ID"""
    
    campaign = db.query(Campaign).filter(
        Campaign.campaign_id == campaign_id
    ).first()
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    return campaign

@app.post("/campaigns", response_model=CampaignResponse)
def create_campaign(
    campaign_data: CampaignCreate,
    current_user: User = Depends(require_role("brand")),
    db: Session = Depends(get_db)
):
    """Create new campaign (brands only)"""
    
    # Get brand profile
    brand = db.query(Brand).filter(Brand.user_id == current_user.user_id).first()
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please create brand profile first"
        )
    
    # Create campaign
    new_campaign = Campaign(
        brand_id=brand.brand_id,
        **campaign_data.dict()
    )
    
    db.add(new_campaign)
    db.commit()
    db.refresh(new_campaign)
    
    return new_campaign

# =====================================================
# MATCHING ENGINE
# =====================================================

@app.post("/campaigns/{campaign_id}/match")
def match_influencers(
    campaign_id: str,
    current_user: User = Depends(require_role("brand")),
    db: Session = Depends(get_db)
):
    """Run AI matching algorithm for campaign"""
    
    # Get campaign
    campaign = db.query(Campaign).filter(
        Campaign.campaign_id == campaign_id
    ).first()
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    # Get eligible influencers
    query = db.query(Influencer).filter(Influencer.is_verified == True)
    
    if campaign.platform:
        query = query.filter(Influencer.platform == campaign.platform)
    
    if campaign.niche:
        query = query.filter(Influencer.niche == campaign.niche)
    
    if campaign.min_followers:
        query = query.filter(Influencer.followers_count >= campaign.min_followers)
    
    if campaign.max_followers:
        query = query.filter(Influencer.followers_count <= campaign.max_followers)
    
    influencers = query.all()
    
    # Calculate matches
    matches = []
    for influencer in influencers:
        # Simple scoring algorithm
        niche_score = 100.0 if campaign.niche == influencer.niche else 50.0
        engagement_score = min(influencer.engagement_rate * 10, 100.0)
        fraud_penalty = influencer.fraud_score * 10
        
        overall_score = (niche_score * 0.4 + engagement_score * 0.6) - fraud_penalty
        overall_score = max(0, min(100, overall_score))  # Clamp between 0-100
        
        # Calculate suggested price
        base_cpm = 10
        suggested_price = (influencer.followers_count / 1000) * base_cpm * (1 + influencer.engagement_rate / 100)
        
        # Create match record
        match = Match(
            campaign_id=campaign_id,
            influencer_id=influencer.influencer_id,
            overall_score=overall_score,
            niche_match_score=niche_score,
            engagement_score=engagement_score,
            fraud_penalty=fraud_penalty,
            suggested_price=suggested_price,
            recommendation_reason=f"Matched based on {influencer.niche} niche with {influencer.engagement_rate}% engagement"
        )
        
        db.add(match)
        matches.append({
            "influencer_id": influencer.influencer_id,
            "influencer_name": influencer.full_name,
            "score": overall_score,
            "suggested_price": round(suggested_price, 2)
        })
    
    db.commit()
    
    # Sort matches by score
    matches.sort(key=lambda x: x['score'], reverse=True)
    
    return {
        "campaign_id": campaign_id,
        "total_matches": len(matches),
        "top_matches": matches[:10]  # Return top 10
    }

# =====================================================
# PRICING CALCULATOR
# =====================================================

@app.post("/calculate-pricing")
def calculate_pricing(
    followers: int,
    engagement_rate: float,
    platform: str,
    content_type: str = "post"
):
    """Calculate suggested pricing for influencer"""
    
    # Base CPM (Cost Per Mille - per 1000 followers)
    base_cpm = 10
    
    # Platform multipliers
    platform_multipliers = {
        "instagram": 1.0,
        "youtube": 1.5,
        "tiktok": 0.8,
        "twitter": 0.7
    }
    
    # Content type multipliers
    content_multipliers = {
        "post": 1.0,
        "story": 0.5,
        "reel": 1.3,
        "video": 1.5
    }
    
    platform_mult = platform_multipliers.get(platform.lower(), 1.0)
    content_mult = content_multipliers.get(content_type.lower(), 1.0)
    engagement_mult = 1 + (engagement_rate / 100)
    
    suggested_price = (followers / 1000) * base_cpm * engagement_mult * platform_mult * content_mult
    
    return {
        "suggested_price": round(suggested_price, 2),
        "min_price": round(suggested_price * 0.8, 2),
        "max_price": round(suggested_price * 1.2, 2),
        "currency": "USD",
        "calculation_factors": {
            "followers": followers,
            "engagement_rate": engagement_rate,
            "platform_multiplier": platform_mult,
            "content_multiplier": content_mult
        }
    }

# =====================================================
# FRAUD DETECTION
# =====================================================

@app.post("/fraud-check/{influencer_id}")
def check_fraud(
    influencer_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Run fraud detection on influencer"""
    
    influencer = db.query(Influencer).filter(
        Influencer.influencer_id == influencer_id
    ).first()
    
    if not influencer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Influencer not found"
        )
    
    # Simple fraud detection logic
    fraud_indicators = []
    fraud_score = 0.0
    
    # Check engagement rate (too high or too low is suspicious)
    if influencer.engagement_rate > 15:
        fraud_indicators.append("Unusually high engagement rate")
        fraud_score += 0.3
    elif influencer.engagement_rate < 0.5:
        fraud_indicators.append("Unusually low engagement rate")
        fraud_score += 0.2
    
    # Check follower-to-following ratio
    if influencer.following_count > 0:
        ratio = influencer.followers_count / influencer.following_count
        if ratio < 0.1:  # Following way more than followers
            fraud_indicators.append("Suspicious follower-following ratio")
            fraud_score += 0.3
    
    # Update fraud score
    influencer.fraud_score = min(fraud_score, 1.0)
    db.commit()
    
    return {
        "influencer_id": influencer_id,
        "fraud_score": round(fraud_score, 2),
        "is_suspicious": fraud_score > 0.5,
        "indicators": fraud_indicators,
        "recommendation": "Review manually" if fraud_score > 0.5 else "Looks legitimate"
    }

# =====================================================
# STATISTICS
# =====================================================

@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get platform statistics"""
    
    total_influencers = db.query(Influencer).count()
    total_brands = db.query(Brand).count()
    total_campaigns = db.query(Campaign).count()
    active_campaigns = db.query(Campaign).filter(Campaign.status == 'active').count()
    total_matches = db.query(Match).count()
    
    return {
        "total_influencers": total_influencers,
        "total_brands": total_brands,
        "total_campaigns": total_campaigns,
        "active_campaigns": active_campaigns,
        "total_matches": total_matches,
        "success_rate": 95.0  # Mock success rate
    }

# =====================================================
# RUN SERVER
# =====================================================

if __name__ == "__main__":
    # Test database connection on startup
    print("🔌 Testing database connection...")
    test_connection()
    
    # Run the server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
