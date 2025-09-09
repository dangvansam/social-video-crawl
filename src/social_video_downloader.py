import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Union
from urllib.parse import urlparse

import yt_dlp
from loguru import logger


class SocialVideoDownloader:
    def __init__(self, download_dir="./download"):
        self.download_dir = download_dir
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        self.download_dir = os.path.join(download_dir, self.current_date)
        self.setup_directories()

    def setup_directories(self):
        os.makedirs(self.download_dir, exist_ok=True)

    def identify_platform(self, url):
        """Identify the platform from URL"""
        domain = urlparse(url).netloc.lower()
        if "tiktok.com" in domain:
            return "tiktok"
        elif "instagram.com" in domain:
            return "instagram"
        elif "facebook.com" in domain or "fb.com" in domain:
            return "facebook"
        elif "youtube.com" in domain or "youtu.be" in domain:
            return "youtube"
        elif "twitter.com" in domain or "x.com" in domain:
            return "twitter"
        else:
            return "unknown"

    def is_playlist_or_channel(self, url):
        """Check if URL is a playlist or channel"""
        if "youtube.com" in url:
            if "/playlist?" in url or "/channel/" in url or "/@" in url or "/c/" in url:
                return True
        elif "tiktok.com/@" in url and "/video/" not in url:
            return True
        return False

    def download_single_video(
        self, url: str, video: bool = True, audio: bool = True, subtitles: bool = True
    ) -> Dict:
        """Download a single video and return paths

        Args:
            url: Video URL
            video: Download video (default True)
            audio: Download audio (default True)
            subtitles: Download subtitles (default True)

        Returns:
            Dict with download results and paths
        """

        platform = self.identify_platform(url)
        timestamp = str(int(time.time()))

        result = {
            "url": url,
            "platform": platform,
            "timestamp": timestamp,
            "success": False,
            "paths": {"video": None, "audio": None, "subtitles": {}},
            "error": None,
        }

        try:
            # Get video info first
            with yt_dlp.YoutubeDL({"quiet": False}) as ydl:
                info = ydl.extract_info(url, download=False)
                video_title = info.get("title", "unknown")
                safe_title = "".join(
                    c for c in video_title if c.isalnum() or c in (" ", "-", "_")
                ).rstrip()
                safe_title = safe_title[:100]  # Limit folder name length

                video_folder = os.path.join(self.download_dir, safe_title)
                os.makedirs(video_folder, exist_ok=True)

            # Download video
            if video:
                video_path = os.path.join(video_folder, "video.%(ext)s")
                ydl_opts = {
                    "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                    "outtmpl": video_path,
                    "quiet": True,
                    "no_warnings": True,
                    "allsubtitles": subtitles,
                    "writesubtitles": subtitles,
                    "writeautomaticsub": subtitles,
                    "subtitlesformat": "vtt",
                    "subtitleslangs": ["all"],
                    "postprocessors": [
                        {"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}
                    ],
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                    actual_video_path = video_path.replace("%(ext)s", "mp4")
                    if os.path.exists(actual_video_path):
                        result["paths"]["video"] = actual_video_path
                        logger.success(f"Video downloaded: {actual_video_path}")

                    # Check for subtitle files downloaded with video
                    if subtitles:
                        for lang_code in ["vie-VN", "eng-US"]:
                            subtitle_file = os.path.join(
                                video_folder, f"video.{lang_code}.vtt"
                            )
                            if os.path.exists(subtitle_file):
                                new_subtitle_file = os.path.join(
                                    video_folder, f"sub-{lang_code}.vtt"
                                )
                                os.rename(subtitle_file, new_subtitle_file)
                                result["paths"]["subtitles"][lang_code] = (
                                    new_subtitle_file
                                )
                                logger.success(
                                    f"Subtitle downloaded: {new_subtitle_file}"
                                )

            # Download audio
            if audio:
                audio_path = os.path.join(video_folder, "audio.%(ext)s")
                ydl_opts = {
                    "format": "bestaudio/best",
                    "outtmpl": audio_path,
                    "quiet": True,
                    "no_warnings": True,
                    "postprocessors": [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "wav",
                            "preferredquality": "192",
                        }
                    ],
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                    actual_audio_path = os.path.join(video_folder, "audio.wav")
                    if os.path.exists(actual_audio_path):
                        result["paths"]["audio"] = actual_audio_path
                        logger.success(f"Audio downloaded: {actual_audio_path}")

            # Download subtitles separately if not already downloaded with video
            if subtitles and not result["paths"]["subtitles"]:
                subtitle_path = os.path.join(video_folder, "sub.%(ext)s")
                ydl_opts = {
                    "skip_download": True,
                    "allsubtitles": True,
                    "writesubtitles": True,
                    "writeautomaticsub": True,
                    "subtitlesformat": "vtt",
                    "subtitleslangs": ["all"],
                    "outtmpl": subtitle_path,
                    "quiet": True,
                    "no_warnings": True,
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                    for lang_code in ["vie-VN", "eng-US"]:
                        subtitle_file = os.path.join(
                            video_folder, f"sub.{lang_code}.vtt"
                        )
                        if os.path.exists(subtitle_file):
                            new_subtitle_file = os.path.join(
                                video_folder, f"sub-{lang_code}.vtt"
                            )
                            os.rename(subtitle_file, new_subtitle_file)
                            result["paths"]["subtitles"][lang_code] = new_subtitle_file
                            logger.success(f"Subtitle downloaded: {new_subtitle_file}")

                if (
                    not video
                    and "actual_video_path" in locals()
                    and os.path.exists(actual_video_path)
                ):
                    os.remove(actual_video_path)

                if (
                    not audio
                    and "actual_audio_path" in locals()
                    and os.path.exists(actual_audio_path)
                ):
                    os.remove(actual_audio_path)

            result["success"] = True

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Error downloading {url}: {e}")

        return result

    def download_playlist_or_channel(
        self, url: str, download_options: Optional[Dict] = None
    ) -> Dict:
        """Download all videos from a playlist or channel

        Args:
            url: Playlist or channel URL
            download_options: Dict with keys 'video', 'audio', 'subtitles'

        Returns:
            Dict with download results for all videos
        """
        if download_options is None:
            download_options = {"video": True, "audio": True, "subtitles": True}

        result = {
            "url": url,
            "type": "playlist" if "playlist" in url else "channel",
            "total_videos": 0,
            "successful_downloads": 0,
            "failed_downloads": 0,
            "videos": [],
        }

        try:
            # Extract all video URLs from playlist/channel
            ydl_opts = {
                "quiet": True,
                "extract_flat": True,
                "force_generic_extractor": False,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                playlist_info = ydl.extract_info(url, download=False)

                if "entries" in playlist_info:
                    entries = list(playlist_info["entries"])
                    result["total_videos"] = len(entries)
                    logger.info(f"Found {len(entries)} videos in {result['type']}")

                    for i, entry in enumerate(entries, 1):
                        if entry:
                            video_url = (
                                entry.get("url")
                                or f"https://www.youtube.com/watch?v={entry.get('id')}"
                            )
                            logger.info(
                                f"[{i}/{len(entries)}] Processing: {entry.get('title', 'Unknown')}"
                            )

                            video_result = self.download_single_video(
                                video_url,
                                video=download_options.get("video", True),
                                audio=download_options.get("audio", True),
                                subtitles=download_options.get("subtitles", True),
                            )
                            result["videos"].append(video_result)

                            if video_result["success"]:
                                result["successful_downloads"] += 1
                            else:
                                result["failed_downloads"] += 1
                else:
                    # Single video, not a playlist
                    video_result = self.download_single_video(
                        url,
                        video=download_options.get("video", True),
                        audio=download_options.get("audio", True),
                        subtitles=download_options.get("subtitles", True),
                    )
                    result["videos"].append(video_result)
                    result["total_videos"] = 1
                    if video_result["success"]:
                        result["successful_downloads"] = 1
                    else:
                        result["failed_downloads"] = 1

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Error processing playlist/channel: {e}")

        return result

    def download_from_urls(
        self, urls: Union[str, List[str]], download_options: Optional[Dict] = None
    ) -> Dict:
        """Download from single URL, list of URLs, playlist, or channel

        Args:
            urls: Single URL string or list of URLs
            download_options: Dict with keys 'video', 'audio', 'subtitles'

        Returns:
            Dict with all download results and paths
        """
        if isinstance(urls, str):
            urls = [urls]

        results = {
            "date": self.current_date,
            "download_directory": self.download_dir,
            "total_urls": len(urls),
            "total_videos": 0,
            "successful_downloads": 0,
            "failed_downloads": 0,
            "downloads": [],
        }

        for url in urls:
            logger.info(f"{'=' * 60}")
            logger.info(f"Processing: {url}")
            logger.info("=" * 60)

            if self.is_playlist_or_channel(url):
                # Handle playlist or channel
                playlist_result = self.download_playlist_or_channel(
                    url, download_options
                )
                results["downloads"].append(playlist_result)
                results["total_videos"] += playlist_result["total_videos"]
                results["successful_downloads"] += playlist_result[
                    "successful_downloads"
                ]
                results["failed_downloads"] += playlist_result["failed_downloads"]
            else:
                # Handle single video
                video_result = self.download_single_video(
                    url,
                    video=download_options.get("video", True),
                    audio=download_options.get("audio", True),
                    subtitles=download_options.get("subtitles", True),
                )
                results["downloads"].append(video_result)
                results["total_videos"] += 1
                if video_result["success"]:
                    results["successful_downloads"] += 1
                else:
                    results["failed_downloads"] += 1

        # Summary
        logger.info(f"{'=' * 60}")
        logger.info("DOWNLOAD SUMMARY")
        logger.info(f"{'=' * 60}")
        logger.info(f"Date: {self.current_date}")
        logger.info(f"Output Directory: {self.download_dir}")
        logger.info(f"Total URLs processed: {results['total_urls']}")
        logger.info(f"Total videos found: {results['total_videos']}")
        logger.info(f"Successful downloads: {results['successful_downloads']}")
        logger.info(f"Failed downloads: {results['failed_downloads']}")
        logger.info(f"{'=' * 60}")

        return results

    def get_video_info(self, url: str) -> Optional[Dict]:
        """Get video information without downloading

        Args:
            url: Video URL

        Returns:
            Dict with video metadata
        """
        try:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                return {
                    "title": info.get("title", "N/A"),
                    "duration": info.get("duration", "N/A"),
                    "uploader": info.get("uploader", "N/A"),
                    "view_count": info.get("view_count", "N/A"),
                    "description": info.get("description", "N/A"),
                    "upload_date": info.get("upload_date", "N/A"),
                    "webpage_url": info.get("webpage_url", url),
                    "thumbnail": info.get("thumbnail", None),
                    "subtitles": list(info.get("subtitles", {}).keys()),
                    "automatic_captions": list(
                        info.get("automatic_captions", {}).keys()
                    ),
                }

        except Exception as e:
            logger.error(f"Error extracting video info: {e}")
            return None


if __name__ == "__main__":
    downloader = SocialVideoDownloader()
    results = downloader.download_from_urls(["https://vt.tiktok.com/ZSAo286Hf"])
    print(results)
