"""
News Intelligence Platform - Report API Endpoints
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import os
import json
import logging
from pathlib import Path

from ..services.report_generator import JournalistReportGenerator
from ..core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/reports", tags=["reports"])

@router.get("/", summary="Report Management API")
async def reports_api_status():
    """Get report API status"""
    return {
        "message": "News Intelligence Reports API v1.0",
        "status": "operational",
        "export_formats": settings.EXPORT_FORMATS,
        "reports_path": settings.REPORTS_BASE_PATH,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/daily/{report_date}", summary="Get Daily Report Files")
async def get_daily_reports(report_date: str = Query(..., description="Date in YYYY-MM-DD format")):
    """Get all report files for a specific date"""
    try:
        # Parse date
        try:
            parsed_date = datetime.strptime(report_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        report_generator = JournalistReportGenerator()
        report_files = await report_generator.get_report_files(parsed_date)
        
        if not any(report_files.values()):
            raise HTTPException(status_code=404, detail=f"No reports found for {report_date}")
        
        return {
            "status": "success",
            "report_date": report_date,
            "files": report_files,
            "total_stories": len(report_files.get("story_reports", [])),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting daily reports: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Report retrieval failed: {str(e)}")

@router.get("/download/{report_date}/{story_id}/{file_type}", summary="Download Report File")
async def download_report_file(
    report_date: str,
    story_id: str,
    file_type: str = Query(..., description="File type: markdown, briefing, source_analysis, breakdown")
):
    """Download a specific report file"""
    try:
        # Validate date format
        try:
            datetime.strptime(report_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Construct file path
        reports_path = Path(settings.REPORTS_BASE_PATH)
        date_dir = reports_path / report_date
        
        # Find story directory that starts with story_id
        story_dirs = [d for d in date_dir.iterdir() if d.is_dir() and d.name.startswith(story_id)]
        
        if not story_dirs:
            raise HTTPException(status_code=404, detail=f"Story {story_id} not found for {report_date}")
        
        story_dir = story_dirs[0]
        
        # Map file types to actual filenames
        file_mapping = {
            "markdown": "comprehensive-report.md",
            "briefing": "anchor-briefing.json",
            "source_analysis": "source-analysis.json",
            "breakdown": "factual-emotional-breakdown.json"
        }
        
        if file_type not in file_mapping:
            raise HTTPException(status_code=400, detail=f"Invalid file type. Choose from: {list(file_mapping.keys())}")
        
        file_path = story_dir / file_mapping[file_type]
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File {file_type} not found for story {story_id}")
        
        # Determine media type
        media_type = "application/json" if file_type != "markdown" else "text/markdown"
        
        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            filename=f"{story_id}-{file_mapping[file_type]}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading report file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@router.get("/summary/{report_date}", summary="Get Daily Summary")
async def get_daily_summary(report_date: str):
    """Get daily summary report"""
    try:
        # Validate date format
        try:
            datetime.strptime(report_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Construct file path
        reports_path = Path(settings.REPORTS_BASE_PATH)
        summary_path = reports_path / report_date / "daily-summary.md"
        
        if not summary_path.exists():
            raise HTTPException(status_code=404, detail=f"Daily summary not found for {report_date}")
        
        return FileResponse(
            path=str(summary_path),
            media_type="text/markdown",
            filename=f"daily-summary-{report_date}.md"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting daily summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Summary retrieval failed: {str(e)}")

@router.get("/list-dates", summary="List Available Report Dates")
async def list_report_dates(limit: int = Query(30, description="Maximum number of dates to return")):
    """List available report dates"""
    try:
        reports_path = Path(settings.REPORTS_BASE_PATH)
        
        if not reports_path.exists():
            return {
                "status": "success",
                "available_dates": [],
                "total_dates": 0
            }
        
        # Get all date directories
        date_dirs = []
        for item in reports_path.iterdir():
            if item.is_dir():
                try:
                    # Validate it's a date directory
                    datetime.strptime(item.name, "%Y-%m-%d")
                    date_dirs.append(item.name)
                except ValueError:
                    continue
        
        # Sort dates (newest first)
        date_dirs.sort(reverse=True)
        date_dirs = date_dirs[:limit]
        
        # Get details for each date
        date_details = []
        for date_str in date_dirs:
            date_path = reports_path / date_str
            
            # Count story reports
            story_count = len([d for d in date_path.iterdir() if d.is_dir()])
            
            # Check for summary
            has_summary = (date_path / "daily-summary.md").exists()
            
            date_details.append({
                "date": date_str,
                "story_count": story_count,
                "has_summary": has_summary,
                "path": str(date_path)
            })
        
        return {
            "status": "success",
            "available_dates": date_details,
            "total_dates": len(date_details),
            "limit_applied": limit,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error listing report dates: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Date listing failed: {str(e)}")

@router.get("/story-preview/{report_date}/{story_id}", summary="Preview Story Report")
async def preview_story_report(report_date: str, story_id: str):
    """Get a preview of a story report (first 1000 characters)"""
    try:
        # Validate date format
        try:
            datetime.strptime(report_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Construct file path
        reports_path = Path(settings.REPORTS_BASE_PATH)
        date_dir = reports_path / report_date
        
        # Find story directory
        story_dirs = [d for d in date_dir.iterdir() if d.is_dir() and d.name.startswith(story_id)]
        
        if not story_dirs:
            raise HTTPException(status_code=404, detail=f"Story {story_id} not found for {report_date}")
        
        story_dir = story_dirs[0]
        markdown_path = story_dir / "comprehensive-report.md"
        briefing_path = story_dir / "anchor-briefing.json"
        
        preview_data = {
            "story_id": story_id,
            "report_date": report_date,
            "story_directory": story_dir.name,
            "available_files": [],
            "markdown_preview": None,
            "briefing_data": None
        }
        
        # List available files
        for file_path in story_dir.iterdir():
            if file_path.is_file():
                preview_data["available_files"].append(file_path.name)
        
        # Get markdown preview
        if markdown_path.exists():
            with open(markdown_path, 'r', encoding='utf-8') as f:
                content = f.read()
                preview_data["markdown_preview"] = content[:1000] + "..." if len(content) > 1000 else content
        
        # Get briefing data
        if briefing_path.exists():
            with open(briefing_path, 'r', encoding='utf-8') as f:
                preview_data["briefing_data"] = json.load(f)
        
        return preview_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing story report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")

@router.get("/search", summary="Search Reports")
async def search_reports(
    query: str = Query(..., description="Search term"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(20, description="Maximum results to return")
):
    """Search through report content"""
    try:
        reports_path = Path(settings.REPORTS_BASE_PATH)
        
        if not reports_path.exists():
            return {
                "status": "success",
                "query": query,
                "results": [],
                "total_found": 0
            }
        
        # Get date range
        date_dirs = []
        for item in reports_path.iterdir():
            if item.is_dir():
                try:
                    item_date = datetime.strptime(item.name, "%Y-%m-%d").date()
                    
                    # Apply date filters
                    if start_date:
                        start = datetime.strptime(start_date, "%Y-%m-%d").date()
                        if item_date < start:
                            continue
                    
                    if end_date:
                        end = datetime.strptime(end_date, "%Y-%m-%d").date()
                        if item_date > end:
                            continue
                    
                    date_dirs.append(item)
                except ValueError:
                    continue
        
        # Search through files
        results = []
        query_lower = query.lower()
        
        for date_dir in date_dirs:
            # Search daily summary
            summary_path = date_dir / "daily-summary.md"
            if summary_path.exists():
                try:
                    with open(summary_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if query_lower in content.lower():
                            # Find context around match
                            index = content.lower().find(query_lower)
                            start = max(0, index - 100)
                            end = min(len(content), index + 200)
                            context = content[start:end].strip()
                            
                            results.append({
                                "type": "daily_summary",
                                "date": date_dir.name,
                                "file": "daily-summary.md",
                                "context": context,
                                "score": content.lower().count(query_lower)
                            })
                except Exception:
                    continue
            
            # Search story reports
            for story_dir in date_dir.iterdir():
                if story_dir.is_dir():
                    markdown_path = story_dir / "comprehensive-report.md"
                    if markdown_path.exists():
                        try:
                            with open(markdown_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                if query_lower in content.lower():
                                    # Find context around match
                                    index = content.lower().find(query_lower)
                                    start = max(0, index - 100)
                                    end = min(len(content), index + 200)
                                    context = content[start:end].strip()
                                    
                                    # Extract story title from content
                                    lines = content.split('\n')
                                    title = lines[0].replace('#', '').strip() if lines else story_dir.name
                                    
                                    results.append({
                                        "type": "story_report",
                                        "date": date_dir.name,
                                        "story_id": story_dir.name.split('-')[0],
                                        "story_title": title,
                                        "file": "comprehensive-report.md",
                                        "context": context,
                                        "score": content.lower().count(query_lower)
                                    })
                        except Exception:
                            continue
        
        # Sort by relevance (score) and limit
        results.sort(key=lambda x: x["score"], reverse=True)
        results = results[:limit]
        
        return {
            "status": "success",
            "query": query,
            "results": results,
            "total_found": len(results),
            "date_range": {
                "start": start_date,
                "end": end_date
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error searching reports: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/stats", summary="Get Report Statistics")
async def get_report_stats():
    """Get statistics about generated reports"""
    try:
        reports_path = Path(settings.REPORTS_BASE_PATH)
        
        if not reports_path.exists():
            return {
                "status": "success",
                "stats": {
                    "total_days": 0,
                    "total_stories": 0,
                    "total_files": 0,
                    "date_range": None
                }
            }
        
        # Collect statistics
        total_days = 0
        total_stories = 0
        total_files = 0
        dates = []
        
        for date_dir in reports_path.iterdir():
            if date_dir.is_dir():
                try:
                    # Validate date
                    datetime.strptime(date_dir.name, "%Y-%m-%d")
                    dates.append(date_dir.name)
                    total_days += 1
                    
                    # Count stories and files
                    for story_dir in date_dir.iterdir():
                        if story_dir.is_dir():
                            total_stories += 1
                            total_files += len([f for f in story_dir.iterdir() if f.is_file()])
                        elif story_dir.is_file():
                            total_files += 1
                            
                except ValueError:
                    continue
        
        # Date range
        date_range = None
        if dates:
            dates.sort()
            date_range = {
                "earliest": dates[0],
                "latest": dates[-1]
            }
        
        return {
            "status": "success",
            "stats": {
                "total_days": total_days,
                "total_stories": total_stories,
                "total_files": total_files,
                "average_stories_per_day": total_stories / total_days if total_days > 0 else 0,
                "date_range": date_range
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting report stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Stats retrieval failed: {str(e)}")