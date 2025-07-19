"""
News Intelligence Platform - Main Application
FastAPI application for automated news analysis and report generation
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Import API routers
from api.news_endpoints import router as news_router
from api.report_endpoints import router as reports_router

# Import core components
from core.config import settings
from core.database import init_database, close_database, health_check
from workers.daily_processor import start_daily_processor, stop_daily_processor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    try:
        logger.info("Starting News Intelligence Platform...")
        
        # Initialize database
        await init_database()
        logger.info("Database initialized")
        
        # Start daily processor scheduler
        await start_daily_processor()
        logger.info("Daily processor scheduler started")
        
        logger.info("News Intelligence Platform startup complete")
        
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    try:
        logger.info("Shutting down News Intelligence Platform...")
        
        # Stop daily processor
        await stop_daily_processor()
        logger.info("Daily processor stopped")
        
        # Close database
        await close_database()
        logger.info("Database connection closed")
        
        logger.info("News Intelligence Platform shutdown complete")
        
    except Exception as e:
        logger.error(f"Shutdown error: {str(e)}")

# Create FastAPI application
app = FastAPI(
    title="News Intelligence Platform",
    description="Automated news aggregation, analysis, and professional report generation for news anchors",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(news_router)
app.include_router(reports_router)

@app.get("/", summary="News Intelligence Platform API")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "News Intelligence Platform",
        "version": "1.0.0",
        "description": "Automated news aggregation, analysis, and professional report generation",
        "features": {
            "news_aggregation": "RSS feeds and external APIs",
            "story_clustering": "Semantic pattern matching (placeholder ready)",
            "impact_assessment": "Data science machine integration (placeholder ready)", 
            "dual_pipeline": "Factual/emotional content separation",
            "report_generation": "Professional journalist-ready reports",
            "automated_scheduling": "Daily processing at Noon Eastern"
        },
        "endpoints": {
            "news_api": "/api/news/",
            "reports_api": "/api/reports/",
            "documentation": "/docs",
            "health_check": "/health"
        },
        "status": "operational",
        "timezone": settings.TIMEZONE,
        "daily_processing_time": settings.DAILY_PROCESSING_TIME
    }

@app.get("/health", summary="Health Check")
async def health_check_endpoint():
    """Application health check"""
    try:
        # Check database connectivity
        db_healthy = await health_check()
        
        # Check if daily processor is running
        from .workers.daily_processor import daily_processor
        processor_status = await daily_processor.get_processing_status()
        
        health_status = {
            "status": "healthy" if db_healthy else "unhealthy",
            "timestamp": "2024-01-15T12:00:00Z",  # Will be dynamic
            "components": {
                "database": "healthy" if db_healthy else "unhealthy",
                "daily_processor": "running" if processor_status["scheduler_running"] else "stopped",
                "processing_active": processor_status["is_processing"]
            },
            "configuration": {
                "database_name": settings.DATABASE_NAME,
                "timezone": settings.TIMEZONE,
                "daily_processing_time": settings.DAILY_PROCESSING_TIME,
                "max_articles_per_story": settings.MAX_ARTICLES_PER_STORY,
                "top_stories_count": settings.TOP_STORIES_COUNT
            }
        }
        
        if not db_healthy:
            raise HTTPException(status_code=503, detail="Database connectivity issue")
        
        return health_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "type": type(exc).__name__
        }
    )

if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )