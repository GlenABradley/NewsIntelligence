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

class DualPipelineAnalysisResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    total_claims: int
    factual_claims: int
    emotional_claims: int
    factual_loci: int
    emotional_variants: int
    fair_witness_narrative: str
    dual_pipeline_summary: str
    processing_details: Dict[str, Any]
    error: Optional[str] = None

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

# Dual Pipeline Truth Detection Endpoints
@api_router.post("/dual-pipeline-analyze", response_model=DualPipelineAnalysisResult)
async def analyze_dual_pipeline_batch(batch: ClaimBatch):
    """
    Analyze a batch of claims using the Dual Pipeline system
    
    This endpoint processes claims through:
    - Factual pipeline: Higgs substrate coherence mapping
    - Emotional pipeline: KNN-based sentiment clustering
    - Fair Witness synthesis: Objective facts with emotional overlays
    """
    try:
        logger.info(f"Processing dual pipeline analysis for {len(batch.claims)} claims")
        
        # Convert to format expected by dual pipeline detector
        claims_data = []
        for i, claim in enumerate(batch.claims):
            claims_data.append({
                'text': claim.text,
                'doc_id': i,
                'source_type': claim.source_type
            })
        
        # Perform dual pipeline analysis
        results = analyze_claims_dual_pipeline(claims_data)
        
        # Create result object
        analysis_result = DualPipelineAnalysisResult(
            id=batch.analysis_id or str(uuid.uuid4()),
            total_claims=results.get('total_claims', 0),
            factual_claims=results.get('factual_claims', 0),
            emotional_claims=results.get('emotional_claims', 0),
            factual_loci=results.get('factual_loci', 0),
            emotional_variants=results.get('emotional_variants', 0),
            fair_witness_narrative=results.get('fair_witness_narrative', ''),
            dual_pipeline_summary=results.get('dual_pipeline_summary', ''),
            processing_details=results.get('processing_details', {}),
            error=results.get('error')
        )
        
        # Store in database
        await db.dual_pipeline_analyses.insert_one(analysis_result.dict())
        
        logger.info(f"Dual pipeline analysis completed with ID: {analysis_result.id}")
        return analysis_result
        
    except Exception as e:
        logger.error(f"Error in dual pipeline analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Dual pipeline analysis failed: {str(e)}")

@api_router.get("/dual-pipeline-analyze/{analysis_id}", response_model=DualPipelineAnalysisResult)
async def get_dual_pipeline_analysis(analysis_id: str):
    """Get a specific dual pipeline analysis by ID"""
    try:
        analysis = await db.dual_pipeline_analyses.find_one({"id": analysis_id})
        if not analysis:
            raise HTTPException(status_code=404, detail="Dual pipeline analysis not found")
        
        # Convert MongoDB document to response model
        analysis.pop('_id', None)  # Remove MongoDB ID
        return DualPipelineAnalysisResult(**analysis)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving dual pipeline analysis {analysis_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve dual pipeline analysis")

@api_router.get("/dual-pipeline-analyze", response_model=List[Dict[str, Any]])
async def list_dual_pipeline_analyses(limit: int = 10, skip: int = 0):
    """List recent dual pipeline analyses"""
    try:
        analyses = await db.dual_pipeline_analyses.find(
            {},
            {"id": 1, "timestamp": 1, "total_claims": 1, "factual_claims": 1, "emotional_claims": 1, "_id": 0}
        ).sort("timestamp", -1).skip(skip).limit(limit).to_list(length=limit)
        
        return analyses
        
    except Exception as e:
        logger.error(f"Error listing dual pipeline analyses: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list dual pipeline analyses")

@api_router.post("/dual-pipeline-demo")
async def run_dual_pipeline_demo():
    """
    Run a demonstration of the dual pipeline system with sample claims
    """
    try:
        # Enhanced demo claims with mixed factual and emotional content
        demo_claims = [
            # Factual claims
            {"text": "The collision occurred at 3:42 PM at the intersection of Main Street and Oak Avenue", "source_type": "police_report"},
            {"text": "According to meteorological data, the temperature was 72°F with clear skies", "source_type": "weather_service"},
            {"text": "The study published in Nature journal shows that water boils at 100°C at sea level", "source_type": "science"},
            {"text": "NASA confirmed that the moon landing took place on July 20, 1969", "source_type": "government"},
            {"text": "The building is located at coordinates 40.7128° N, 74.0060° W", "source_type": "official_record"},
            
            # Emotional/subjective claims
            {"text": "I was absolutely terrified when I saw the accident happen right in front of me", "source_type": "witness"},
            {"text": "The whole situation seemed incredibly confusing and chaotic to everyone involved", "source_type": "witness"},
            {"text": "It felt like the most frightening experience of my entire life", "source_type": "witness"},
            {"text": "The weather was surprisingly beautiful and pleasant for this time of year", "source_type": "opinion"},
            {"text": "I think the moon landing was an amazing achievement that filled me with wonder", "source_type": "opinion"},
            
            # Mixed claims (factual with emotional elements)
            {"text": "The terrifying collision at Main and Oak involved two vehicles at 3:42 PM", "source_type": "news"},
            {"text": "Scientists are excited about the groundbreaking water boiling research findings", "source_type": "news"},
            {"text": "Many people feel that the moon landing was a magnificent human accomplishment", "source_type": "social_media"},
            
            # Contradictory emotional perspectives
            {"text": "I found the whole accident situation strangely fascinating rather than scary", "source_type": "bystander"},
            {"text": "The moon landing story seems suspicious and makes me feel doubtful", "source_type": "skeptic"},
        ]
        
        # Analyze with dual pipeline
        results = analyze_claims_dual_pipeline(demo_claims)
        
        return {
            "message": "Dual pipeline demonstration completed",
            "demo_claims_count": len(demo_claims),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error in dual pipeline demo: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Dual pipeline demo failed: {str(e)}")

@api_router.post("/analyze-urls-dual-pipeline", response_model=DualPipelineAnalysisResult)
async def analyze_urls_dual_pipeline(batch: URLBatch):
    """
    Extract content from URLs and analyze using dual pipeline system
    
    This endpoint:
    1. Extracts content from provided URLs
    2. Converts extracted content to claims
    3. Runs dual pipeline analysis with factual-emotional separation
    4. Returns Fair Witness results with emotional overlays
    """
    try:
        logger.info(f"Processing URL dual pipeline analysis for {len(batch.urls)} URLs")
        
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
        
        # Perform dual pipeline analysis on extracted claims
        results = analyze_claims_dual_pipeline(extracted_claims)
        
        # Add extraction metadata to results
        results['extracted_claims_count'] = len(extracted_claims)
        results['extraction_errors'] = extraction_errors
        
        # Create result object
        analysis_result = DualPipelineAnalysisResult(
            id=batch.analysis_id or str(uuid.uuid4()),
            total_claims=results.get('total_claims', 0),
            factual_claims=results.get('factual_claims', 0),
            emotional_claims=results.get('emotional_claims', 0),
            factual_loci=results.get('factual_loci', 0),
            emotional_variants=results.get('emotional_variants', 0),
            fair_witness_narrative=results.get('fair_witness_narrative', ''),
            dual_pipeline_summary=results.get('dual_pipeline_summary', ''),
            processing_details=results.get('processing_details', {}),
            error=results.get('error')
        )
        
        # Store in database
        await db.dual_pipeline_url_analyses.insert_one(analysis_result.dict())
        
        logger.info(f"URL dual pipeline analysis completed with ID: {analysis_result.id}")
        return analysis_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in URL dual pipeline analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"URL dual pipeline analysis failed: {str(e)}")

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