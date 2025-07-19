# News Intelligence Platform

**Automated news aggregation, analysis, and professional report generation for news anchors and journalists.**

## 🎯 Overview

The News Intelligence Platform is a sophisticated AI-powered system that:

1. **Aggregates news** from diverse sources (RSS feeds + external APIs)
2. **Clusters similar stories** using semantic pattern matching
3. **Assesses impact** using configurable data science algorithms
4. **Analyzes content** through dual pipeline (factual vs emotional separation)
5. **Generates professional reports** ready for news anchors and journalists

## 🏗️ Architecture

### Core Components

- **Feed Manager**: Polls RSS feeds and external news APIs
- **Story Clustering**: Groups articles about the same events (your semantic algorithms)
- **Impact Assessment**: Ranks stories by importance (your data science machine)
- **Dual Pipeline**: Separates factual claims from emotional content
- **Report Generator**: Creates professional journalist-ready reports

### Daily Workflow

```
12:00 PM Eastern → Poll feeds → Cluster stories → Assess impact → 
Select top 25 → Dual pipeline analysis → Generate reports → 
Ready for human review
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- MongoDB
- Node.js (for frontend)

### Installation

1. **Clone and setup backend:**
```bash
cd news-platform/backend
pip install -r requirements.txt
cp .env.example .env
```

2. **Configure environment:**
Edit `.env` file with your settings:
```env
MONGO_URL=mongodb://localhost:27017
DAILY_PROCESSING_TIME=12:00
TIMEZONE=America/New_York
```

3. **Start the application:**
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

4. **Access the API:**
- API Documentation: http://localhost:8001/docs
- Health Check: http://localhost:8001/health

## 📋 API Endpoints

### News Processing
- `GET /api/news/` - API status and configuration
- `POST /api/news/poll-feeds` - Manually poll news feeds
- `POST /api/news/cluster-articles` - Cluster articles into stories
- `POST /api/news/assess-impact` - Assess and rank story impact
- `POST /api/news/trigger-processing` - Trigger manual processing cycle
- `GET /api/news/processing-status` - Get current processing status

### Report Management
- `GET /api/reports/daily/{date}` - Get daily report files
- `GET /api/reports/download/{date}/{story_id}/{type}` - Download specific report
- `GET /api/reports/summary/{date}` - Get daily summary
- `GET /api/reports/search?query=...` - Search through reports

## 🔧 Integration Points

### Your Semantic Pattern Matching
Replace placeholder in `services/story_clustering.py`:
```python
class StoryClusteringEngine:
    async def cluster_articles(self, articles):
        # YOUR SEMANTIC ALGORITHMS HERE
        pass
```

### Your Impact Assessment Data Science Machine
Configure in `services/impact_assessment.py`:
```python
await engine.configure_external_service(
    endpoint="your_impact_service_url",
    auth_token="your_auth_token"
)
```

## 📊 Output Structure

Daily reports are organized as:
```
/reports/YYYY-MM-DD/
├── story-01-ukraine-conflict/
│   ├── comprehensive-report.md
│   ├── anchor-briefing.json
│   ├── source-analysis.json
│   └── factual-emotional-breakdown.json
├── story-02-climate-summit/
│   └── ...
└── daily-summary.md
```

## 🎛️ Configuration

### News Sources
Free RSS feeds are configured in `config/news_sources.json`. Current sources include:
- BBC World News
- Reuters Top News
- AP News
- NPR News
- CNN, Fox News
- Washington Post, Wall Street Journal
- Guardian, Al Jazeera

### Processing Schedule
- **Automatic**: Daily at Noon Eastern time
- **Manual**: Trigger via API for testing
- **Configurable**: Adjust time in settings

### External APIs (Ready for Integration)
- NewsAPI.org (when you get API key)
- Reuters API (when you get API key)
- Associated Press API (when you get API key)

## 🧪 Testing

### Manual Processing (for testing)
```bash
curl -X POST "http://localhost:8001/api/news/trigger-processing"
```

### Check Processing Status
```bash
curl "http://localhost:8001/api/news/processing-status"
```

### Test Feed Polling
```bash
curl -X POST "http://localhost:8001/api/news/poll-feeds"
```

## 📈 Features

### ✅ Implemented
- RSS feed polling from 10 diverse sources
- Basic story clustering (placeholder for your algorithms)
- Impact assessment framework (placeholder for your data science)
- Dual pipeline factual/emotional analysis
- Professional report generation (Markdown + JSON)
- Automated daily processing
- Manual processing triggers
- Complete API for monitoring and control

### 🔄 Ready for Your Integration
- **Semantic Pattern Matching**: Interface ready for your algorithms
- **Impact Assessment**: Placeholder for your data science machine
- **External APIs**: Configured for premium news services
- **PDF Export**: Framework ready for implementation

### 🎯 Output Quality
- **Professional Reports**: Broadcast-ready format
- **Journalist Briefings**: Key facts and talking points
- **Source Analysis**: Perspective diversity and reliability
- **Factual Consensus**: Cross-source verification
- **Emotional Spectrum**: Sentiment analysis across sources

## 🔐 Production Considerations

### Security (Not Yet Implemented)
- Add authentication for API endpoints
- Input validation and sanitization
- Rate limiting

### Performance (Basic Implementation)
- Currently handles moderate loads
- Memory management for large article sets
- Database indexing implemented

### Monitoring (Basic Logging)
- Structured logging in place
- Health check endpoints available
- Processing status tracking

## 🛠️ Development

### Architecture Decisions
- **FastAPI**: Modern async Python web framework
- **MongoDB**: Document database for flexible news data
- **Dual Pipeline**: Separates factual from emotional content
- **Modular Design**: Easy integration of your algorithms

### Code Structure
- `services/`: Business logic modules
- `api/`: REST API endpoints  
- `models/`: Data models and schemas
- `workers/`: Background processing
- `utils/`: Utility functions
- `core/`: Configuration and database

## 📞 Support

This platform is designed to integrate with your existing:
1. **Semantic pattern matching algorithms**
2. **Impact assessment data science machine**
3. **Premium news API subscriptions**

All integration points are clearly marked with `PLACEHOLDER` comments and ready interfaces.

---

**Status**: Production-ready foundation with placeholders for your enhancements
**Next Steps**: Integrate your semantic algorithms and impact assessment system