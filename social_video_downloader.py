import os
import time
import json
import requests
from urllib.parse import urlparse, parse_qs
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class SocialVideoDownloader:
    def __init__(self, headless=True, download_dir="./downloads"):
        self.download_dir = download_dir
        self.temp_dir = None
        self.setup_directories()
        self.driver = self.setup_driver(headless)
        
    def setup_directories(self):
        os.makedirs(self.download_dir, exist_ok=True)
        os.makedirs(f"{self.download_dir}/videos", exist_ok=True)
        os.makedirs(f"{self.download_dir}/subtitles", exist_ok=True)
        
    def setup_driver(self, headless):
        chrome_options = Options()
        
        # Create a unique temp directory for this session
        import tempfile
        temp_dir = tempfile.mkdtemp(prefix="selenium_")
        chrome_options.add_argument(f"--user-data-dir={temp_dir}")
        
        # Use system Chrome/Chromium (remove binary_location to use default)
        # chrome_options.binary_location = "/snap/bin/chromium"
        
        if headless:
            chrome_options.add_argument("--headless=new")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36")
        
        prefs = {
            "download.default_directory": os.path.abspath(self.download_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Store temp_dir for cleanup
        self.temp_dir = temp_dir
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    
    def identify_platform(self, url):
        domain = urlparse(url).netloc.lower()
        if 'tiktok.com' in domain:
            return 'tiktok'
        elif 'instagram.com' in domain:
            return 'instagram'
        elif 'facebook.com' in domain or 'fb.com' in domain:
            return 'facebook'
        elif 'youtube.com' in domain or 'youtu.be' in domain:
            return 'youtube'
        elif 'twitter.com' in domain or 'x.com' in domain:
            return 'twitter'
        else:
            return 'unknown'
    
    def extract_video_info_tiktok(self, url):
        try:
            self.driver.get(url)
            time.sleep(3)
            
            video_info = {}
            
            try:
                video_element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "video"))
                )
                video_info['video_url'] = video_element.get_attribute("src")
            except:
                scripts = self.driver.find_elements(By.TAG_NAME, "script")
                for script in scripts:
                    content = script.get_attribute("innerHTML")
                    if '"downloadAddr"' in content or '"playAddr"' in content:
                        try:
                            data = json.loads(content)
                            if 'downloadAddr' in str(data):
                                video_info['video_url'] = self.extract_url_from_json(data, 'downloadAddr')
                            elif 'playAddr' in str(data):
                                video_info['video_url'] = self.extract_url_from_json(data, 'playAddr')
                        except:
                            pass
            
            try:
                caption_element = self.driver.find_element(By.CSS_SELECTOR, "[data-e2e='browse-video-desc']")
                video_info['caption'] = caption_element.text
            except:
                try:
                    caption_element = self.driver.find_element(By.CSS_SELECTOR, ".tiktok-caption")
                    video_info['caption'] = caption_element.text
                except:
                    video_info['caption'] = None
            
            video_info['subtitles'] = self.extract_subtitles_from_page()
            
            return video_info
            
        except Exception as e:
            print(f"Error extracting TikTok video info: {e}")
            return None
    
    def extract_video_info_instagram(self, url):
        try:
            self.driver.get(url)
            time.sleep(3)
            
            video_info = {}
            
            try:
                video_element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "video"))
                )
                video_info['video_url'] = video_element.get_attribute("src")
            except:
                video_info['video_url'] = None
            
            try:
                caption_element = self.driver.find_element(By.CSS_SELECTOR, "meta[property='og:description']")
                video_info['caption'] = caption_element.get_attribute("content")
            except:
                video_info['caption'] = None
            
            video_info['subtitles'] = self.extract_subtitles_from_page()
            
            return video_info
            
        except Exception as e:
            print(f"Error extracting Instagram video info: {e}")
            return None
    
    def extract_video_info_youtube(self, url):
        try:
            self.driver.get(url)
            time.sleep(3)
            
            video_info = {}
            
            try:
                video_element = self.driver.find_element(By.TAG_NAME, "video")
                video_info['video_url'] = video_element.get_attribute("src")
            except:
                video_info['video_url'] = None
            
            try:
                title_element = self.driver.find_element(By.CSS_SELECTOR, "h1.title")
                video_info['title'] = title_element.text
            except:
                video_info['title'] = None
            
            try:
                self.driver.execute_script("""
                    var buttons = document.querySelectorAll('button');
                    for(var i = 0; i < buttons.length; i++) {
                        if(buttons[i].getAttribute('aria-label') && 
                           buttons[i].getAttribute('aria-label').toLowerCase().includes('subtitle')) {
                            buttons[i].click();
                            break;
                        }
                    }
                """)
                time.sleep(1)
                
                subtitle_tracks = self.driver.execute_script("""
                    var video = document.querySelector('video');
                    if(video && video.textTracks) {
                        var tracks = [];
                        for(var i = 0; i < video.textTracks.length; i++) {
                            var track = video.textTracks[i];
                            var cues = [];
                            for(var j = 0; j < track.cues.length; j++) {
                                cues.push({
                                    startTime: track.cues[j].startTime,
                                    endTime: track.cues[j].endTime,
                                    text: track.cues[j].text
                                });
                            }
                            tracks.push({
                                language: track.language,
                                label: track.label,
                                cues: cues
                            });
                        }
                        return tracks;
                    }
                    return null;
                """)
                video_info['subtitles'] = subtitle_tracks
            except:
                video_info['subtitles'] = None
            
            return video_info
            
        except Exception as e:
            print(f"Error extracting YouTube video info: {e}")
            return None
    
    def extract_subtitles_from_page(self):
        try:
            subtitles = self.driver.execute_script("""
                var tracks = document.querySelectorAll('track[kind="subtitles"], track[kind="captions"]');
                var result = [];
                for(var i = 0; i < tracks.length; i++) {
                    result.push({
                        src: tracks[i].src,
                        srclang: tracks[i].srclang,
                        label: tracks[i].label
                    });
                }
                return result;
            """)
            return subtitles if subtitles else None
        except:
            return None
    
    def extract_url_from_json(self, data, key):
        if isinstance(data, dict):
            for k, v in data.items():
                if k == key and isinstance(v, str) and v.startswith('http'):
                    return v
                elif isinstance(v, (dict, list)):
                    result = self.extract_url_from_json(v, key)
                    if result:
                        return result
        elif isinstance(data, list):
            for item in data:
                result = self.extract_url_from_json(item, key)
                if result:
                    return result
        return None
    
    def download_video(self, video_url, filename):
        if not video_url:
            print("No video URL available")
            return False
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': self.driver.current_url
            }
            
            response = requests.get(video_url, headers=headers, stream=True)
            response.raise_for_status()
            
            video_path = f"{self.download_dir}/videos/{filename}.mp4"
            with open(video_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"Video downloaded: {video_path}")
            return True
            
        except Exception as e:
            print(f"Error downloading video: {e}")
            return False
    
    def download_subtitles(self, subtitles, filename):
        if not subtitles:
            print("No subtitles available")
            return False
        
        try:
            subtitle_path = f"{self.download_dir}/subtitles/{filename}.json"
            with open(subtitle_path, 'w', encoding='utf-8') as f:
                json.dump(subtitles, f, ensure_ascii=False, indent=2)
            
            print(f"Subtitles saved: {subtitle_path}")
            
            if isinstance(subtitles, list) and len(subtitles) > 0:
                if 'src' in subtitles[0]:
                    for i, sub in enumerate(subtitles):
                        if sub.get('src'):
                            try:
                                response = requests.get(sub['src'])
                                response.raise_for_status()
                                lang = sub.get('srclang', f'lang{i}')
                                vtt_path = f"{self.download_dir}/subtitles/{filename}_{lang}.vtt"
                                with open(vtt_path, 'w', encoding='utf-8') as f:
                                    f.write(response.text)
                                print(f"VTT subtitle downloaded: {vtt_path}")
                            except:
                                pass
            
            return True
            
        except Exception as e:
            print(f"Error saving subtitles: {e}")
            return False
    
    def save_caption(self, caption, filename):
        if not caption:
            return False
        
        try:
            caption_path = f"{self.download_dir}/subtitles/{filename}_caption.txt"
            with open(caption_path, 'w', encoding='utf-8') as f:
                f.write(caption)
            print(f"Caption saved: {caption_path}")
            return True
        except Exception as e:
            print(f"Error saving caption: {e}")
            return False
    
    def download_from_url(self, url):
        platform = self.identify_platform(url)
        print(f"Detected platform: {platform}")
        
        timestamp = str(int(time.time()))
        filename = f"{platform}_{timestamp}"
        
        if platform == 'tiktok':
            video_info = self.extract_video_info_tiktok(url)
        elif platform == 'instagram':
            video_info = self.extract_video_info_instagram(url)
        elif platform == 'youtube':
            video_info = self.extract_video_info_youtube(url)
        else:
            print(f"Platform {platform} not fully supported yet")
            video_info = self.extract_generic_video_info(url)
        
        if video_info:
            print(f"Extracted video info: {json.dumps(video_info, indent=2)}")
            
            if video_info.get('video_url'):
                self.download_video(video_info['video_url'], filename)
            
            if video_info.get('subtitles'):
                self.download_subtitles(video_info['subtitles'], filename)
            
            if video_info.get('caption'):
                self.save_caption(video_info['caption'], filename)
            
            return True
        
        return False
    
    def extract_generic_video_info(self, url):
        try:
            self.driver.get(url)
            time.sleep(3)
            
            video_info = {}
            
            try:
                video_element = self.driver.find_element(By.TAG_NAME, "video")
                video_info['video_url'] = video_element.get_attribute("src")
            except:
                video_info['video_url'] = None
            
            video_info['subtitles'] = self.extract_subtitles_from_page()
            
            return video_info
            
        except Exception as e:
            print(f"Error extracting generic video info: {e}")
            return None
    
    def close(self):
        if self.driver:
            self.driver.quit()
        # Clean up temporary directory
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            import shutil
            try:
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass