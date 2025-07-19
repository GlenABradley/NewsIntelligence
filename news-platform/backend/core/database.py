"""
News Intelligence Platform - Database Configuration
MongoDB connection and database operations
"""
import motor.motor_asyncio
from typing import Optional
import logging

from .config import settings

logger = logging.getLogger(__name__)

# Global database client
_client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
_database = None

async def get_database():
    """Get database instance"""
    global _client, _database
    
    if _database is None:
        _client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGO_URL)
        _database = _client[settings.DATABASE_NAME]
        logger.info(f"Connected to MongoDB database: {settings.DATABASE_NAME}")
    
    return _database

async def close_database():
    """Close database connection"""
    global _client, _database
    
    if _client:
        _client.close()
        _client = None
        _database = None
        logger.info("Database connection closed")

async def init_database():
    """Initialize database with indexes and collections"""
    try:
        db = await get_database()
        
        # Create indexes for better performance
        
        # News articles indexes
        await db.news_articles.create_index("url", unique=True)
        await db.news_articles.create_index("published_at")
        await db.news_articles.create_index("source")
        await db.news_articles.create_index("story_cluster_id")
        await db.news_articles.create_index("impact_score")
        
        # Story clusters indexes
        await db.story_clusters.create_index("cluster_id", unique=True)
        await db.story_clusters.create_index("impact_score")
        await db.story_clusters.create_index("first_seen")
        await db.story_clusters.create_index("analysis_complete")
        
        # News analyses indexes
        await db.news_analyses.create_index("cluster_id", unique=True)
        await db.news_analyses.create_index("analysis_date")
        
        # Processing jobs indexes
        await db.processing_jobs.create_index("job_type")
        await db.processing_jobs.create_index("status")
        await db.processing_jobs.create_index("started_at")
        
        # Daily reports indexes
        await db.daily_reports.create_index("report_date", unique=True)
        await db.daily_reports.create_index("generation_time")
        
        logger.info("Database initialized with indexes")
        
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

# Collection helpers

async def save_news_article(article_data: dict):
    """Save news article to database"""
    db = await get_database()
    try:
        result = await db.news_articles.insert_one(article_data)
        return result.inserted_id
    except Exception as e:
        logger.error(f"Error saving news article: {str(e)}")
        raise

async def save_story_cluster(cluster_data: dict):
    """Save story cluster to database"""
    db = await get_database()
    try:
        result = await db.story_clusters.insert_one(cluster_data)
        return result.inserted_id
    except Exception as e:
        logger.error(f"Error saving story cluster: {str(e)}")
        raise

async def save_news_analysis(analysis_data: dict):
    """Save news analysis to database"""
    db = await get_database()
    try:
        result = await db.news_analyses.insert_one(analysis_data)
        return result.inserted_id
    except Exception as e:
        logger.error(f"Error saving news analysis: {str(e)}")
        raise

async def save_processing_job(job_data: dict):
    """Save processing job to database"""
    db = await get_database()
    try:
        result = await db.processing_jobs.insert_one(job_data)
        return result.inserted_id
    except Exception as e:
        logger.error(f"Error saving processing job: {str(e)}")
        raise

async def save_daily_report(report_data: dict):
    """Save daily report to database"""
    db = await get_database()
    try:
        result = await db.daily_reports.insert_one(report_data)
        return result.inserted_id
    except Exception as e:
        logger.error(f"Error saving daily report: {str(e)}")
        raise

async def get_articles_by_timeframe(hours: int = 24):
    """Get articles from the last N hours"""
    from datetime import datetime, timedelta
    
    db = await get_database()
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    cursor = db.news_articles.find({
        "published_at": {"$gte": cutoff_time}
    }).sort("published_at", -1)
    
    return await cursor.to_list(length=1000)

async def get_story_clusters_by_date(target_date):
    """Get story clusters for a specific date"""
    from datetime import datetime, timedelta
    
    db = await get_database()
    
    # Get clusters that were first seen on the target date
    start_of_day = datetime.combine(target_date, datetime.min.time())
    end_of_day = start_of_day + timedelta(days=1)
    
    cursor = db.story_clusters.find({
        "first_seen": {
            "$gte": start_of_day,
            "$lt": end_of_day
        }
    }).sort("impact_score", -1)
    
    return await cursor.to_list(length=100)

async def get_news_analysis_by_cluster_id(cluster_id: str):
    """Get news analysis by cluster ID"""
    db = await get_database()
    return await db.news_analyses.find_one({"cluster_id": cluster_id})

async def get_processing_jobs(job_type: str = None, status: str = None, limit: int = 20):
    """Get processing jobs with optional filters"""
    db = await get_database()
    
    query = {}
    if job_type:
        query["job_type"] = job_type
    if status:
        query["status"] = status
    
    cursor = db.processing_jobs.find(query).sort("started_at", -1).limit(limit)
    return await cursor.to_list(length=limit)

async def get_daily_report_by_date(report_date):
    """Get daily report by date"""
    db = await get_database()
    return await db.daily_reports.find_one({"report_date": report_date})

async def update_processing_job(job_id, update_data: dict):
    """Update processing job"""
    db = await get_database()
    result = await db.processing_jobs.update_one(
        {"_id": job_id},
        {"$set": update_data}
    )
    return result.modified_count > 0

async def health_check():
    """Database health check"""
    try:
        db = await get_database()
        # Simple ping to check connection
        await db.command("ping")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return False