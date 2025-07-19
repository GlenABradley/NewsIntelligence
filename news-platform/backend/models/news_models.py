"""
News Intelligence Platform - Data Models
"""
from datetime import datetime
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")
        return field_schema

class NewsArticle(BaseModel):
    """Individual news article model"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    url: str
    title: str
    content: str
    summary: Optional[str] = None
    source: str
    source_perspective: str  # "left", "center-left", "center", "center-right", "right", "international"
    category: str  # "breaking", "national", "international", "business", etc.
    published_at: datetime
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Analysis fields
    impact_score: Optional[float] = None  # Your impact assessment module will populate
    story_cluster_id: Optional[str] = None
    processed: bool = False
    
    # Content analysis
    word_count: Optional[int] = None
    entities: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class StoryCluster(BaseModel):
    """Grouped articles about the same event/story"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    cluster_id: str
    main_event: str
    event_summary: str
    
    # Articles in this cluster
    articles: List[NewsArticle] = []
    article_count: int = 0
    
    # Metadata
    impact_score: float = 0.0  # Will be calculated by your impact module
    source_diversity_score: float = 0.0
    perspective_coverage: Dict[str, int] = {}
    
    # Timeline
    first_seen: datetime
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    # Processing status
    analysis_complete: bool = False
    report_generated: bool = False
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class FactualClaim(BaseModel):
    """Factual claim extracted from news content"""
    claim_text: str
    confidence_score: float
    supporting_sources: List[str]
    contradiction_sources: List[str] = []
    consensus_level: float  # 0-1, how much sources agree
    entity_mentions: List[str] = []

class EmotionalClaim(BaseModel):
    """Emotional/subjective content from news"""
    claim_text: str
    emotion_type: str  # fear, anger, joy, etc.
    intensity: float  # 0-10
    perspective: str  # source perspective
    source: str

class NewsAnalysis(BaseModel):
    """Complete analysis results for a story cluster"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    cluster_id: str
    analysis_date: datetime = Field(default_factory=datetime.utcnow)
    
    # Dual Pipeline Results
    factual_claims: List[FactualClaim] = []
    emotional_claims: List[EmotionalClaim] = []
    
    # Analysis Metadata
    total_sources: int
    factual_consensus_score: float
    emotional_spectrum_coverage: Dict[str, float]
    perspective_breakdown: Dict[str, int]
    
    # Fair Witness Synthesis
    objective_summary: str
    emotional_overlay: Dict[str, any]
    source_reliability_notes: str
    
    # Processing info
    processing_time_seconds: float
    processing_metadata: Dict[str, any] = {}
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class DailyReport(BaseModel):
    """Daily comprehensive report metadata"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    report_date: datetime
    generation_time: datetime = Field(default_factory=datetime.utcnow)
    
    # Top stories for the day
    top_stories: List[str] = []  # cluster_ids
    total_stories_processed: int
    total_sources_analyzed: int
    
    # Report files generated
    report_files: Dict[str, str] = {}  # format -> file_path
    
    # Quality metrics
    average_source_diversity: float
    average_factual_consensus: float
    processing_success_rate: float
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class ProcessingJob(BaseModel):
    """Background job tracking"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    job_type: str  # "daily_processing", "manual_trigger", "feed_poll"
    status: str  # "pending", "running", "completed", "failed"
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    # Job details
    parameters: Dict[str, any] = {}
    progress: int = 0  # 0-100
    current_step: str = ""
    
    # Results
    results: Dict[str, any] = {}
    error_message: Optional[str] = None
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}