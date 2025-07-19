"""
News Intelligence Platform - Enhanced Content Extraction
Optimized for news article content extraction from URLs
"""
import asyncio
import aiohttp
from typing import Optional, Dict, Any
import logging
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

class ContentExtractor:
    """
    Enhanced content extractor optimized for news articles
    """
    
    def __init__(self):
        self.timeout = aiohttp.ClientTimeout(total=30)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
    async def extract_content(self, url: str) -> Optional[str]:
        """
        Extract main article content from news URL
        
        Args:
            url: Article URL to extract content from
            
        Returns:
            Extracted article text or None if extraction fails
        """
        try:
            async with aiohttp.ClientSession(timeout=self.timeout, headers=self.headers) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.warning(f"HTTP {response.status} for URL: {url}")
                        return None
                    
                    html_content = await response.text()
                    
                    # Extract content using multiple strategies
                    content = self._extract_article_content(html_content, url)
                    
                    if content and len(content.strip()) > 100:
                        return self._clean_extracted_content(content)
                    else:
                        logger.warning(f"Insufficient content extracted from: {url}")
                        return None
                        
        except asyncio.TimeoutError:
            logger.error(f"Timeout extracting content from: {url}")
            return None
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {str(e)}")
            return None
    
    def _extract_article_content(self, html: str, url: str) -> Optional[str]:
        """
        Extract article content using multiple extraction strategies
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Strategy 1: Look for structured data (JSON-LD)
        content = self._extract_from_structured_data(soup)
        if content:
            return content
        
        # Strategy 2: Look for news-specific selectors
        content = self._extract_from_news_selectors(soup)
        if content:
            return content
        
        # Strategy 3: Look for article tags and common patterns
        content = self._extract_from_article_tags(soup)
        if content:
            return content
        
        # Strategy 4: Fallback to content heuristics
        content = self._extract_with_heuristics(soup)
        return content
    
    def _extract_from_structured_data(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract content from JSON-LD structured data"""
        try:
            import json
            
            # Look for JSON-LD scripts
            json_scripts = soup.find_all('script', type='application/ld+json')
            
            for script in json_scripts:
                try:
                    data = json.loads(script.string)
                    
                    # Handle both single objects and arrays
                    if isinstance(data, list):
                        data = data[0] if data else {}
                    
                    # Look for article content
                    if data.get('@type') in ['Article', 'NewsArticle']:
                        article_body = data.get('articleBody')
                        if article_body and len(article_body) > 100:
                            return article_body
                            
                except (json.JSONDecodeError, TypeError):
                    continue
                    
        except Exception as e:
            logger.debug(f"Error extracting structured data: {e}")
            
        return None
    
    def _extract_from_news_selectors(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract using news-specific CSS selectors"""
        
        # Common news site selectors
        news_selectors = [
            # Generic article selectors
            'article [data-module="ArticleBody"]',
            'article .article-body',
            'article .story-body',
            'article .entry-content',
            'article .post-content',
            
            # Specific news sites
            '.story-body__inner',  # BBC
            '.ArticleBody-articleBody',  # CNN
            '.story-text',  # Reuters
            '.story-content',  # Generic
            '.article-content',  # Generic
            '.post-body',  # Generic
            
            # Fallback article selectors
            'article',
            '[role="main"] article',
            '.main-content article'
        ]
        
        for selector in news_selectors:
            try:
                elements = soup.select(selector)
                if elements:
                    content = self._extract_text_from_elements(elements)
                    if content and len(content) > 200:
                        return content
            except Exception:
                continue
                
        return None
    
    def _extract_from_article_tags(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract content from article tags and semantic HTML"""
        
        # Look for semantic article elements
        content_elements = []
        
        # Article tag
        article = soup.find('article')
        if article:
            content_elements.append(article)
        
        # Main content areas
        main = soup.find('main')
        if main:
            content_elements.append(main)
        
        # Look for elements with article-related classes
        article_divs = soup.find_all('div', class_=re.compile(r'(article|story|content|post)', re.I))
        content_elements.extend(article_divs[:3])  # Limit to first 3
        
        for element in content_elements:
            content = self._extract_text_from_elements([element])
            if content and len(content) > 200:
                return content
                
        return None
    
    def _extract_with_heuristics(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract content using heuristics (paragraph density, text length, etc.)
        """
        # Remove unwanted elements
        self._remove_unwanted_elements(soup)
        
        # Find all paragraph-like elements
        text_elements = soup.find_all(['p', 'div'], string=True)
        
        # Score elements by content quality
        scored_elements = []
        for elem in text_elements:
            text = elem.get_text().strip()
            if len(text) > 50:  # Minimum meaningful text length
                score = self._calculate_content_score(elem, text)
                scored_elements.append((score, text))
        
        # Sort by score and combine top elements
        scored_elements.sort(reverse=True)
        
        if scored_elements:
            # Take elements that score above threshold
            threshold = max(scored_elements[0][0] * 0.3, 1.0)  # 30% of top score, min 1.0
            good_content = [text for score, text in scored_elements if score >= threshold]
            
            if good_content:
                return '\n\n'.join(good_content[:20])  # Limit to top 20 paragraphs
        
        return None
    
    def _extract_text_from_elements(self, elements) -> str:
        """Extract clean text from list of elements"""
        texts = []
        
        for element in elements:
            # Remove unwanted child elements
            for unwanted in element.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                unwanted.decompose()
            
            # Get text and clean it
            text = element.get_text(separator='\n', strip=True)
            if text:
                texts.append(text)
        
        return '\n\n'.join(texts)
    
    def _remove_unwanted_elements(self, soup: BeautifulSoup):
        """Remove elements that typically don't contain article content"""
        
        unwanted_tags = ['script', 'style', 'nav', 'header', 'footer', 'aside', 'form']
        unwanted_classes = ['advertisement', 'ad', 'social', 'share', 'comment', 'sidebar', 'related']
        
        # Remove by tag
        for tag in unwanted_tags:
            for element in soup.find_all(tag):
                element.decompose()
        
        # Remove by class
        for class_name in unwanted_classes:
            for element in soup.find_all(class_=re.compile(class_name, re.I)):
                element.decompose()
    
    def _calculate_content_score(self, element, text: str) -> float:
        """Calculate content quality score for an element"""
        score = 0.0
        
        # Length score (favor longer paragraphs)
        score += min(len(text) / 100, 5.0)
        
        # Sentence score (favor elements with multiple sentences)
        sentences = text.count('.') + text.count('!') + text.count('?')
        score += min(sentences * 0.5, 3.0)
        
        # Word count score
        words = len(text.split())
        score += min(words / 20, 3.0)
        
        # Penalty for elements with many links
        if element.find_all('a'):
            link_ratio = len(element.find_all('a')) / max(words / 10, 1)
            score -= min(link_ratio, 2.0)
        
        # Bonus for paragraph tags
        if element.name == 'p':
            score += 1.0
        
        # Penalty for very short elements
        if len(text) < 50:
            score -= 2.0
        
        return max(score, 0.0)
    
    def _clean_extracted_content(self, content: str) -> str:
        """Clean and normalize extracted content"""
        
        # Remove excessive whitespace
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = re.sub(r'\s+', ' ', content)
        
        # Remove common boilerplate patterns
        boilerplate_patterns = [
            r'Click here to.*',
            r'Read more:.*',
            r'Subscribe to.*',
            r'Follow us on.*',
            r'Share this.*',
            r'Advertisement\s*',
            r'Related articles?:.*',
        ]
        
        for pattern in boilerplate_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        # Clean up line breaks and spacing
        content = content.strip()
        content = re.sub(r'\n\s*\n', '\n\n', content)
        
        return content
    
    async def extract_metadata(self, url: str) -> Dict[str, Any]:
        """
        Extract article metadata (title, description, publish date, etc.)
        """
        try:
            async with aiohttp.ClientSession(timeout=self.timeout, headers=self.headers) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return {}
                    
                    html_content = await response.text()
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    metadata = {}
                    
                    # Extract title
                    title = soup.find('title')
                    if title:
                        metadata['title'] = title.get_text().strip()
                    
                    # Extract meta description
                    desc = soup.find('meta', attrs={'name': 'description'})
                    if desc:
                        metadata['description'] = desc.get('content', '').strip()
                    
                    # Extract publish date
                    date_selectors = [
                        'meta[property="article:published_time"]',
                        'meta[name="publish-date"]',
                        'meta[name="date"]',
                        'time[datetime]'
                    ]
                    
                    for selector in date_selectors:
                        date_elem = soup.select_one(selector)
                        if date_elem:
                            date_value = date_elem.get('content') or date_elem.get('datetime')
                            if date_value:
                                metadata['published_date'] = date_value
                                break
                    
                    # Extract author
                    author_selectors = [
                        'meta[name="author"]',
                        'meta[property="article:author"]',
                        '.author',
                        '.byline'
                    ]
                    
                    for selector in author_selectors:
                        author_elem = soup.select_one(selector)
                        if author_elem:
                            author = author_elem.get('content') or author_elem.get_text()
                            if author:
                                metadata['author'] = author.strip()
                                break
                    
                    return metadata
                    
        except Exception as e:
            logger.error(f"Error extracting metadata from {url}: {str(e)}")
            return {}