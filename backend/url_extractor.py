import requests
import newspaper
from newspaper import Article
from bs4 import BeautifulSoup
from readability import Document
import html2text
import logging
from typing import Dict, Optional
import re
from urllib.parse import urlparse
import time

logger = logging.getLogger(__name__)

class URLContentExtractor:
    """Robust URL content extraction with multiple fallback methods"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.timeout = 10
        
    def extract_article_content(self, url: str) -> Dict[str, str]:
        """
        Extract article content from URL using multiple methods
        Returns: {title, content, source_domain, success, error}
        """
        try:
            # Validate URL
            if not self._is_valid_url(url):
                return {
                    "title": "",
                    "content": "",
                    "source_domain": "",
                    "success": False,
                    "error": "Invalid URL format"
                }
            
            source_domain = urlparse(url).netloc
            logger.info(f"Extracting content from: {source_domain}")
            
            # Method 1: newspaper3k (best for news articles)
            result = self._extract_with_newspaper(url)
            if result["success"]:
                result["source_domain"] = source_domain
                return result
            
            # Method 2: readability + BeautifulSoup
            result = self._extract_with_readability(url)
            if result["success"]:
                result["source_domain"] = source_domain
                return result
                
            # Method 3: Basic BeautifulSoup fallback
            result = self._extract_with_beautifulsoup(url)
            result["source_domain"] = source_domain
            return result
            
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {str(e)}")
            return {
                "title": "",
                "content": "",
                "source_domain": urlparse(url).netloc if self._is_valid_url(url) else "",
                "success": False,
                "error": f"Extraction failed: {str(e)}"
            }
    
    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def _extract_with_newspaper(self, url: str) -> Dict[str, str]:
        """Extract using newspaper3k library"""
        try:
            article = Article(url)
            article.download()
            article.parse()
            
            if article.text and len(article.text.strip()) > 100:
                return {
                    "title": article.title or "Untitled Article",
                    "content": article.text.strip(),
                    "success": True,
                    "error": None
                }
            else:
                return {"success": False, "error": "Insufficient content extracted"}
                
        except Exception as e:
            logger.warning(f"Newspaper extraction failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _extract_with_readability(self, url: str) -> Dict[str, str]:
        """Extract using readability + BeautifulSoup"""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # Use readability to extract main content
            doc = Document(response.content)
            readable_html = doc.summary()
            
            # Convert to plain text
            soup = BeautifulSoup(readable_html, 'html.parser')
            
            # Extract title
            title = doc.title() or soup.find('h1')
            if title and hasattr(title, 'get_text'):
                title = title.get_text().strip()
            elif isinstance(title, str):
                title = title.strip()
            else:
                title = "Untitled Article"
            
            # Extract content
            content = soup.get_text()
            content = self._clean_text(content)
            
            if len(content.strip()) > 100:
                return {
                    "title": title,
                    "content": content,
                    "success": True,
                    "error": None
                }
            else:
                return {"success": False, "error": "Insufficient content after readability extraction"}
                
        except Exception as e:
            logger.warning(f"Readability extraction failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _extract_with_beautifulsoup(self, url: str) -> Dict[str, str]:
        """Fallback extraction using BeautifulSoup"""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
                script.decompose()
            
            # Try to find title
            title = soup.find('title')
            if title:
                title = title.get_text().strip()
            else:
                title = soup.find('h1')
                title = title.get_text().strip() if title else "Untitled Article"
            
            # Try to find main content area
            content_selectors = [
                'article', '[role="main"]', '.article-content', '.post-content',
                '.entry-content', '.content', 'main', '.article-body'
            ]
            
            content = ""
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    content = elements[0].get_text()
                    break
            
            # Fallback to body if no specific content found
            if not content:
                body = soup.find('body')
                if body:
                    content = body.get_text()
            
            content = self._clean_text(content)
            
            if len(content.strip()) > 100:
                return {
                    "title": title,
                    "content": content,
                    "success": True,
                    "error": None
                }
            else:
                return {
                    "title": title,
                    "content": content,
                    "success": False,
                    "error": "Insufficient content extracted with BeautifulSoup"
                }
                
        except Exception as e:
            logger.error(f"BeautifulSoup extraction failed: {str(e)}")
            return {
                "title": "",
                "content": "",
                "success": False,
                "error": str(e)
            }
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common noise patterns
        noise_patterns = [
            r'Cookie.*?Accept',
            r'Subscribe.*?Newsletter',
            r'Follow us on.*?Twitter',
            r'Share.*?Facebook',
            r'Advertisement',
            r'Loading\.\.\.',
        ]
        
        for pattern in noise_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Clean up extra spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

# Global extractor instance
url_extractor = URLContentExtractor()

def extract_content_from_url(url: str) -> Dict[str, str]:
    """Convenience function for URL content extraction"""
    return url_extractor.extract_article_content(url)