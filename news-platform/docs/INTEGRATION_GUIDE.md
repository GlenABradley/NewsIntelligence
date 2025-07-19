# Integration Guide: News Intelligence Platform

## 🎯 Overview

This guide explains how to integrate your existing algorithms and data science machine with the News Intelligence Platform.

## 🔧 Integration Points

### 1. Semantic Pattern Matching Integration

**Location**: `backend/services/story_clustering.py`

**Interface**: `StoryClusteringEngine.cluster_articles()`

```python
async def cluster_articles(self, articles: List[NewsArticle]) -> List[StoryCluster]:
    """
    REPLACE THIS METHOD with your semantic pattern matching algorithms
    
    Expected Input:
        articles: List of NewsArticle objects with title, content, source, etc.
    
    Expected Output:
        List of StoryCluster objects with grouped articles
    
    Your algorithm should:
        - Group articles about the same event/story
        - Use semantic similarity rather than keyword matching
        - Identify different perspectives on the same story
        - Return clusters with similarity scores
    """
    
    # YOUR SEMANTIC ALGORITHMS HERE
    # Example integration:
    
    # 1. Convert articles to your format
    your_format_articles = self._convert_to_your_format(articles)
    
    # 2. Call your clustering algorithm
    clusters = await your_semantic_engine.cluster_by_similarity(your_format_articles)
    
    # 3. Convert back to our format
    story_clusters = self._convert_to_story_clusters(clusters, articles)
    
    return story_clusters
```

**Additional methods to implement:**
- `analyze_semantic_similarity(text1, text2)` - Return similarity score 0-1
- `extract_story_entities(article)` - Extract key entities/topics
- `classify_story_type(article)` - Return story type classification
- `detect_duplicate_events(articles)` - Group articles about same event

### 2. Impact Assessment Data Science Machine

**Location**: `backend/services/impact_assessment.py`

**Integration Options:**

#### Option A: HTTP Service Integration
```python
# Configure your external service
await impact_engine.configure_external_service(
    endpoint="http://your-impact-service:8080/assess",
    auth_token="your_auth_token"
)
```

#### Option B: Direct Python Integration
```python
async def assess_article_impact(self, article: NewsArticle) -> float:
    """
    REPLACE with your impact assessment algorithm
    
    Expected Input:
        article: NewsArticle object with content, source, etc.
    
    Expected Output:
        Impact score (0.0 - 10.0 scale)
    """
    
    # YOUR IMPACT ASSESSMENT HERE
    # Example integration:
    
    features = your_feature_extractor.extract_features(article)
    impact_score = your_impact_model.predict(features)
    
    return float(impact_score)
```

**Data Science Interface:**
```python
class ImpactDataScienceInterface:
    async def calculate_social_impact(self, content: str) -> float:
        # Your social impact algorithm
        pass
    
    async def assess_political_significance(self, content: str) -> float:
        # Your political significance algorithm
        pass
    
    async def measure_economic_impact(self, content: str) -> float:
        # Your economic impact algorithm
        pass
    
    async def predict_story_trajectory(self, articles: List[NewsArticle]) -> Dict:
        # Your story trajectory prediction
        pass
```

### 3. External News APIs Integration

**Location**: `backend/services/feed_manager.py`

**Add your API keys to `.env`:**
```env
NEWSAPI_KEY=your_newsapi_key
REUTERS_API_KEY=your_reuters_key
AP_NEWS_API_KEY=your_ap_key
```

**Implement API methods:**
```python
async def get_newsapi_headlines(self, query: str = None) -> List[NewsArticle]:
    """Implement NewsAPI.org integration"""
    headers = {"X-API-Key": self.newsapi_key}
    # Your API implementation here
    pass

async def get_reuters_headlines(self) -> List[NewsArticle]:
    """Implement Reuters API integration"""
    # Your API implementation here
    pass
```

## 📊 Data Flow Integration

### Your Algorithm Integration Points:

```
1. RSS Feeds → Articles Collection
2. [YOUR SEMANTIC CLUSTERING] → Story Groups  
3. [YOUR IMPACT ASSESSMENT] → Story Ranking
4. Dual Pipeline Analysis → Factual/Emotional Separation
5. Report Generation → Professional Output
```

### Expected Data Formats:

**Input to your clustering algorithm:**
```python
articles = [
    {
        "title": "Article title",
        "content": "Full article text...",
        "source": "BBC World News",
        "published_at": datetime,
        "url": "https://...",
        "source_perspective": "center-international"
    }
]
```

**Output from your clustering:**
```python
clusters = [
    {
        "cluster_id": "unique_id",
        "main_event": "Event description",
        "articles": [article_objects],
        "similarity_score": 0.95
    }
]
```

**Input to your impact assessment:**
```python
{
    "title": "Article title",
    "content": "Full content",
    "source": "Source name",
    "published_at": "2024-01-15T10:30:00Z",
    "metadata": {...}
}
```

**Output from your impact assessment:**
```python
{
    "impact_score": 8.5,  # 0-10 scale
    "confidence": 0.92,   # 0-1 scale
    "factors": {
        "social_impact": 0.8,
        "political_significance": 0.9,
        "economic_impact": 0.6,
        "viral_probability": 0.7
    }
}
```

## 🔌 Configuration

### Environment Variables for Your Services:

```env
# Your Semantic Engine
SEMANTIC_MATCHING_ENABLED=true
SEMANTIC_MATCHING_ENDPOINT=http://your-semantic-service:8080

# Your Impact Assessment
IMPACT_ASSESSMENT_ENABLED=true
IMPACT_ASSESSMENT_ENDPOINT=http://your-impact-service:8080
IMPACT_ASSESSMENT_AUTH_TOKEN=your_token

# Your API Keys
NEWSAPI_KEY=your_newsapi_key
REUTERS_API_KEY=your_reuters_key
```

### Database Integration:

Your algorithms can access the same MongoDB instance:
```python
from backend.core.database import get_database

async def your_algorithm():
    db = await get_database()
    articles = await db.news_articles.find().to_list(1000)
    # Process with your algorithms
```

## 🧪 Testing Your Integration

### 1. Test Semantic Clustering:
```bash
curl -X POST "http://localhost:8001/api/news/cluster-articles?timeframe_hours=6"
```

### 2. Test Impact Assessment:
```bash
curl -X POST "http://localhost:8001/api/news/assess-impact?timeframe_hours=6&top_n=10"
```

### 3. Test Full Pipeline:
```bash
curl -X POST "http://localhost:8001/api/news/trigger-processing"
```

### 4. Monitor Processing:
```bash
curl "http://localhost:8001/api/news/processing-status"
```

## 📈 Performance Considerations

### Semantic Clustering:
- **Expected Load**: 100-500 articles per processing cycle
- **Frequency**: Once daily + manual triggers
- **Timeout**: Configure clustering to complete within 10 minutes
- **Memory**: Plan for ~1GB RAM for processing 500 articles

### Impact Assessment:
- **Expected Load**: 50-100 story clusters per cycle
- **Frequency**: Once per story cluster
- **Timeout**: Configure assessment to complete within 30 seconds per story
- **API Rate Limits**: Plan for burst processing of 25 stories

## 🛠️ Development Workflow

### 1. Development Setup:
```bash
# Setup virtual environment with your dependencies
cd backend
pip install -r requirements.txt
pip install your-semantic-package
pip install your-impact-package

# Add your modules to the requirements.txt
echo "your-semantic-package==1.0.0" >> requirements.txt
echo "your-impact-package==1.0.0" >> requirements.txt
```

### 2. Testing Integration:
```python
# Test your algorithms in isolation
from your_semantic_engine import SemanticCluster
from your_impact_engine import ImpactAssessment

# Test with sample data
articles = load_sample_articles()
clusters = SemanticCluster.cluster(articles)
scores = ImpactAssessment.assess(clusters)
```

### 3. Integration Testing:
```bash
# Test with small dataset
curl -X POST "http://localhost:8001/api/news/poll-feeds"
curl -X POST "http://localhost:8001/api/news/cluster-articles?timeframe_hours=1"
```

## 🔐 Security Considerations

### API Keys:
- Store in environment variables, never in code
- Use different keys for development/production
- Implement rate limiting for your services

### Service Communication:
- Use HTTPS for production deployments
- Implement authentication between services
- Add input validation for your algorithms

## 📞 Support

### Integration Checklist:

- [ ] Semantic clustering algorithm integrated
- [ ] Impact assessment algorithm integrated  
- [ ] External APIs configured (if available)
- [ ] Environment variables set
- [ ] Integration testing completed
- [ ] Performance benchmarking done
- [ ] Error handling implemented
- [ ] Logging configured

### Common Issues:

1. **Timeout Errors**: Adjust processing timeouts in config
2. **Memory Issues**: Implement batch processing for large datasets
3. **API Rate Limits**: Add exponential backoff and retry logic
4. **Data Format Mismatches**: Use conversion utilities provided

### Next Steps:

1. Integrate your semantic clustering algorithm
2. Integrate your impact assessment data science machine
3. Test with small datasets
4. Scale testing with full daily processing
5. Configure production deployment

---

**Ready for Integration**: All interfaces are prepared and documented for your algorithms.