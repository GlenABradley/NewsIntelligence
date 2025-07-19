"""
News Intelligence Platform - Core Configuration
"""
import os
from typing import List, Dict
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
from datetime import time
import pytz

class Settings(BaseSettings):
    # Database Configuration
    MONGO_URL: str = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    DATABASE_NAME: str = "news_intelligence"
    
    # News Processing Configuration
    DAILY_PROCESSING_TIME: str = "12:00"  # Noon Eastern
    TIMEZONE: str = "America/New_York"
    MAX_ARTICLES_PER_STORY: int = 50
    TOP_STORIES_COUNT: int = 25
    
    # Feed Configuration
    FEED_POLL_INTERVAL: int = 300  # 5 minutes
    CONTENT_EXTRACTION_TIMEOUT: int = 30
    
    # Report Configuration
    REPORTS_BASE_PATH: str = "/app/news-platform/data/reports"
    EXPORT_FORMATS: str = "markdown,pdf,json"  # Will be split into list
    
    # Impact Assessment (Placeholder for your data science machine)
    IMPACT_ASSESSMENT_ENABLED: bool = False  # Your module will enable this
    IMPACT_ASSESSMENT_ENDPOINT: str = ""  # Your service endpoint
    
    # External API Placeholders (for when you get keys)
    NEWSAPI_KEY: str = os.getenv("NEWSAPI_KEY", "")
    REUTERS_API_KEY: str = os.getenv("REUTERS_API_KEY", "")
    
    # Processing Configuration
    ENABLE_MANUAL_PROCESSING: bool = True  # Allow manual triggers for testing
    
    @property
    def export_formats_list(self) -> List[str]:
        """Convert export formats string to list"""
        return [fmt.strip() for fmt in self.EXPORT_FORMATS.split(",")]
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

# Free News Sources Configuration
FREE_NEWS_SOURCES = {
    "rss_feeds": [
        {
            "name": "BBC World News",
            "url": "http://feeds.bbci.co.uk/news/world/rss.xml",
            "category": "international",
            "perspective": "center-international"
        },
        {
            "name": "Reuters Top News",
            "url": "http://feeds.reuters.com/reuters/topNews",
            "category": "breaking",
            "perspective": "center-wire"
        },
        {
            "name": "AP News",
            "url": "https://rsshub.app/ap/topics/apf-topnews",
            "category": "breaking",
            "perspective": "center-wire"
        },
        {
            "name": "NPR News",
            "url": "https://feeds.npr.org/1001/rss.xml",
            "category": "national",
            "perspective": "center-left"
        },
        {
            "name": "CNN Top Stories",
            "url": "http://rss.cnn.com/rss/edition.rss",
            "category": "breaking",
            "perspective": "center-left"
        },
        {
            "name": "Fox News",
            "url": "http://feeds.foxnews.com/foxnews/latest",
            "category": "breaking", 
            "perspective": "center-right"
        },
        {
            "name": "Washington Post",
            "url": "http://feeds.washingtonpost.com/rss/national",
            "category": "national",
            "perspective": "center-left"
        },
        {
            "name": "Wall Street Journal",
            "url": "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
            "category": "business",
            "perspective": "center-right"
        },
        {
            "name": "Guardian World",
            "url": "https://www.theguardian.com/world/rss",
            "category": "international",
            "perspective": "left-international"
        },
        {
            "name": "Al Jazeera",
            "url": "https://www.aljazeera.com/xml/rss/all.xml",
            "category": "international",
            "perspective": "international-middle-east"
        }
    ]
}