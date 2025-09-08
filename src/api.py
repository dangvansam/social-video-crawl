#!/usr/bin/env python3
"""
FastAPI application with Hatchet for background task processing
Provides REST API endpoints for downloading videos, audio, and subtitles
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Dict, Any
from enum import Enum
import os
import asyncio
from datetime import datetime
from loguru import logger
import uuid

from hatchet_sdk import Hatchet, Context
from src.social_video_downloader import SocialVideoDownloader

# Configure logger
logger.add("api_hatchet.log", rotation="10 MB", retention="7 days", level="INFO")

# Initialize Hatchet
hatchet = Hatchet(debug=True)

# Initialize FastAPI app
app = FastAPI(
    title="Social Video Downloader API with Hatchet",
    description="API for downloading videos from various social media platforms using Hatchet for background processing",
    version="2.0.0"
)

# Global downloader instance
downloader = SocialVideoDownloader(download_dir="./download")

# Store task results
task_results: Dict[str, Dict[str, Any]] = {}


# ============== Hatchet Task Definitions ==============

class SingleDownloadInput(BaseModel):
    """Input model for single video download task"""
    url: str
    video: bool = True
    audio: bool = True
    subtitles: bool = True
    task_id: str


class BatchDownloadInput(BaseModel):
    """Input model for batch download task"""
    urls: List[str]
    video: bool = True
    audio: bool = True
    subtitles: bool = True
    task_id: str


class VideoInfoInput(BaseModel):
    """Input model for video info extraction task"""
    url: str
    task_id: str


@hatchet.workflow(name="SingleVideoDownload")
class SingleVideoDownloadWorkflow:
    """Workflow for downloading a single video"""
    
    @hatchet.step(name="download_video")
    def download_video(self, context: Context) -> dict:
        input_data = context.workflow_input()
        task_id = input_data["task_id"]
        
        # Update task status
        task_results[task_id] = {
            "status": "processing",
            "started_at": datetime.now().isoformat(),
            "url": input_data["url"]
        }
        
        logger.info(f"Processing download task {task_id} for URL: {input_data['url']}")
        
        try:
            # Perform the download
            result = downloader.download_single_video(
                url=input_data["url"],
                video=input_data["video"],
                audio=input_data["audio"],
                subtitles=input_data["subtitles"]
            )
            
            # Update task results
            task_results[task_id]["status"] = "completed" if result["success"] else "failed"
            task_results[task_id]["result"] = result
            task_results[task_id]["completed_at"] = datetime.now().isoformat()
            
            if result["success"]:
                logger.success(f"Download task {task_id} completed successfully")
            else:
                logger.error(f"Download task {task_id} failed: {result.get('error')}")
                task_results[task_id]["error"] = result.get("error")
            
            return {
                "task_id": task_id,
                "success": result["success"],
                "paths": result.get("paths", {}),
                "error": result.get("error")
            }
            
        except Exception as e:
            logger.error(f"Error processing download task {task_id}: {str(e)}")
            task_results[task_id]["status"] = "failed"
            task_results[task_id]["error"] = str(e)
            task_results[task_id]["completed_at"] = datetime.now().isoformat()
            
            return {
                "task_id": task_id,
                "success": False,
                "error": str(e)
            }


@hatchet.workflow(name="BatchVideoDownload")
class BatchVideoDownloadWorkflow:
    """Workflow for downloading multiple videos"""
    
    @hatchet.step(name="download_batch")
    def download_batch(self, context: Context) -> dict:
        input_data = context.workflow_input()
        task_id = input_data["task_id"]
        
        # Update task status
        task_results[task_id] = {
            "status": "processing",
            "started_at": datetime.now().isoformat(),
            "urls": input_data["urls"]
        }
        
        logger.info(f"Processing batch download task {task_id} for {len(input_data['urls'])} URLs")
        
        try:
            # Perform the batch download
            result = downloader.download_from_urls(
                urls=input_data["urls"],
                download_options={
                    "video": input_data["video"],
                    "audio": input_data["audio"],
                    "subtitles": input_data["subtitles"]
                }
            )
            
            # Update task results
            task_results[task_id]["status"] = "completed"
            task_results[task_id]["result"] = result
            task_results[task_id]["completed_at"] = datetime.now().isoformat()
            
            logger.success(
                f"Batch download task {task_id} completed: "
                f"{result['successful_downloads']}/{result['total_videos']} successful"
            )
            
            return {
                "task_id": task_id,
                "success": True,
                "total_videos": result["total_videos"],
                "successful_downloads": result["successful_downloads"],
                "failed_downloads": result["failed_downloads"]
            }
            
        except Exception as e:
            logger.error(f"Error processing batch download task {task_id}: {str(e)}")
            task_results[task_id]["status"] = "failed"
            task_results[task_id]["error"] = str(e)
            task_results[task_id]["completed_at"] = datetime.now().isoformat()
            
            return {
                "task_id": task_id,
                "success": False,
                "error": str(e)
            }


@hatchet.workflow(name="VideoInfoExtraction")
class VideoInfoExtractionWorkflow:
    """Workflow for extracting video information"""
    
    @hatchet.step(name="extract_info")
    def extract_info(self, context: Context) -> dict:
        input_data = context.workflow_input()
        task_id = input_data["task_id"]
        
        logger.info(f"Extracting info for URL: {input_data['url']}")
        
        try:
            # Extract video info
            info = downloader.get_video_info(input_data["url"])
            
            if info:
                task_results[task_id] = {
                    "status": "completed",
                    "info": info,
                    "completed_at": datetime.now().isoformat()
                }
                
                return {
                    "task_id": task_id,
                    "success": True,
                    "info": info
                }
            else:
                task_results[task_id] = {
                    "status": "failed",
                    "error": "Could not extract video information",
                    "completed_at": datetime.now().isoformat()
                }
                
                return {
                    "task_id": task_id,
                    "success": False,
                    "error": "Could not extract video information"
                }
                
        except Exception as e:
            logger.error(f"Error extracting video info: {str(e)}")
            task_results[task_id] = {
                "status": "failed",
                "error": str(e),
                "completed_at": datetime.now().isoformat()
            }
            
            return {
                "task_id": task_id,
                "success": False,
                "error": str(e)
            }


# ============== API Request/Response Models ==============

class SingleDownloadRequest(BaseModel):
    """Request model for single video download"""
    url: HttpUrl
    video: bool = True
    audio: bool = True
    subtitles: bool = True
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
                "video": True,
                "audio": True,
                "subtitles": False
            }
        }


class BatchDownloadRequest(BaseModel):
    """Request model for batch download"""
    urls: List[HttpUrl]
    video: bool = True
    audio: bool = True
    subtitles: bool = True
    
    class Config:
        json_schema_extra = {
            "example": {
                "urls": [
                    "https://www.youtube.com/watch?v=jNQXAC9IVRw",
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
                ],
                "video": True,
                "audio": False,
                "subtitles": True
            }
        }


class TaskResponse(BaseModel):
    """Response model for task operations"""
    task_id: str
    status: str
    message: str
    hatchet_run_id: Optional[str] = None


# ============== API Endpoints ==============

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Social Video Downloader API with Hatchet",
        "version": "2.0.0",
        "endpoints": {
            "GET /": "API information",
            "GET /health": "Health check",
            "POST /download": "Download single video",
            "POST /download/batch": "Download multiple videos",
            "GET /task/{task_id}": "Check task status",
            "POST /video-info": "Get video information",
            "GET /files/{date}/{folder}/{filename}": "Download file",
            "DELETE /task/{task_id}": "Delete task result"
        },
        "powered_by": "Hatchet Distributed Task Queue"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "download_dir": downloader.download_dir,
        "hatchet": "connected"
    }


@app.post("/download", response_model=TaskResponse)
async def download_single(request: SingleDownloadRequest):
    """
    Download a single video with specified options
    
    - **url**: Video URL to download
    - **video**: Download video file (default: true)
    - **audio**: Download audio file (default: true)
    - **subtitles**: Download subtitles (default: true)
    """
    task_id = str(uuid.uuid4())
    
    # Initialize task status
    task_results[task_id] = {
        "status": "pending",
        "url": str(request.url),
        "created_at": datetime.now().isoformat()
    }
    
    try:
        # Spawn the workflow
        spawned = hatchet.client.admin.run_workflow(
            "SingleVideoDownload",
            {
                "url": str(request.url),
                "video": request.video,
                "audio": request.audio,
                "subtitles": request.subtitles,
                "task_id": task_id
            }
        )
        
        logger.info(f"Spawned workflow for task {task_id}, run_id: {spawned.workflow_run_id}")
        
        return TaskResponse(
            task_id=task_id,
            status="pending",
            message=f"Download task created for {request.url}",
            hatchet_run_id=spawned.workflow_run_id
        )
        
    except Exception as e:
        logger.error(f"Failed to spawn workflow: {str(e)}")
        task_results[task_id]["status"] = "failed"
        task_results[task_id]["error"] = str(e)
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")


@app.post("/download/batch", response_model=TaskResponse)
async def download_batch(request: BatchDownloadRequest):
    """
    Download multiple videos with specified options
    
    - **urls**: List of video URLs to download
    - **video**: Download video files (default: true)
    - **audio**: Download audio files (default: true)
    - **subtitles**: Download subtitles (default: true)
    """
    task_id = str(uuid.uuid4())
    
    # Initialize task status
    task_results[task_id] = {
        "status": "pending",
        "urls": [str(url) for url in request.urls],
        "created_at": datetime.now().isoformat()
    }
    
    try:
        # Spawn the workflow
        spawned = hatchet.client.admin.run_workflow(
            "BatchVideoDownload",
            {
                "urls": [str(url) for url in request.urls],
                "video": request.video,
                "audio": request.audio,
                "subtitles": request.subtitles,
                "task_id": task_id
            }
        )
        
        logger.info(f"Spawned batch workflow for task {task_id}, run_id: {spawned.workflow_run_id}")
        
        return TaskResponse(
            task_id=task_id,
            status="pending",
            message=f"Batch download task created for {len(request.urls)} URLs",
            hatchet_run_id=spawned.workflow_run_id
        )
        
    except Exception as e:
        logger.error(f"Failed to spawn batch workflow: {str(e)}")
        task_results[task_id]["status"] = "failed"
        task_results[task_id]["error"] = str(e)
        raise HTTPException(status_code=500, detail=f"Failed to create batch task: {str(e)}")


@app.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """
    Get the status of a task
    
    - **task_id**: The task ID returned from download endpoints
    """
    if task_id not in task_results:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task_results[task_id]


@app.post("/video-info")
async def get_video_info(url: HttpUrl = Query(..., description="Video URL to get information from")):
    """
    Get video information without downloading
    
    - **url**: Video URL to analyze
    """
    task_id = str(uuid.uuid4())
    
    try:
        # Spawn the workflow
        spawned = hatchet.client.admin.run_workflow(
            "VideoInfoExtraction",
            {
                "url": str(url),
                "task_id": task_id
            }
        )
        
        logger.info(f"Spawned video info workflow for task {task_id}, run_id: {spawned.workflow_run_id}")
        
        # Wait a bit for quick responses
        await asyncio.sleep(2)
        
        # Check if completed
        if task_id in task_results and task_results[task_id].get("status") == "completed":
            return {
                "success": True,
                "info": task_results[task_id].get("info"),
                "task_id": task_id
            }
        else:
            return {
                "success": False,
                "message": "Processing, check task status",
                "task_id": task_id,
                "hatchet_run_id": spawned.workflow_run_id
            }
            
    except Exception as e:
        logger.error(f"Failed to spawn video info workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get video info: {str(e)}")


@app.get("/files/{date}/{folder}/{filename}")
async def download_file(date: str, folder: str, filename: str):
    """
    Download a file from the download directory
    
    - **date**: Date folder (YYYY-MM-DD format)
    - **folder**: Video folder name
    - **filename**: File name to download
    """
    file_path = os.path.join("./download", date, folder, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Security check: ensure the path is within download directory
    abs_file_path = os.path.abspath(file_path)
    abs_download_dir = os.path.abspath("./download")
    
    if not abs_file_path.startswith(abs_download_dir):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream"
    )


@app.delete("/task/{task_id}")
async def delete_task(task_id: str):
    """
    Delete a task result from memory
    
    - **task_id**: The task ID to delete
    """
    if task_id not in task_results:
        raise HTTPException(status_code=404, detail="Task not found")
    
    del task_results[task_id]
    
    return {
        "success": True,
        "message": f"Task {task_id} deleted"
    }


@app.get("/tasks")
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(10, ge=1, le=100)
):
    """List all tasks with optional filtering"""
    tasks = list(task_results.items())
    
    # Filter by status if provided
    if status:
        tasks = [(tid, task) for tid, task in tasks if task.get("status") == status]
    
    # Sort by created_at or started_at
    tasks.sort(
        key=lambda x: x[1].get("created_at", x[1].get("started_at", "")),
        reverse=True
    )
    
    # Apply limit
    tasks = tasks[:limit]
    
    return {
        "total": len(task_results),
        "filtered": len(tasks),
        "tasks": [
            {
                "task_id": tid,
                "status": task.get("status"),
                "created_at": task.get("created_at"),
                "completed_at": task.get("completed_at"),
                "url": task.get("url") or task.get("urls")
            }
            for tid, task in tasks
        ]
    }


# ============== Hatchet Worker ==============

def start_worker():
    """Start the Hatchet worker"""
    worker = hatchet.worker(
        "video-downloader-worker",
        max_runs=10
    )
    
    logger.info("Starting Hatchet worker...")
    worker.start()


if __name__ == "__main__":
    import uvicorn
    import threading
    
    # Start the Hatchet worker in a separate thread
    worker_thread = threading.Thread(target=start_worker, daemon=True)
    worker_thread.start()
    
    logger.info("Starting Social Video Downloader API with Hatchet...")
    
    # Start the FastAPI server
    port = int(os.getenv("API_PORT", 8001))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )