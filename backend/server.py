from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import uuid
from datetime import datetime
from truth_detector import analyze_truth_claims, Claim, TruthDetectorCore
from url_extractor import extract_content_from_url
import asyncio
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="Truth Detector API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Enhanced Models
class ClaimInput(BaseModel):
    text: str = Field(..., min_length=1, max_length=7000, description="The claim text")
    source_type: str = Field(default="unknown", description="Source type of the claim")

class ClaimBatch(BaseModel):
    claims: List[ClaimInput] = Field(..., min_items=1, max_items=100, description="List of claims to analyze")
    analysis_id: Optional[str] = Field(default=None, description="Optional analysis ID for tracking")

class TruthAnalysisResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    total_claims: int
    total_clusters: int
    contradictions: int
    probable_truths: List[Dict[str, Any]]
    inconsistencies: List[Dict[str, Any]]
    narrative: str
    summary: str
    clusters: List[Dict[str, Any]]
    error: Optional[str] = None

class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

# Truth Detection Endpoints
@api_router.post("/truth-analyze", response_model=TruthAnalysisResult)
async def analyze_truth_batch(batch: ClaimBatch):
    """
    Analyze a batch of claims for truth detection
    
    This endpoint processes multiple claims and returns:
    - Probable truths with confidence scores
    - Detected inconsistencies and contradictions
    - Coherent narrative generation
    - Detailed analysis summary
    """
    try:
        logger.info(f"Processing truth analysis for {len(batch.claims)} claims")
        
        # Convert to format expected by truth detector
        claims_data = []
        for i, claim in enumerate(batch.claims):
            claims_data.append({
                'text': claim.text,
                'doc_id': i,
                'source_type': claim.source_type
            })
        
        # Perform analysis
        results = analyze_truth_claims(claims_data)
        
        # Create result object
        analysis_result = TruthAnalysisResult(
            id=batch.analysis_id or str(uuid.uuid4()),
            total_claims=results.get('total_claims', 0),
            total_clusters=results.get('total_clusters', 0),
            contradictions=results.get('contradictions', 0),
            probable_truths=results.get('probable_truths', []),
            inconsistencies=results.get('inconsistencies', []),
            narrative=results.get('narrative', ''),
            summary=results.get('summary', ''),
            clusters=results.get('clusters', []),
            error=results.get('error')
        )
        
        # Store in database
        await db.truth_analyses.insert_one(analysis_result.dict())
        
        logger.info(f"Truth analysis completed with ID: {analysis_result.id}")
        return analysis_result
        
    except Exception as e:
        logger.error(f"Error in truth analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@api_router.get("/truth-analyze/{analysis_id}", response_model=TruthAnalysisResult)
async def get_truth_analysis(analysis_id: str):
    """Get a specific truth analysis by ID"""
    try:
        analysis = await db.truth_analyses.find_one({"id": analysis_id})
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        # Convert MongoDB document to response model
        analysis.pop('_id', None)  # Remove MongoDB ID
        return TruthAnalysisResult(**analysis)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving analysis {analysis_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve analysis")

@api_router.get("/truth-analyze", response_model=List[Dict[str, Any]])
async def list_truth_analyses(limit: int = 10, skip: int = 0):
    """List recent truth analyses"""
    try:
        analyses = await db.truth_analyses.find(
            {},
            {"id": 1, "timestamp": 1, "total_claims": 1, "total_clusters": 1, "contradictions": 1, "_id": 0}
        ).sort("timestamp", -1).skip(skip).limit(limit).to_list(length=limit)
        
        return analyses
        
    except Exception as e:
        logger.error(f"Error listing analyses: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list analyses")

@api_router.post("/truth-demo")
async def run_truth_demo():
    """
    Run a demonstration of the truth detector with sample claims
    """
    try:
        # Enhanced demo claims with better contradiction examples
        demo_claims = [
            # Earth shape contradiction
            {"text": "Earth is round and orbits the Sun", "source_type": "science"},
            {"text": "Earth is flat and stationary", "source_type": "conspiracy"},
            {"text": "Earth is spherical globe", "source_type": "academic"},
            
            # Climate change contradiction
            {"text": "Climate change is caused by human activities", "source_type": "science"},
            {"text": "Climate change is natural phenomenon", "source_type": "skeptic"},
            {"text": "Global warming is real and man-made", "source_type": "expert"},
            
            # Vaccine contradiction
            {"text": "COVID-19 vaccines are safe and effective", "source_type": "medical"},
            {"text": "COVID-19 vaccines are dangerous and harmful", "source_type": "anti-vaccine"},
            {"text": "Vaccines have proven safety profile", "source_type": "government"},
            
            # Moon landing contradiction
            {"text": "Moon landing was real historical achievement", "source_type": "history"},
            {"text": "Moon landing was staged in studio", "source_type": "conspiracy"},
            
            # Universal facts (should cluster together)
            {"text": "Water boils at 100°C at sea level", "source_type": "science"},
            {"text": "Water freezes at 0°C", "source_type": "science"},
            {"text": "Regular exercise improves health", "source_type": "health"},
        ]
        
        # Analyze demo claims
        results = analyze_truth_claims(demo_claims)
        
        return {
            "message": "Truth detector demonstration completed",
            "demo_claims_count": len(demo_claims),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error in truth demo: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Demo failed: {str(e)}")

# Health check endpoint
@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "service": "truth_detector_api"
    }

# Original endpoints
@api_router.get("/")
async def root():
    return {"message": "Truth Detector API v1.0"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)