import csv
import os
import re
import time
from datetime import datetime, timedelta
from collections import Counter
from textblob import TextBlob
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def setup_driver():
    """Sets up the Chrome WebDriver."""
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  # Keep commented to see the login screen
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Use a standard user agent to reduce bot detection
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
    
    # Add persistent profile to store login session (cookies, etc.)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    profile_dir = os.path.join(current_dir, "threads_selenium_profile")
    options.add_argument(f"--user-data-dir={profile_dir}")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def parse_threads_date(date_str):
    """Parses Threads relative or absolute date strings."""
    if not date_str:
        return None
    
    now = datetime.now()
    date_str = date_str.strip()
    
    try:
        # Relative time (e.g., "20s", "5m", "2h", "3d")
        if date_str.endswith('s') and date_str[:-1].isdigit():
            return now - timedelta(seconds=int(date_str[:-1]))
        elif date_str.endswith('m') and date_str[:-1].isdigit():
            return now - timedelta(minutes=int(date_str[:-1]))
        elif date_str.endswith('h') and date_str[:-1].isdigit():
            return now - timedelta(hours=int(date_str[:-1]))
        elif date_str.endswith('d') and date_str[:-1].isdigit():
            return now - timedelta(days=int(date_str[:-1]))
        
        # Absolute dates (e.g., "Oct 15" or "Oct 15, 2023")
        if ',' in date_str:
            return datetime.strptime(date_str, "%b %d, %Y")
        else:
            # "Oct 15" -> assumes current year, handles rollover if date is in future
            dt = datetime.strptime(date_str, "%b %d")
            dt = dt.replace(year=now.year)
            if dt > now:
                dt = dt.replace(year=now.year - 1)
            return dt
    except ValueError:
        return None

def scrape_threads_search(driver, query, start_date, end_date, max_posts=50, known_ids=None):
    """
    Searches Threads for a query and scrapes the results.
    Assumes driver is already initialized and logged in.
    """
    posts_data = []
    scraped_ids = set(known_ids) if known_ids else set()
    
    # Handle optional end_date (default to now)
    if not end_date:
        end_dt = datetime.now()
    else:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(hours=23, minutes=59, seconds=59)
        except ValueError:
            end_dt = datetime.now()

    # Handle optional start_date (default to start of today)
    if not start_date:
        now = datetime.now()
        start_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            start_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    try:
        # Perform Search
        # Use after: and before: operators in the search query
        # Adjust dates by 1 day to ensure inclusive range (assuming strict inequality for after/before)
        q_start = (start_dt - timedelta(days=1)).strftime('%Y-%m-%d')
        q_end = (end_dt + timedelta(days=1)).strftime('%Y-%m-%d')
        search_query_str = f"{query} after:{q_start} before:{q_end}"
        print(f"Searching for: {search_query_str}")

        # Threads search URL
        encoded_query = search_query_str.replace(' ', '%20').replace(':', '%3A')
        search_url = f"https://www.threads.net/search?q={encoded_query}&serp_type=default"
        driver.get(search_url)

        # Wait for results to load (look for any feed content)
        wait = WebDriverWait(driver, 20)
        # Waiting for a link that looks like a profile link as a proxy for content loading
        wait.until(EC.presence_of_element_located((By.XPATH, '//a[starts-with(@href, "/@")]')))

        # 3. Scrape Loop
        last_height = driver.execute_script("return document.body.scrollHeight")
        
        while len(posts_data) < max_posts:
            # Find all elements that look like post containers.
            # Strategy: Find the timestamp/permalink anchor, then traverse up to the container.
            # Threads permalinks usually look like /@username/post/ID
            
            # This XPath finds 'a' tags containing '/post/' in href, which are usually the timestamps/permalinks
            permalink_elements = driver.find_elements(By.XPATH, '//a[contains(@href, "/post/")]')
            
            for permalink in permalink_elements:
                if len(posts_data) >= max_posts:
                    break
                
                try:
                    # Fix URL: Ensure it uses threads.net (sometimes resolves to threads.com incorrectly)
                    raw_url = permalink.get_attribute("href")
                    post_url = raw_url.replace("threads.com", "threads.net")
                    
                    if post_url in scraped_ids:
                        continue

                    # Attempt to find the container relative to the permalink
                    # The container is usually several levels up. We can try to extract data relative to this anchor.
                    
                    # 1. Get Username (usually an anchor with href="/@username" nearby)
                    # We look for a preceding sibling or ancestor's descendant that links to the user.
                    # Updated to 7 levels up to capture the full post body, not just the header.
                    container = permalink.find_element(By.XPATH, "./../../../../../../..") 
                    
                    # Extract Username specifically if possible
                    try:
                        user_element = container.find_element(By.XPATH, './/a[starts-with(@href, "/@") and not(contains(@href, "/post/"))]')
                        username = user_element.text
                        handle = user_element.get_attribute("href").split('/')[-1]
                    except:
                        username = "Unknown"
                        handle = "Unknown"

                    post_time = permalink.text.strip()
                    
                    # Filter by date
                    post_dt = parse_threads_date(post_time)
                    if post_dt:
                        if not (start_dt <= post_dt <= end_dt):
                            continue
                    else:
                        continue

                    # Extract Text
                    # Attempt to find the specific text element to avoid capturing header (user/time) and footer (counts)
                    text = ""
                    try:
                        # More robust XPath: checks for 'white-space' and 'pre-wrap' separately to handle spacing differences
                        text_element = container.find_element(By.XPATH, './/*[contains(@style, "white-space") and contains(@style, "pre-wrap")]')
                        text = text_element.text.replace('\n', ' ').strip()
                    except:
                        pass

                    # Fallback: If specific element fails, get full container text and clean it
                    if not text:
                        try:
                            text = container.text.replace('\n', ' ').strip()
                        except:
                            text = ""

                    # General Cleanup (applies to both specific element and fallback text)
                    if username != "Unknown" and text.startswith(username):
                        text = text[len(username):].strip()
                    if text.startswith(post_time):
                        text = text[len(post_time):].strip()
                    
                    # Remove "Translate" and trailing numbers (interaction counts, image counts like 1 / 4, or incomplete 1 /)
                    # Also handles suffixes like 1.3K and words like 'likes'
                    text = re.sub(r'\s*(?:Translate)?(?:(?:\s*[-•]?\s*)?(?:\d+(?:[.,]\d+)?[KkMmBb]?\s*(?:likes|replies|reposts|views)?|[/]\s*\d*))+$', '', text).strip()

                    # Sentiment Analysis using TextBlob
                    sentiment = "N/A"
                    if text:
                        try:
                            blob = TextBlob(text)
                            if blob.sentiment.polarity > 0:
                                sentiment = "Positive"
                            elif blob.sentiment.polarity < 0:
                                sentiment = "Negative"
                            else:
                                sentiment = "Neutral"
                        except Exception as e:
                            print(f"Sentiment error: {e}")

                    scraped_ids.add(post_url)
                    post_info = {
                        "keyword": query,
                        "username": username,
                        "handle": handle,
                        "text": text,
                        "sentiment": sentiment,
                        "url": post_url,
                        "datetime": post_dt
                    }
                    posts_data.append(post_info)
                    print(f"[{len(posts_data)}] Scraped post by {username}")

                except Exception as e:
                    # Skip incomplete posts
                    continue

            # Scroll down with retry mechanism
            scroll_attempts = 0
            while scroll_attempts < 3:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)
                new_height = driver.execute_script("return document.body.scrollHeight")
                
                if new_height > last_height:
                    last_height = new_height
                    break
                
                scroll_attempts += 1
                time.sleep(2)
            
            if scroll_attempts == 3:
                print("No more posts found or end of results.")
                break

    except Exception as e:
        print(f"An error occurred: {e}")

    # Sort by datetime descending (latest to oldest)
    if posts_data:
        posts_data.sort(key=lambda x: x['datetime'], reverse=True)
        # Convert datetime object to string for CSV
        for post in posts_data:
            post['datetime'] = post['datetime'].strftime("%Y-%m-%d %H:%M:%S")

    return posts_data

if __name__ == "__main__":
    driver = setup_driver()
    
    try:
        # Initial Login Check
        print("Opening Threads to check login status...")
        driver.get("https://www.threads.net/")
        time.sleep(3)
        
        # Simple check: if we are on login page or see login button
        if "login" in driver.current_url or len(driver.find_elements(By.XPATH, '//a[@href="/login"]')) > 0:
            print("-" * 60)
            print("ACTION REQUIRED: Please log in to Threads (via Instagram) in the opened browser window.")
            print("Once you are logged in and see your home feed, press ENTER here.")
            print("-" * 60)
            input()
        else:
            print("Already logged in (session restored).")

        while True:
            SEARCH_QUERY = input("\nEnter your search query (or 'q' to quit): ")
            if SEARCH_QUERY.lower() == 'q':
                break
                
            START_DATE = input("Enter start date (YYYY-MM-DD) [Leave empty for today]: ")
            END_DATE = input("Enter end date (YYYY-MM-DD) [Leave empty for now]: ")
            MAX_RESULTS = input("Enter the maximum number of posts to scrape: ")
            OUTPUT_FILE = input('Enter the name of the output CSV file not including .csv extension: ')
            OUTPUT_FILE += '.csv'
            
            try:
                MAX_RESULTS = int(MAX_RESULTS)
            except ValueError:
                print("Invalid number for max posts. Using default 50.")
                MAX_RESULTS = 50

            # Check for existing file to handle appending and duplicates
            known_ids = set()
            existing_data = []
            file_exists = os.path.exists(OUTPUT_FILE)
            if file_exists:
                try:
                    with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            if 'url' in row:
                                known_ids.add(row['url'])
                            existing_data.append(row)
                    print(f"Found {len(known_ids)} existing posts in {OUTPUT_FILE}. Duplicates will be skipped.")
                except Exception as e:
                    print(f"Warning reading existing file: {e}")

            print(f"Starting scraper for query: '{SEARCH_QUERY}' from {START_DATE} to {END_DATE}")
            data = scrape_threads_search(driver, SEARCH_QUERY, START_DATE, END_DATE, MAX_RESULTS, known_ids)

            if data:
                all_data = existing_data + data
                
                # Calculate the number of scraped posts per date
                date_counts = Counter()
                for row in all_data:
                    date_str = str(row.get('datetime', ''))[:10]
                    row['parsed_date'] = date_str
                    date_counts[date_str] += 1
                
                for row in all_data:
                    row['posts_per_date'] = date_counts[row['parsed_date']]
                    del row['parsed_date']  # Remove temporary key to keep CSV clean
                
                fieldnames = list(data[0].keys())

                with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                    writer.writeheader()
                    writer.writerows(all_data)
                print(f"Successfully saved {len(data)} new posts to {OUTPUT_FILE} (Total rows: {len(all_data)})")
            else:
                print("No new data scraped.")
                
    except Exception as e:
        print(f"Critical error: {e}")
    finally:
        print("Closing driver...")
        driver.quit()
