import sys
import argparse
from social_video_downloader import SocialVideoDownloader
from loguru import logger

def main():
    parser = argparse.ArgumentParser(description='Download videos and subtitles from social media platforms')
    parser.add_argument('url', nargs='?', help='Social media video URL')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    parser.add_argument('--download-dir', default='./downloads', help='Directory to save downloads')
    parser.add_argument('--batch', type=str, help='File containing URLs (one per line)')
    
    args = parser.parse_args()
    
    if not args.url and not args.batch:
        logger.error("Error: Please provide a URL or a batch file")
        parser.print_help()
        sys.exit(1)
    
    downloader = SocialVideoDownloader(headless=args.headless, download_dir=args.download_dir)
    
    try:
        if args.batch:
            with open(args.batch, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
            
            logger.info(f"Processing {len(urls)} URLs from batch file...")
            for i, url in enumerate(urls, 1):
                logger.info(f"\n[{i}/{len(urls)}] Processing: {url}")
                success = downloader.download_from_url(url)
                if success:
                    logger.success(f"✓ Successfully processed: {url}")
                else:
                    logger.error(f"✗ Failed to process: {url}")
        else:
            logger.info(f"Processing: {args.url}")
            success = downloader.download_from_url(args.url)
            if success:
                logger.success(f"✓ Successfully downloaded video and subtitles")
            else:
                logger.error(f"✗ Failed to download content")
    
    except KeyboardInterrupt:
        logger.info("\n\nProcess interrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        downloader.close()
        logger.error("\nDownloader closed")


if __name__ == "__main__":
    main()
