"""
News Intelligence Platform - Professional Report Generator
Generates broadcast-ready reports for news anchors and journalists
"""
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, date
import os
import json
import logging
from pathlib import Path

# PDF generation (placeholder for when you want to add it)
# from reportlab.lib.pagesizes import letter
# from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

from models.news_models import StoryCluster, NewsAnalysis, DailyReport
from core.config import settings

logger = logging.getLogger(__name__)

class JournalistReportGenerator:
    """
    Professional report generator for news anchors and journalists
    Creates multiple formats: Markdown (primary), PDF, JSON
    """
    
    def __init__(self):
        self.reports_base_path = Path(settings.REPORTS_BASE_PATH)
        self.reports_base_path.mkdir(parents=True, exist_ok=True)
        
    async def generate_comprehensive_report(self, analysis: NewsAnalysis, cluster: StoryCluster) -> Dict[str, str]:
        """
        Generate comprehensive broadcast-ready report
        
        Args:
            analysis: Complete news analysis results
            cluster: Story cluster information
            
        Returns:
            Dictionary with file paths for each format generated
        """
        logger.info(f"Generating comprehensive report for story: {cluster.cluster_id}")
        
        # Create date-based directory
        report_date = datetime.utcnow().date()
        date_dir = self.reports_base_path / str(report_date)
        date_dir.mkdir(exist_ok=True)
        
        # Create story-specific directory
        story_slug = self._create_story_slug(cluster.main_event)
        story_dir = date_dir / f"{cluster.cluster_id[:8]}-{story_slug}"
        story_dir.mkdir(exist_ok=True)
        
        file_paths = {}
        
        # Generate Markdown report (primary)
        markdown_content = await self._generate_markdown_report(analysis, cluster)
        markdown_path = story_dir / "comprehensive-report.md"
        with open(markdown_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        file_paths["markdown"] = str(markdown_path)
        
        # Generate anchor briefing (JSON)
        briefing_content = await self._generate_anchor_briefing(analysis, cluster)
        briefing_path = story_dir / "anchor-briefing.json"
        with open(briefing_path, 'w', encoding='utf-8') as f:
            json.dump(briefing_content, f, indent=2, default=str)
        file_paths["briefing"] = str(briefing_path)
        
        # Generate source analysis (JSON)
        source_analysis = await self._generate_source_analysis(analysis, cluster)
        source_path = story_dir / "source-analysis.json"
        with open(source_path, 'w', encoding='utf-8') as f:
            json.dump(source_analysis, f, indent=2, default=str)
        file_paths["source_analysis"] = str(source_path)
        
        # Generate factual/emotional breakdown (JSON)
        breakdown = await self._generate_factual_emotional_breakdown(analysis)
        breakdown_path = story_dir / "factual-emotional-breakdown.json"
        with open(breakdown_path, 'w', encoding='utf-8') as f:
            json.dump(breakdown, f, indent=2, default=str)
        file_paths["breakdown"] = str(breakdown_path)
        
        # TODO: Generate PDF when needed
        # if "pdf" in settings.EXPORT_FORMATS:
        #     pdf_path = await self._generate_pdf_report(analysis, cluster, story_dir)
        #     file_paths["pdf"] = pdf_path
        
        logger.info(f"Report generated successfully: {len(file_paths)} files created")
        return file_paths
    
    async def _generate_markdown_report(self, analysis: NewsAnalysis, cluster: StoryCluster) -> str:
        """Generate comprehensive Markdown report for human review"""
        
        report_parts = []
        
        # Header
        report_parts.append(f"# {cluster.main_event}")
        report_parts.append(f"**Report Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        report_parts.append(f"**Story ID:** {cluster.cluster_id}")
        report_parts.append(f"**Sources Analyzed:** {analysis.total_sources}")
        report_parts.append("")
        
        # Executive Summary
        report_parts.append("## Executive Summary")
        report_parts.append(cluster.event_summary)
        report_parts.append("")
        
        # Factual Foundation
        if analysis.factual_claims:
            report_parts.append("## Verified Facts")
            report_parts.append(f"*Factual Consensus Score: {analysis.factual_consensus_score:.1%}*")
            report_parts.append("")
            
            for i, claim in enumerate(analysis.factual_claims[:15], 1):
                sources_text = f"({len(claim.supporting_sources)} sources)"
                consensus_text = f"[{claim.consensus_level:.1%} consensus]"
                report_parts.append(f"{i}. {claim.claim_text} {sources_text} {consensus_text}")
            
            report_parts.append("")
        
        # Key Talking Points
        report_parts.append("## Key Talking Points for Anchors")
        talking_points = await self._generate_talking_points(analysis, cluster)
        for point in talking_points:
            report_parts.append(f"• {point}")
        report_parts.append("")
        
        # Perspective Analysis
        report_parts.append("## Perspective Analysis")
        report_parts.append(f"**Source Perspectives Covered:**")
        for perspective, count in analysis.perspective_breakdown.items():
            percentage = (count / analysis.total_sources) * 100
            report_parts.append(f"• {perspective.title()}: {count} articles ({percentage:.1f}%)")
        report_parts.append("")
        
        # Emotional Spectrum
        if analysis.emotional_claims:
            report_parts.append("## Emotional Spectrum Across Sources")
            
            # Dominant emotions
            dominant_emotions = analysis.emotional_overlay.get("dominant_emotions", [])
            if dominant_emotions:
                report_parts.append("**Dominant Emotional Responses:**")
                for emotion in dominant_emotions[:5]:
                    report_parts.append(f"• {emotion['emotion'].title()}: {emotion['prevalence']:.1f}% prevalence, {emotion['average_intensity']:.1f}/10 intensity")
                report_parts.append("")
            
            # Perspective-specific emotions
            perspective_emotions = analysis.emotional_overlay.get("perspective_emotions", {})
            if perspective_emotions:
                report_parts.append("**Emotional Responses by Perspective:**")
                for perspective, emotions in perspective_emotions.items():
                    report_parts.append(f"**{perspective.title()}:**")
                    for emotion in emotions[:3]:  # Top 3 per perspective
                        report_parts.append(f"  - {emotion['emotion'].title()} ({emotion['intensity']:.1f}/10): {emotion['example']}")
                    report_parts.append("")
        
        # Source Reliability
        report_parts.append("## Source Analysis")
        report_parts.append(analysis.source_reliability_notes)
        report_parts.append("")
        
        # Source List
        report_parts.append("## Sources")
        for i, article in enumerate(cluster.articles, 1):
            publish_time = article.published_at.strftime("%Y-%m-%d %H:%M")
            report_parts.append(f"{i}. **{article.source}** ({article.source_perspective}) - {publish_time}")
            report_parts.append(f"   *{article.title}*")
            report_parts.append(f"   {article.url}")
            report_parts.append("")
        
        # Footer
        report_parts.append("---")
        report_parts.append("*Report generated by News Intelligence Platform - Dual Pipeline Analysis*")
        report_parts.append(f"*Processing time: {analysis.processing_time_seconds:.2f} seconds*")
        
        return "\n".join(report_parts)
    
    async def _generate_anchor_briefing(self, analysis: NewsAnalysis, cluster: StoryCluster) -> Dict[str, Any]:
        """Generate short-form briefing for news anchors"""
        
        # Extract top 3 verified facts
        top_facts = []
        for claim in analysis.factual_claims[:3]:
            top_facts.append({
                "fact": claim.claim_text,
                "confidence": claim.consensus_level,
                "sources": len(claim.supporting_sources)
            })
        
        # Extract key emotional angles
        emotional_angles = []
        dominant_emotions = analysis.emotional_overlay.get("dominant_emotions", [])
        for emotion in dominant_emotions[:3]:
            emotional_angles.append({
                "emotion": emotion["emotion"],
                "prevalence": emotion["prevalence"],
                "intensity": emotion["average_intensity"]
            })
        
        briefing = {
            "story_id": cluster.cluster_id,
            "headline": cluster.main_event,
            "one_liner": cluster.event_summary[:200] + "..." if len(cluster.event_summary) > 200 else cluster.event_summary,
            
            "key_facts": top_facts,
            "talking_points": await self._generate_talking_points(analysis, cluster, max_points=5),
            "emotional_angles": emotional_angles,
            
            "source_confidence": {
                "factual_consensus": analysis.factual_consensus_score,
                "total_sources": analysis.total_sources,
                "perspective_diversity": len(analysis.perspective_breakdown)
            },
            
            "broadcast_notes": {
                "story_complexity": "high" if analysis.total_sources > 10 else "medium" if analysis.total_sources > 5 else "low",
                "controversy_level": self._assess_controversy_level(analysis),
                "follow_up_potential": "high" if len(analysis.factual_claims) > 10 else "medium"
            },
            
            "generated_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow().replace(hour=23, minute=59, second=59)).isoformat()
        }
        
        return briefing
    
    async def _generate_source_analysis(self, analysis: NewsAnalysis, cluster: StoryCluster) -> Dict[str, Any]:
        """Generate detailed source analysis"""
        
        source_metrics = {}
        for article in cluster.articles:
            source = article.source
            if source not in source_metrics:
                source_metrics[source] = {
                    "article_count": 0,
                    "perspective": article.source_perspective,
                    "total_word_count": 0,
                    "articles": []
                }
            
            source_metrics[source]["article_count"] += 1
            source_metrics[source]["total_word_count"] += article.word_count or 0
            source_metrics[source]["articles"].append({
                "title": article.title,
                "published_at": article.published_at.isoformat(),
                "url": article.url,
                "word_count": article.word_count
            })
        
        return {
            "cluster_id": cluster.cluster_id,
            "analysis_date": analysis.analysis_date.isoformat(),
            "source_metrics": source_metrics,
            "diversity_score": cluster.source_diversity_score,
            "perspective_coverage": analysis.perspective_breakdown,
            "reliability_assessment": analysis.source_reliability_notes
        }
    
    async def _generate_factual_emotional_breakdown(self, analysis: NewsAnalysis) -> Dict[str, Any]:
        """Generate detailed factual/emotional analysis breakdown"""
        
        return {
            "analysis_summary": {
                "total_factual_claims": len(analysis.factual_claims),
                "total_emotional_claims": len(analysis.emotional_claims),
                "factual_consensus_score": analysis.factual_consensus_score,
                "emotional_spectrum_coverage": analysis.emotional_spectrum_coverage
            },
            
            "factual_claims": [
                {
                    "text": claim.claim_text,
                    "confidence": claim.confidence_score,
                    "consensus_level": claim.consensus_level,
                    "supporting_sources": claim.supporting_sources,
                    "entities": claim.entity_mentions
                }
                for claim in analysis.factual_claims
            ],
            
            "emotional_claims": [
                {
                    "text": claim.claim_text,
                    "emotion_type": claim.emotion_type,
                    "intensity": claim.intensity,
                    "perspective": claim.perspective,
                    "source": claim.source
                }
                for claim in analysis.emotional_claims
            ],
            
            "emotional_overlay": analysis.emotional_overlay,
            "processing_metadata": analysis.processing_metadata
        }
    
    async def _generate_talking_points(self, analysis: NewsAnalysis, cluster: StoryCluster, max_points: int = 8) -> List[str]:
        """Generate key talking points for news anchors"""
        
        talking_points = []
        
        # Lead with strongest factual claims
        if analysis.factual_claims:
            top_fact = analysis.factual_claims[0]
            talking_points.append(f"According to {len(top_fact.supporting_sources)} sources, {top_fact.claim_text.lower()}")
        
        # Add perspective diversity note
        if len(analysis.perspective_breakdown) >= 3:
            talking_points.append(f"This story has been covered across {len(analysis.perspective_breakdown)} different perspective sources")
        
        # Add source reliability note
        if analysis.total_sources >= 5:
            talking_points.append(f"Based on analysis of {analysis.total_sources} sources with {analysis.factual_consensus_score:.0%} factual consensus")
        
        # Add emotional context if significant
        dominant_emotions = analysis.emotional_overlay.get("dominant_emotions", [])
        if dominant_emotions and dominant_emotions[0]["prevalence"] > 30:
            emotion = dominant_emotions[0]
            talking_points.append(f"Coverage shows significant {emotion['emotion']} response ({emotion['prevalence']:.0f}% of emotional content)")
        
        # Add development note
        if cluster.article_count > 10:
            talking_points.append("This is a developing story with significant ongoing coverage")
        
        # Add any high-confidence unique facts
        for claim in analysis.factual_claims[1:4]:  # Skip first one, already used
            if claim.consensus_level > 0.8:
                talking_points.append(f"Multiple sources confirm: {claim.claim_text.lower()}")
        
        return talking_points[:max_points]
    
    def _assess_controversy_level(self, analysis: NewsAnalysis) -> str:
        """Assess controversy level based on emotional spectrum"""
        if not analysis.emotional_claims:
            return "low"
        
        # Check for high-intensity negative emotions
        high_intensity_negative = 0
        total_emotional = len(analysis.emotional_claims)
        
        for claim in analysis.emotional_claims:
            if claim.emotion_type in ["anger", "fear", "disgust", "sadness"] and claim.intensity > 7:
                high_intensity_negative += 1
        
        controversy_ratio = high_intensity_negative / total_emotional if total_emotional > 0 else 0
        
        if controversy_ratio > 0.5:
            return "high"
        elif controversy_ratio > 0.2:
            return "medium"
        else:
            return "low"
    
    def _create_story_slug(self, event_title: str) -> str:
        """Create URL-friendly slug from story title"""
        import re
        
        # Convert to lowercase and replace spaces with hyphens
        slug = event_title.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)  # Remove special characters
        slug = re.sub(r'[-\s]+', '-', slug)   # Replace spaces and multiple hyphens
        
        # Limit length
        return slug[:50].strip('-')
    
    async def generate_daily_summary(self, analyses: List[NewsAnalysis], clusters: List[StoryCluster]) -> str:
        """Generate daily summary report"""
        
        report_date = datetime.utcnow().date()
        date_dir = self.reports_base_path / str(report_date)
        
        summary_parts = []
        
        # Header
        summary_parts.append(f"# Daily News Intelligence Summary")
        summary_parts.append(f"**Date:** {report_date.strftime('%B %d, %Y')}")
        summary_parts.append(f"**Generated:** {datetime.utcnow().strftime('%H:%M UTC')}")
        summary_parts.append("")
        
        # Overview
        total_sources = sum(analysis.total_sources for analysis in analyses)
        avg_consensus = sum(analysis.factual_consensus_score for analysis in analyses) / len(analyses) if analyses else 0
        
        summary_parts.append("## Overview")
        summary_parts.append(f"- **Total Stories Analyzed:** {len(clusters)}")
        summary_parts.append(f"- **Total Sources Processed:** {total_sources}")
        summary_parts.append(f"- **Average Factual Consensus:** {avg_consensus:.1%}")
        summary_parts.append("")
        
        # Top Stories
        summary_parts.append("## Top Stories by Impact")
        sorted_clusters = sorted(clusters, key=lambda c: c.impact_score, reverse=True)
        
        for i, cluster in enumerate(sorted_clusters[:10], 1):
            summary_parts.append(f"{i}. **{cluster.main_event}** (Impact: {cluster.impact_score:.1f}/10)")
            summary_parts.append(f"   - {cluster.article_count} sources, {cluster.source_diversity_score:.1%} diversity")
            summary_parts.append(f"   - Report: `{cluster.cluster_id[:8]}-{self._create_story_slug(cluster.main_event)}/`")
            summary_parts.append("")
        
        # Generate summary file
        summary_content = "\n".join(summary_parts)
        summary_path = date_dir / "daily-summary.md"
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(summary_content)
        
        return str(summary_path)
    
    async def export_to_pdf(self, markdown_content: str, output_path: str) -> str:
        """
        PLACEHOLDER: Export markdown to PDF
        Can be implemented with reportlab or weasyprint when needed
        """
        logger.info("PDF export not yet implemented - placeholder")
        
        # TODO: Implement PDF generation
        # This is where you'd convert markdown to PDF
        
        return output_path
    
    async def get_report_files(self, report_date: date = None) -> Dict[str, List[str]]:
        """Get list of all report files for a given date"""
        
        if report_date is None:
            report_date = datetime.utcnow().date()
        
        date_dir = self.reports_base_path / str(report_date)
        
        if not date_dir.exists():
            return {}
        
        report_files = {
            "story_reports": [],
            "summary_files": [],
            "data_files": []
        }
        
        for item in date_dir.iterdir():
            if item.is_dir():
                # Story directory
                story_files = []
                for file in item.iterdir():
                    if file.is_file():
                        story_files.append(str(file))
                report_files["story_reports"].append({
                    "story_dir": str(item),
                    "files": story_files
                })
            elif item.is_file():
                if "summary" in item.name:
                    report_files["summary_files"].append(str(item))
                else:
                    report_files["data_files"].append(str(item))
        
        return report_files