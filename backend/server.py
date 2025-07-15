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
from dual_pipeline_detector import analyze_claims_dual_pipeline, DualPipelineDetector
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

class URLInput(BaseModel):
    url: str = Field(..., description="URL to extract content from")
    source_type: str = Field(default="news", description="Source type for the extracted content")

class URLBatch(BaseModel):
    urls: List[URLInput] = Field(..., min_items=1, max_items=20, description="List of URLs to analyze")
    analysis_id: Optional[str] = Field(default=None, description="Optional analysis ID for tracking")

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

@api_router.post("/analyze-urls", response_model=TruthAnalysisResult)
async def analyze_urls(batch: URLBatch):
    """
    Extract content from URLs and analyze for truth detection
    
    This endpoint:
    1. Extracts content from provided URLs
    2. Converts extracted content to claims
    3. Runs truth detection analysis
    4. Returns comprehensive results
    """
    try:
        logger.info(f"Processing URL analysis for {len(batch.urls)} URLs")
        
        # Extract content from all URLs
        extracted_claims = []
        extraction_errors = []
        
        for i, url_input in enumerate(batch.urls):
            try:
                content_result = extract_content_from_url(url_input.url)
                
                if content_result["success"]:
                    # Create claim from extracted content
                    claim_text = f"{content_result['title']}\n\n{content_result['content']}"
                    
                    # Truncate if too long (keep within 6500 chars for safety)
                    if len(claim_text) > 6500:
                        claim_text = claim_text[:6500] + "..."
                    
                    extracted_claims.append({
                        'text': claim_text,
                        'doc_id': i,
                        'source_type': url_input.source_type,
                        'source_url': url_input.url,
                        'source_domain': content_result['source_domain']
                    })
                    
                    logger.info(f"Successfully extracted content from {content_result['source_domain']}")
                else:
                    extraction_errors.append(f"Failed to extract from {url_input.url}: {content_result['error']}")
                    
            except Exception as e:
                extraction_errors.append(f"Error processing {url_input.url}: {str(e)}")
        
        if not extracted_claims:
            raise HTTPException(
                status_code=400, 
                detail=f"No content could be extracted from any URLs. Errors: {'; '.join(extraction_errors)}"
            )
        
        # Perform truth analysis on extracted claims
        results = analyze_truth_claims(extracted_claims)
        
        # Add extraction metadata to results
        results['extracted_claims_count'] = len(extracted_claims)
        results['extraction_errors'] = extraction_errors
        
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
        await db.url_analyses.insert_one(analysis_result.dict())
        
        logger.info(f"URL analysis completed with ID: {analysis_result.id}")
        return analysis_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in URL analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"URL analysis failed: {str(e)}")

@api_router.post("/extract-url")
async def extract_single_url(url_input: URLInput):
    """
    Extract and preview content from a single URL
    Useful for testing URL extraction before analysis
    """
    try:
        logger.info(f"Extracting content from single URL: {url_input.url}")
        
        content_result = extract_content_from_url(url_input.url)
        
        return {
            "url": url_input.url,
            "success": content_result["success"],
            "title": content_result.get("title", ""),
            "content_preview": content_result.get("content", "")[:500] + "..." if content_result.get("content") else "",
            "content_length": len(content_result.get("content", "")),
            "source_domain": content_result.get("source_domain", ""),
            "error": content_result.get("error")
        }
        
    except Exception as e:
        logger.error(f"Error extracting single URL: {str(e)}")
        raise HTTPException(status_code=500, detail=f"URL extraction failed: {str(e)}")

@api_router.post("/url-batch", response_model=URLBatch)
async def process_url_batch(batch: URLBatch):
    """Process a batch of URLs for content extraction"""
    try:
        # Store the batch request
        await db.url_batches.insert_one(batch.dict())
        return batch
    except Exception as e:
        logger.error(f"Error processing URL batch: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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