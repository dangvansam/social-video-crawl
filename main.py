import sys
import argparse
from social_video_downloader import SocialVideoDownloader


def main():
    parser = argparse.ArgumentParser(description='Download videos and subtitles from social media platforms')
    parser.add_argument('url', nargs='?', help='Social media video URL')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    parser.add_argument('--download-dir', default='./downloads', help='Directory to save downloads')
    parser.add_argument('--batch', type=str, help='File containing URLs (one per line)')
    
    args = parser.parse_args()
    
    if not args.url and not args.batch:
        print("Error: Please provide a URL or a batch file")
        parser.print_help()
        sys.exit(1)
    
    downloader = SocialVideoDownloader(headless=args.headless, download_dir=args.download_dir)
    
    try:
        if args.batch:
            with open(args.batch, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
            
            print(f"Processing {len(urls)} URLs from batch file...")
            for i, url in enumerate(urls, 1):
                print(f"\n[{i}/{len(urls)}] Processing: {url}")
                success = downloader.download_from_url(url)
                if success:
                    print(f"✓ Successfully processed: {url}")
                else:
                    print(f"✗ Failed to process: {url}")
        else:
            print(f"Processing: {args.url}")
            success = downloader.download_from_url(args.url)
            if success:
                print(f"✓ Successfully downloaded video and subtitles")
            else:
                print(f"✗ Failed to download content")
    
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        downloader.close()
        print("\nDownloader closed")


if __name__ == "__main__":
    main()
