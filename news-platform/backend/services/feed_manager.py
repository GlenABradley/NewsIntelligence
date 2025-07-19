"""
News Intelligence Platform - Feed Management Service
Handles RSS feed polling and article extraction from free sources
"""
import asyncio
import aiohttp
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import hashlib
import re
from bs4 import BeautifulSoup
import logging

from core.config import settings, FREE_NEWS_SOURCES
from models.news_models import NewsArticle
from utils.content_extractor import ContentExtractor

logger = logging.getLogger(__name__)

class NewsFeedManager:
    """Manages polling of free RSS feeds and article extraction"""
    
    def __init__(self):
        self.content_extractor = ContentExtractor()
        self.seen_urls = set()  # Simple deduplication
        
    async def poll_all_feeds(self) -> List[NewsArticle]:
        """Poll all configured RSS feeds and return new articles"""
        all_articles = []
        
        for feed_config in FREE_NEWS_SOURCES["rss_feeds"]:
            try:
                logger.info(f"Polling feed: {feed_config['name']}")
                articles = await self._poll_single_feed(feed_config)
                all_articles.extend(articles)
                logger.info(f"Got {len(articles)} articles from {feed_config['name']}")
            except Exception as e:
                logger.error(f"Error polling {feed_config['name']}: {str(e)}")
                continue
                
        # Deduplicate articles
        unique_articles = self._deduplicate_articles(all_articles)
        logger.info(f"Total unique articles: {len(unique_articles)}")
        
        return unique_articles
    
    async def _poll_single_feed(self, feed_config: Dict) -> List[NewsArticle]:
        """Poll a single RSS feed"""
        articles = []
        
        try:
            # Parse RSS feed
            feed = feedparser.parse(feed_config["url"])
            
            if feed.bozo:
                logger.warning(f"Feed parsing issues for {feed_config['name']}: {feed.bozo_exception}")
            
            # Process each entry
            for entry in feed.entries[:20]:  # Limit to latest 20 per feed
                try:
                    article = await self._process_feed_entry(entry, feed_config)
                    if article:
                        articles.append(article)
                except Exception as e:
                    logger.error(f"Error processing entry from {feed_config['name']}: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error fetching feed {feed_config['url']}: {str(e)}")
            
        return articles
    
    async def _process_feed_entry(self, entry, feed_config: Dict) -> Optional[NewsArticle]:
        """Process a single RSS entry into a NewsArticle"""
        
        # Skip if we've seen this URL
        if entry.link in self.seen_urls:
            return None
            
        # Extract publication date
        published_at = self._parse_published_date(entry)
        
        # Skip articles older than 24 hours for daily processing
        if published_at and published_at < datetime.utcnow() - timedelta(hours=24):
            return None
            
        # Extract full content
        content = await self._extract_full_content(entry.link)
        if not content:
            content = self._extract_summary_from_entry(entry)
            
        # Create article
        article = NewsArticle(
            url=entry.link,
            title=entry.title,
            content=content,
            summary=self._extract_summary_from_entry(entry),
            source=feed_config["name"],
            source_perspective=feed_config["perspective"],
            category=feed_config["category"],
            published_at=published_at or datetime.utcnow(),
            word_count=len(content.split()) if content else 0
        )
        
        # Mark as seen
        self.seen_urls.add(entry.link)
        
        return article
    
    async def _extract_full_content(self, url: str) -> Optional[str]:
        """Extract full article content from URL"""
        try:
            return await self.content_extractor.extract_content(url)
        except Exception as e:
            logger.error(f"Content extraction failed for {url}: {str(e)}")
            return None
    
    def _extract_summary_from_entry(self, entry) -> str:
        """Extract summary/description from RSS entry"""
        summary = ""
        
        if hasattr(entry, 'summary'):
            summary = entry.summary
        elif hasattr(entry, 'description'):
            summary = entry.description
        elif hasattr(entry, 'content'):
            if isinstance(entry.content, list) and entry.content:
                summary = entry.content[0].value
            else:
                summary = str(entry.content)
                
        # Clean HTML tags
        if summary:
            soup = BeautifulSoup(summary, 'html.parser')
            summary = soup.get_text().strip()
            
        return summary
    
    def _parse_published_date(self, entry) -> Optional[datetime]:
        """Parse publication date from RSS entry"""
        try:
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                return datetime(*entry.published_parsed[:6])
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                return datetime(*entry.updated_parsed[:6])
        except Exception:
            pass
            
        return None
    
    def _deduplicate_articles(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        """Remove duplicate articles based on title similarity and URL"""
        seen_titles = {}
        unique_articles = []
        
        for article in articles:
            # Create a hash of the title for comparison
            title_hash = hashlib.md5(article.title.lower().encode()).hexdigest()
            
            if title_hash not in seen_titles:
                seen_titles[title_hash] = article
                unique_articles.append(article)
            else:
                # Keep the one with more content
                existing = seen_titles[title_hash]
                if len(article.content) > len(existing.content):
                    # Replace existing with current
                    unique_articles.remove(existing)
                    unique_articles.append(article)
                    seen_titles[title_hash] = article
                    
        return unique_articles
    
    async def get_articles_by_timeframe(self, hours: int = 24) -> List[NewsArticle]:
        """Get articles from the last N hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        articles = await self.poll_all_feeds()
        
        return [
            article for article in articles 
            if article.published_at >= cutoff_time
        ]

# External API Placeholders (ready for when you get API keys)
class ExternalNewsAPIs:
    """Placeholder for premium news API integrations"""
    
    def __init__(self):
        self.newsapi_key = settings.NEWSAPI_KEY
        self.reuters_key = settings.REUTERS_API_KEY
    
    async def get_newsapi_headlines(self, query: str = None) -> List[NewsArticle]:
        """
        PLACEHOLDER: NewsAPI.org integration
        Will return articles when API key is provided
        """
        if not self.newsapi_key:
            logger.info("NewsAPI key not configured, skipping")
            return []
            
        # TODO: Implement NewsAPI integration
        logger.info("NewsAPI integration ready for implementation")
        return []
    
    async def get_reuters_headlines(self) -> List[NewsArticle]:
        """
        PLACEHOLDER: Reuters API integration
        Will return articles when API key is provided
        """
        if not self.reuters_key:
            logger.info("Reuters API key not configured, skipping")
            return []
            
        # TODO: Implement Reuters API integration
        logger.info("Reuters API integration ready for implementation")
        return []
    
    async def get_ap_news_feed(self) -> List[NewsArticle]:
        """
        PLACEHOLDER: Associated Press API integration
        Will return articles when API key is provided
        """
        # TODO: Implement AP News API integration
        logger.info("AP News API integration ready for implementation")
        return []