"""
News Intelligence Platform - News API Endpoints
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import logging

from ..models.news_models import NewsArticle, StoryCluster, ProcessingJob
from ..services.feed_manager import NewsFeedManager
from ..services.story_clustering import StoryClusteringEngine
from ..services.impact_assessment import ImpactAssessmentEngine
from ..workers.daily_processor import daily_processor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/news", tags=["news"])

@router.get("/", summary="News Intelligence API Status")
async def news_api_status():
    """Get API status and configuration"""
    return {
        "message": "News Intelligence Platform API v1.0",
        "status": "operational",
        "features": {
            "feed_polling": "active",
            "story_clustering": "active", 
            "impact_assessment": "placeholder_ready",
            "dual_pipeline": "active",
            "report_generation": "active"
        },
        "processing": await daily_processor.get_processing_status(),
        "timestamp": datetime.utcnow().isoformat()
    }

@router.post("/poll-feeds", summary="Poll News Feeds")
async def poll_news_feeds():
    """Manually poll all configured news feeds"""
    try:
        feed_manager = NewsFeedManager()
        articles = await feed_manager.poll_all_feeds()
        
        return {
            "status": "success",
            "articles_collected": len(articles),
            "sources": list(set(article.source for article in articles)),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error polling feeds: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Feed polling failed: {str(e)}")

@router.post("/cluster-articles", summary="Cluster Articles into Stories")
async def cluster_articles(timeframe_hours: int = Query(24, description="Timeframe in hours to collect articles")):
    """Manually trigger article clustering"""
    try:
        feed_manager = NewsFeedManager()
        clustering_engine = StoryClusteringEngine()
        
        # Get recent articles
        articles = await feed_manager.get_articles_by_timeframe(timeframe_hours)
        
        if not articles:
            return {
                "status": "no_articles",
                "message": f"No articles found in last {timeframe_hours} hours",
                "clusters": []
            }
        
        # Cluster articles
        clusters = await clustering_engine.cluster_articles(articles)
        
        # Format response
        cluster_summaries = []
        for cluster in clusters:
            cluster_summaries.append({
                "cluster_id": cluster.cluster_id,
                "main_event": cluster.main_event,
                "article_count": len(cluster.articles),
                "source_diversity": cluster.source_diversity_score,
                "perspectives": cluster.perspective_coverage,
                "first_seen": cluster.first_seen.isoformat(),
                "sources": [article.source for article in cluster.articles]
            })
        
        return {
            "status": "success",
            "total_articles": len(articles),
            "clusters_created": len(clusters),
            "clusters": cluster_summaries,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error clustering articles: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Clustering failed: {str(e)}")

@router.post("/assess-impact", summary="Assess Story Impact")
async def assess_story_impact(timeframe_hours: int = Query(24), top_n: int = Query(25)):
    """Assess impact and rank top stories"""
    try:
        feed_manager = NewsFeedManager()
        clustering_engine = StoryClusteringEngine()
        impact_engine = ImpactAssessmentEngine()
        
        # Get and cluster articles
        articles = await feed_manager.get_articles_by_timeframe(timeframe_hours)
        clusters = await clustering_engine.cluster_articles(articles)
        
        # Rank by impact
        top_clusters = await impact_engine.rank_stories_by_impact(clusters, top_n)
        
        # Format response
        ranked_stories = []
        for i, cluster in enumerate(top_clusters, 1):
            ranked_stories.append({
                "rank": i,
                "cluster_id": cluster.cluster_id,
                "main_event": cluster.main_event,
                "impact_score": cluster.impact_score,
                "article_count": len(cluster.articles),
                "source_diversity": cluster.source_diversity_score,
                "first_seen": cluster.first_seen.isoformat()
            })
        
        return {
            "status": "success",
            "total_clusters": len(clusters),
            "top_stories": ranked_stories,
            "assessment_method": "placeholder" if not impact_engine.assessment_enabled else "external",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error assessing impact: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Impact assessment failed: {str(e)}")

@router.get("/processing-status", summary="Get Processing Status")
async def get_processing_status():
    """Get current processing status"""
    try:
        status = await daily_processor.get_processing_status()
        return status
    except Exception as e:
        logger.error(f"Error getting processing status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@router.post("/trigger-processing", summary="Trigger Manual Processing")
async def trigger_manual_processing(background_tasks: BackgroundTasks):
    """Trigger manual news processing cycle"""
    try:
        if daily_processor.is_processing:
            raise HTTPException(status_code=409, detail="Processing already in progress")
        
        job_id = await daily_processor.run_manual_processing()
        
        return {
            "status": "started",
            "job_id": job_id,
            "message": "Manual processing started",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Error triggering processing: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing trigger failed: {str(e)}")

@router.post("/cancel-processing", summary="Cancel Current Processing")
async def cancel_processing():
    """Cancel currently running processing"""
    try:
        cancelled = await daily_processor.cancel_current_processing()
        
        if cancelled:
            return {
                "status": "cancelled",
                "message": "Processing cancelled successfully",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "status": "no_processing",
                "message": "No processing currently running",
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error cancelling processing: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cancel failed: {str(e)}")

@router.get("/feeds-config", summary="Get Feed Configuration")
async def get_feeds_config():
    """Get current news feed configuration"""
    from ..core.config import FREE_NEWS_SOURCES
    
    return {
        "rss_feeds": FREE_NEWS_SOURCES["rss_feeds"],
        "total_feeds": len(FREE_NEWS_SOURCES["rss_feeds"]),
        "feed_categories": list(set(feed["category"] for feed in FREE_NEWS_SOURCES["rss_feeds"])),
        "perspectives_covered": list(set(feed["perspective"] for feed in FREE_NEWS_SOURCES["rss_feeds"]))
    }

@router.get("/test-extraction", summary="Test Content Extraction")
async def test_content_extraction(url: str = Query(..., description="URL to test content extraction")):
    """Test content extraction from a specific URL"""
    try:
        from ..utils.content_extractor import ContentExtractor
        
        extractor = ContentExtractor()
        content = await extractor.extract_content(url)
        metadata = await extractor.extract_metadata(url)
        
        return {
            "status": "success",
            "url": url,
            "content_length": len(content) if content else 0,
            "content_preview": content[:500] + "..." if content and len(content) > 500 else content,
            "metadata": metadata,
            "extraction_successful": content is not None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error testing extraction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Extraction test failed: {str(e)}")

@router.get("/recent-articles", summary="Get Recent Articles")
async def get_recent_articles(
    hours: int = Query(24, description="Hours to look back"),
    limit: int = Query(50, description="Maximum articles to return"),
    source: Optional[str] = Query(None, description="Filter by specific source")
):
    """Get recent articles from feeds"""
    try:
        feed_manager = NewsFeedManager()
        articles = await feed_manager.get_articles_by_timeframe(hours)
        
        # Filter by source if specified
        if source:
            articles = [article for article in articles if article.source == source]
        
        # Limit results
        articles = articles[:limit]
        
        # Format response
        article_summaries = []
        for article in articles:
            article_summaries.append({
                "title": article.title,
                "source": article.source,
                "perspective": article.source_perspective,
                "category": article.category,
                "published_at": article.published_at.isoformat(),
                "url": article.url,
                "word_count": article.word_count,
                "impact_score": article.impact_score
            })
        
        return {
            "status": "success",
            "articles": article_summaries,
            "total_found": len(articles),
            "timeframe_hours": hours,
            "filtered_by_source": source,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting recent articles: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Article retrieval failed: {str(e)}")