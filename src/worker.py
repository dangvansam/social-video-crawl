#!/usr/bin/env python3
"""
Hatchet Worker for processing video download tasks
"""

import os
import sys
import asyncio
from typing import Dict, Any
from loguru import logger
from dotenv import load_dotenv

from social_video_downloader import SocialVideoDownloader

# Load environment variables
load_dotenv()

# Configure logger
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level=os.getenv("LOG_LEVEL", "INFO")
)
logger.add(
    "logs/worker.log",
    rotation="500 MB",
    retention="10 days",
    level=os.getenv("LOG_LEVEL", "INFO")
)

try:
    from hatchet_sdk import Hatchet, Context
    HATCHET_AVAILABLE = True
except ImportError:
    logger.warning("Hatchet SDK not available. Running in fallback mode.")
    HATCHET_AVAILABLE = False


class VideoDownloadWorker:
    """Worker for processing video download tasks"""
    
    def __init__(self):
        self.download_dir = os.getenv("DOWNLOAD_DIR", "./download")
        self.worker_id = os.getenv("WORKER_ID", "1")
        self.downloader = SocialVideoDownloader(download_dir=self.download_dir)
        
        if HATCHET_AVAILABLE:
            self.hatchet = Hatchet(debug=True)
        else:
            self.hatchet = None
    
    def process_single_download(self, context: 'Context') -> Dict[str, Any]:
        """Process a single video download"""
        try:
            url = context.workflow_input()["url"]
            video = context.workflow_input().get("video", True)
            audio = context.workflow_input().get("audio", True)
            subtitles = context.workflow_input().get("subtitles", True)
            
            logger.info(f"Worker {self.worker_id}: Processing download for {url}")
            
            # Execute download
            result = self.downloader.download_single_video(
                url=url,
                video=video,
                audio=audio,
                subtitles=subtitles
            )
            
            logger.success(f"Worker {self.worker_id}: Successfully downloaded {url}")
            return {
                "status": "success",
                "result": result,
                "worker_id": self.worker_id
            }
            
        except Exception as e:
            logger.error(f"Worker {self.worker_id}: Error downloading {url}: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "worker_id": self.worker_id
            }
    
    def process_batch_download(self, context: 'Context') -> Dict[str, Any]:
        """Process a batch of video downloads"""
        try:
            urls = context.workflow_input()["urls"]
            video = context.workflow_input().get("video", True)
            audio = context.workflow_input().get("audio", True)
            subtitles = context.workflow_input().get("subtitles", True)
            
            logger.info(f"Worker {self.worker_id}: Processing batch of {len(urls)} videos")
            
            results = []
            for i, url in enumerate(urls, 1):
                logger.info(f"Worker {self.worker_id}: Processing {i}/{len(urls)}: {url}")
                try:
                    result = self.downloader.download_single_video(
                        url=url,
                        video=video,
                        audio=audio,
                        subtitles=subtitles
                    )
                    results.append({
                        "url": url,
                        "status": "success",
                        "result": result
                    })
                except Exception as e:
                    logger.error(f"Worker {self.worker_id}: Failed to download {url}: {str(e)}")
                    results.append({
                        "url": url,
                        "status": "error",
                        "error": str(e)
                    })
            
            successful = sum(1 for r in results if r["status"] == "success")
            logger.info(f"Worker {self.worker_id}: Batch complete. {successful}/{len(urls)} successful")
            
            return {
                "status": "completed",
                "total": len(urls),
                "successful": successful,
                "failed": len(urls) - successful,
                "results": results,
                "worker_id": self.worker_id
            }
            
        except Exception as e:
            logger.error(f"Worker {self.worker_id}: Batch processing error: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "worker_id": self.worker_id
            }
    
    def extract_video_info(self, context: 'Context') -> Dict[str, Any]:
        """Extract video information without downloading"""
        try:
            url = context.workflow_input()["url"]
            
            logger.info(f"Worker {self.worker_id}: Extracting info for {url}")
            
            info = self.downloader.extract_info(url)
            
            logger.success(f"Worker {self.worker_id}: Successfully extracted info for {url}")
            return {
                "status": "success",
                "info": info,
                "worker_id": self.worker_id
            }
            
        except Exception as e:
            logger.error(f"Worker {self.worker_id}: Error extracting info for {url}: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "worker_id": self.worker_id
            }
    
    def register_workflows(self):
        """Register Hatchet workflows"""
        if not HATCHET_AVAILABLE or not self.hatchet:
            logger.warning("Hatchet not available. Skipping workflow registration.")
            return
        
        # Register single download workflow
        @self.hatchet.workflow(name="SingleVideoDownload")
        class SingleVideoDownloadWorkflow:
            @self.hatchet.step(name="download_video")
            def download(self, context: Context) -> dict:
                return self.process_single_download(context)
        
        # Register batch download workflow
        @self.hatchet.workflow(name="BatchVideoDownload")
        class BatchVideoDownloadWorkflow:
            @self.hatchet.step(name="download_batch")
            def download_batch(self, context: Context) -> dict:
                return self.process_batch_download(context)
        
        # Register info extraction workflow
        @self.hatchet.workflow(name="VideoInfoExtraction")
        class VideoInfoExtractionWorkflow:
            @self.hatchet.step(name="extract_info")
            def extract(self, context: Context) -> dict:
                return self.extract_video_info(context)
        
        logger.info(f"Worker {self.worker_id}: Registered workflows")
    
    async def run(self):
        """Run the worker"""
        logger.info(f"Starting Video Download Worker {self.worker_id}")
        logger.info(f"Download directory: {self.download_dir}")
        logger.info(f"Hatchet available: {HATCHET_AVAILABLE}")
        
        if HATCHET_AVAILABLE and self.hatchet:
            # Register workflows
            self.register_workflows()
            
            # Create and start worker
            worker = self.hatchet.worker("video-download-worker")
            logger.info(f"Worker {self.worker_id}: Starting Hatchet worker...")
            
            try:
                await worker.async_start()
            except KeyboardInterrupt:
                logger.info(f"Worker {self.worker_id}: Shutting down...")
                await worker.async_stop()
        else:
            # Fallback mode - just keep the process alive
            logger.warning("Running in fallback mode without Hatchet")
            logger.info("Worker ready. Waiting for Redis/Celery tasks...")
            try:
                while True:
                    await asyncio.sleep(60)
                    logger.debug(f"Worker {self.worker_id}: Heartbeat")
            except KeyboardInterrupt:
                logger.info(f"Worker {self.worker_id}: Shutting down...")


def main():
    """Main entry point"""
    worker = VideoDownloadWorker()
    
    try:
        asyncio.run(worker.run())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()