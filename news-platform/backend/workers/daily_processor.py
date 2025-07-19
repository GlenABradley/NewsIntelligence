"""
News Intelligence Platform - Daily Processing Worker
Automated daily news processing at Noon Eastern (12:00 PM EST)
"""
import asyncio
from typing import List, Optional
from datetime import datetime, time
import pytz
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from core.config import settings
from models.news_models import ProcessingJob, StoryCluster, NewsAnalysis, DailyReport
from services.feed_manager import NewsFeedManager, ExternalNewsAPIs
from services.story_clustering import StoryClusteringEngine
from services.impact_assessment import ImpactAssessmentEngine
from services.dual_pipeline import NewsIntelligencePipeline
from services.report_generator import JournalistReportGenerator
from core.database import get_database

logger = logging.getLogger(__name__)

class DailyNewsProcessor:
    """
    Automated daily news intelligence processing
    Runs at Noon Eastern time with manual trigger capability
    """
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.feed_manager = NewsFeedManager()
        self.clustering_engine = StoryClusteringEngine()
        self.impact_engine = ImpactAssessmentEngine()
        self.dual_pipeline = NewsIntelligencePipeline()
        self.report_generator = JournalistReportGenerator()
        self.external_apis = ExternalNewsAPIs()
        
        self.is_processing = False
        self.current_job: Optional[ProcessingJob] = None
        
    async def start_scheduler(self):
        """Start the automated scheduler"""
        
        # Schedule daily processing at Noon Eastern
        eastern = pytz.timezone(settings.TIMEZONE)
        trigger = CronTrigger(
            hour=12,  # Noon
            minute=0,
            timezone=eastern
        )
        
        self.scheduler.add_job(
            self.run_daily_processing,
            trigger=trigger,
            id='daily_news_processing',
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("Daily news processing scheduler started (Noon Eastern)")
    
    async def stop_scheduler(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Daily news processing scheduler stopped")
    
    async def run_manual_processing(self) -> str:
        """
        Manual processing trigger for testing and immediate processing
        Returns job ID for tracking
        """
        if self.is_processing:
            raise ValueError("Processing already in progress")
        
        logger.info("Starting manual news processing")
        
        # Create processing job
        job = ProcessingJob(
            job_type="manual_trigger",
            status="pending",
            parameters={"triggered_by": "manual", "triggered_at": datetime.utcnow()}
        )
        
        # Start processing in background
        asyncio.create_task(self._execute_processing_cycle(job))
        
        return str(job.id)
    
    async def run_daily_processing(self) -> str:
        """
        Scheduled daily processing
        Returns job ID for tracking
        """
        if self.is_processing:
            logger.warning("Skipping daily processing - already in progress")
            return ""
        
        logger.info("Starting scheduled daily news processing")
        
        # Create processing job
        job = ProcessingJob(
            job_type="daily_processing",
            status="pending",
            parameters={"scheduled_time": datetime.utcnow()}
        )
        
        # Start processing
        asyncio.create_task(self._execute_processing_cycle(job))
        
        return str(job.id)
    
    async def _execute_processing_cycle(self, job: ProcessingJob):
        """
        Execute complete processing cycle
        
        Processing Steps:
        1. Poll news feeds (30 min window)
        2. Assess impact and select top 25 stories
        3. Cluster similar stories
        4. Gather diverse sources per story
        5. Run dual pipeline analysis
        6. Generate professional reports
        7. Organize files for human review
        """
        self.is_processing = True
        self.current_job = job
        
        try:
            job.status = "running"
            job.current_step = "Starting processing cycle"
            await self._update_job_progress(job, 5)
            
            # Step 1: Poll news feeds
            logger.info("Step 1: Polling news feeds")
            job.current_step = "Polling news feeds"
            await self._update_job_progress(job, 10)
            
            articles = await self.feed_manager.poll_all_feeds()
            logger.info(f"Collected {len(articles)} articles from feeds")
            
            if not articles:
                raise Exception("No articles collected from feeds")
            
            # Step 2: Assess impact and filter
            logger.info("Step 2: Assessing article impact")
            job.current_step = "Assessing article impact"
            await self._update_job_progress(job, 20)
            
            # Score articles individually first
            for article in articles:
                article.impact_score = await self.impact_engine.assess_article_impact(article)
            
            # Step 3: Cluster similar stories
            logger.info("Step 3: Clustering similar stories")
            job.current_step = "Clustering stories by similarity"
            await self._update_job_progress(job, 30)
            
            clusters = await self.clustering_engine.cluster_articles(articles)
            logger.info(f"Created {len(clusters)} story clusters")
            
            # Step 4: Rank clusters and select top stories
            logger.info("Step 4: Ranking stories by impact")
            job.current_step = "Ranking stories by impact"
            await self._update_job_progress(job, 40)
            
            top_clusters = await self.impact_engine.rank_stories_by_impact(
                clusters, 
                top_n=settings.TOP_STORIES_COUNT
            )
            
            logger.info(f"Selected top {len(top_clusters)} stories for analysis")
            
            # Step 5: Run dual pipeline analysis on each story
            logger.info("Step 5: Running dual pipeline analysis")
            job.current_step = "Analyzing stories with dual pipeline"
            await self._update_job_progress(job, 50)
            
            analyses = []
            for i, cluster in enumerate(top_clusters):
                logger.info(f"Analyzing story {i+1}/{len(top_clusters)}: {cluster.main_event}")
                
                try:
                    analysis = await self.dual_pipeline.analyze_story_cluster(cluster)
                    analyses.append(analysis)
                    
                    # Update progress
                    progress = 50 + (i + 1) / len(top_clusters) * 30
                    await self._update_job_progress(job, int(progress))
                    
                except Exception as e:
                    logger.error(f"Error analyzing cluster {cluster.cluster_id}: {str(e)}")
                    continue
            
            logger.info(f"Completed analysis for {len(analyses)} stories")
            
            # Step 6: Generate professional reports
            logger.info("Step 6: Generating professional reports")
            job.current_step = "Generating professional reports"
            await self._update_job_progress(job, 85)
            
            report_files = []
            for i, (analysis, cluster) in enumerate(zip(analyses, top_clusters[:len(analyses)])):
                try:
                    files = await self.report_generator.generate_comprehensive_report(analysis, cluster)
                    report_files.append(files)
                    
                    logger.info(f"Generated report for: {cluster.main_event}")
                    
                except Exception as e:
                    logger.error(f"Error generating report for {cluster.cluster_id}: {str(e)}")
                    continue
            
            # Step 7: Generate daily summary
            logger.info("Step 7: Generating daily summary")
            job.current_step = "Generating daily summary"
            await self._update_job_progress(job, 95)
            
            summary_file = await self.report_generator.generate_daily_summary(analyses, top_clusters)
            
            # Complete job
            job.status = "completed"
            job.current_step = "Processing complete"
            job.completed_at = datetime.utcnow()
            job.results = {
                "articles_processed": len(articles),
                "clusters_created": len(clusters),
                "top_stories_analyzed": len(analyses),
                "reports_generated": len(report_files),
                "summary_file": summary_file,
                "processing_date": datetime.utcnow().date().isoformat()
            }
            await self._update_job_progress(job, 100)
            
            logger.info("Daily news processing completed successfully")
            
            # Create daily report record
            daily_report = DailyReport(
                report_date=datetime.utcnow().date(),
                top_stories=[cluster.cluster_id for cluster in top_clusters[:len(analyses)]],
                total_stories_processed=len(clusters),
                total_sources_analyzed=sum(analysis.total_sources for analysis in analyses),
                report_files={"summary": summary_file, "story_reports": [f["markdown"] for f in report_files]},
                average_source_diversity=sum(cluster.source_diversity_score for cluster in top_clusters) / len(top_clusters) if top_clusters else 0,
                average_factual_consensus=sum(analysis.factual_consensus_score for analysis in analyses) / len(analyses) if analyses else 0,
                processing_success_rate=len(analyses) / len(top_clusters) if top_clusters else 0
            )
            
            # Save to database (placeholder)
            # await self._save_daily_report(daily_report)
            
        except Exception as e:
            logger.error(f"Error in processing cycle: {str(e)}")
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            
        finally:
            self.is_processing = False
            self.current_job = None
    
    async def _update_job_progress(self, job: ProcessingJob, progress: int):
        """Update job progress"""
        job.progress = progress
        
        # Save to database (placeholder)
        # db = await get_database()
        # await db.processing_jobs.update_one(
        #     {"_id": job.id},
        #     {"$set": {"progress": progress, "current_step": job.current_step, "status": job.status}}
        # )
        
        logger.info(f"Processing progress: {progress}% - {job.current_step}")
    
    async def get_processing_status(self) -> dict:
        """Get current processing status"""
        return {
            "is_processing": self.is_processing,
            "current_job": self.current_job.dict() if self.current_job else None,
            "scheduler_running": self.scheduler.running if hasattr(self, 'scheduler') else False,
            "next_scheduled_run": self._get_next_scheduled_run()
        }
    
    def _get_next_scheduled_run(self) -> Optional[str]:
        """Get next scheduled run time"""
        try:
            if hasattr(self, 'scheduler') and self.scheduler.running:
                job = self.scheduler.get_job('daily_news_processing')
                if job:
                    return job.next_run_time.isoformat()
        except Exception:
            pass
        return None
    
    async def cancel_current_processing(self) -> bool:
        """Cancel current processing if running"""
        if self.is_processing and self.current_job:
            self.current_job.status = "cancelled"
            self.current_job.completed_at = datetime.utcnow()
            self.is_processing = False
            logger.info("Processing cancelled by user request")
            return True
        return False

# Global processor instance
daily_processor = DailyNewsProcessor()

async def start_daily_processor():
    """Start the daily processor"""
    await daily_processor.start_scheduler()

async def stop_daily_processor():
    """Stop the daily processor"""
    await daily_processor.stop_scheduler()

async def trigger_manual_processing() -> str:
    """Trigger manual processing"""
    return await daily_processor.run_manual_processing()

async def get_processing_status() -> dict:
    """Get processing status"""
    return await daily_processor.get_processing_status()