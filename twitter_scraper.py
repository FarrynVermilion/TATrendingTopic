import asyncio
import csv
import os
import json
from datetime import datetime, timedelta
import glob
import random
from collections import Counter
from textblob import TextBlob
from twikit import Client

# MONKEY PATCH: Remove this block when twikit is updated to fix ON_DEMAND_FILE_REGEX
import re
_tx_mod = __import__('twikit.x_client_transaction.transaction', fromlist=['ClientTransaction'])
_tx_mod.ON_DEMAND_FILE_REGEX = re.compile(
    r""",(\d+):["']ondemand\.s["']""", flags=(re.VERBOSE | re.MULTILINE))
_tx_mod.ON_DEMAND_HASH_PATTERN = r',{}:"([0-9a-f]+)"'

async def _patched_get_indices(self, home_page_response, session, headers):
    key_byte_indices = []
    response = self.validate_response(home_page_response) or self.home_page_response
    on_demand_file_index = _tx_mod.ON_DEMAND_FILE_REGEX.search(str(response)).group(1)
    regex = re.compile(_tx_mod.ON_DEMAND_HASH_PATTERN.format(on_demand_file_index))
    filename = regex.search(str(response)).group(1)
    on_demand_file_url = f"https://abs.twimg.com/responsive-web/client-web/ondemand.s.{filename}a.js"
    on_demand_file_response = await session.request(method="GET", url=on_demand_file_url, headers=headers)
    key_byte_indices_match = _tx_mod.INDICES_REGEX.finditer(str(on_demand_file_response.text))
    for item in key_byte_indices_match:
        key_byte_indices.append(item.group(2))
    if not key_byte_indices:
        raise Exception("Couldn't get KEY_BYTE indices")
    key_byte_indices = list(map(int, key_byte_indices))
    return key_byte_indices[0], key_byte_indices[1:]

_tx_mod.ClientTransaction.get_indices = _patched_get_indices
# END MONKEY PATCH

# username = wanderingpadoru
# email = anandareynalwijaya.99@gmail.com
# password = IJustWant2DieRightN0w
# auth_token = 49ca16333ca5afb5638cf414b0ce75ebb22eaffe
# ct0 = 67902afc8ce469b5779437e7426c0fb59b6f861d9d848abdc38b7f82779ad05f7ed30e06c4d25daa6ff3252c28438d4d78deea088bc53e3d7c790f24af34fac1b1d2554a986d3842a1b743d942854309
async def authenticate(client, cookies_file):
    """Authenticates to Twitter, using saved cookies if available."""
    if os.path.exists(cookies_file):
        print(f"Loading saved cookies from {os.path.basename(cookies_file)}...")
        try:
            client.load_cookies(cookies_file)
            print("Successfully loaded cookies.")
            return True
        except Exception as e:
            print(f"Failed to load saved cookies: {e}")
            print("Proceeding to fresh login...")

    print("-" * 60)
    print("ACTION REQUIRED: Twitter Authentication")
    print("Please enter your X (Twitter) credentials to generate a session cookie.")
    print("-" * 60)
    
    try:
        username = input("Enter your Twitter Username (Handle): ")
        email = input("Enter your Twitter Email: ")
        password = input("Enter your Twitter Password: ")
        
        print("Logging in to Twitter...")
        await client.login(
            auth_info_1=username,
            auth_info_2=email,
            password=password
        )
        client.save_cookies(cookies_file)
        print("Login successful! Cookies saved for future sessions.")
        return True
    except Exception as e:
        error_msg = str(e)
        print(f"\n[!] Authentication failed: {error_msg}")
        
        if "status: 403" in error_msg:
            print("\n[!] CLOUDFLARE BLOCK DETECTED.")
            print("Twitter/X is blocking automated login attempts. Using manual cookies is required.")
        
        print("\nPlease provide your session cookies manually to continue.")
        print("-" * 60)
        print("HOW TO GET COOKIES:")
        print("1. Open X (Twitter) in your browser and log in.")
        print("2. Open Developer Tools (F12 or Ctrl+Shift+I).")
        print("3. Go to the 'Application' tab -> 'Cookies' -> 'https://x.com'.")
        print("4. Find the values for 'auth_token' and 'ct0'.")
        print("-" * 60)
        
        auth_token = input("Enter 'auth_token' value: ").strip()
        ct0 = input("Enter 'ct0' value: ").strip()
        
        if auth_token and ct0:
            cookies = {
                'auth_token': auth_token,
                'ct0': ct0
            }
            # Twikit expects cookies in a specific format or directly set
            # For simpler injection, we can save them to a temporary file and load them
            with open(cookies_file, 'w') as f:
                json.dump(cookies, f)
            client.load_cookies(cookies_file)
            print("Cookies applied and saved!")
            return True
        else:
            print("Missing required cookies. Aborting.")
            return False

def analyze_sentiment(text):
    """Simple sentiment analysis using TextBlob."""
    if not text:
        return "N/A"
    try:
        blob = TextBlob(text)
        if blob.sentiment.polarity > 0:
            return "Positive"
        elif blob.sentiment.polarity < 0:
            return "Negative"
        else:
            return "Neutral"
    except Exception:
        return "Error"

async def get_trending_topics(client):
    """Fetches current trending topics from Twitter."""
    print("\nFetching current trending topics...")
    try:
        # Twikit get_trends requires a category string as the first positional argument
        trends = await client.get_trends('trending')
        if not trends:
            print("No trending topics found.")
            return []
        
        print("-" * 30)
        print("CURRENT TRENDING TOPICS:")
        # Show top 15 trends
        display_trends = trends[:15]
        for i, trend in enumerate(display_trends, 1):
            count_str = f" ({trend.tweet_count} tweets)" if hasattr(trend, 'tweet_count') and trend.tweet_count else ""
            print(f"{i}. {trend.name}{count_str}")
        print("-" * 30)
        return display_trends
    except Exception as e:
        print(f"Error fetching trends: {e}")
        return []

async def scrape_twitter_search(client, query, start_date=None, end_date=None, max_tweets=50, known_ids=None, search_product='Latest'):
    """Searches Twitter for a query and scrapes the results."""
    posts_data = []
    scraped_ids = set(known_ids) if known_ids else set()
    
    search_query = query
    if start_date:
        search_query += f" since:{start_date}"
    if end_date:
        search_query += f" until:{end_date}"
        
    print(f"Searching for: '{search_query}' using product: '{search_product}'")

    try:
        # Search for tweets using positional arguments (query, product)
        try:
            tweets = await client.search_tweet(search_query, search_product)
        except Exception as e:
            if '404' in str(e) and search_product == 'Latest':
                print("-> Twitter mengembalikan 404 (Tidak ada hasil terbaru). Mencoba fallback ke 'Top' tweet...")
                tweets = await client.search_tweet(search_query, 'Top')
            else:
                raise e

        while len(posts_data) < max_tweets:
            if not tweets:
                break
                
            new_tweets_in_batch = 0
            for tweet in tweets:
                if len(posts_data) >= max_tweets:
                    break
                
                # Skip if we already have this tweet
                if str(tweet.id) in scraped_ids:
                    continue
                
                new_tweets_in_batch += 1
                text = tweet.text.replace('\n', ' ').strip()
                sentiment = analyze_sentiment(text)

                scraped_ids.add(str(tweet.id))
                post_info = {
                    "keyword": query,
                    "tweet_id": tweet.id,
                    "username": tweet.user.name,
                    "handle": tweet.user.screen_name,
                    "text": text,
                    "sentiment": sentiment,
                    "url": f"https://x.com/{tweet.user.screen_name}/status/{tweet.id}",
                    "datetime": tweet.created_at,
                    "likes": tweet.favorite_count,
                    "retweets": tweet.retweet_count,
                    "replies": tweet.reply_count,
                }
                posts_data.append(post_info)
                print(f"[{len(posts_data)}] Scraped tweet by @{tweet.user.screen_name}")

            # If we processed a whole batch and didn't find any new tweets, 
            # it's likely we've already scraped this time period. Stop to save API calls.
            if new_tweets_in_batch == 0:
                print("-> Only found duplicate tweets in this batch. Stopping search for this interval to avoid rate limits.")
                break

            if len(posts_data) < max_tweets:
                print("Fetching next page of results...")
                
                retry_delays = [60, 300, 900] # Menunggu 1 menit, 5 menit, lalu 15 menit
                retry_count = 0
                success = False
                
                while retry_count < len(retry_delays):
                    try:
                        tweets = await tweets.next()
                        success = True
                        break
                    except Exception as e:
                        error_msg = str(e)
                        if '429' in error_msg or 'Rate limit' in error_msg:
                            wait_time = retry_delays[retry_count]
                            print(f"[!] Rate limit exceeded (429). Waiting for {wait_time} seconds before retrying... ({retry_count+1}/{len(retry_delays)})")
                            await asyncio.sleep(wait_time)
                            retry_count += 1
                        else:
                            print(f"-> Pencarian selesai atau mencapai akhir halaman (API error/No cursor): {e}")
                            break
                            
                if not success:
                    print("-> Berhenti mengambil halaman selanjutnya (Batas retry tercapai atau Error).")
                    break
                    
                if not tweets:
                    break
                await asyncio.sleep(2) # Be polite to the API

    except Exception as e:
        if '404' in str(e):
            print("-> Pencarian selesai: Tidak ada (lagi) tweet yang ditemukan untuk query/tanggal ini.")
        else:
            print(f"An error occurred during search: {e}")

    return posts_data

async def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    cookie_files = glob.glob(os.path.join(current_dir, 'twitter_cookies*.json'))
    clients = []
    
    try:
        if not cookie_files:
            print("No saved cookies found. Setting up first account...")
            client = Client('en-US')
            cookies_file = os.path.join(current_dir, 'twitter_cookies.json')
            success = await authenticate(client, cookies_file)
            if success:
                clients.append(client)
                cookie_files.append(cookies_file)
        else:
            for f in cookie_files:
                client = Client('en-US')
                success = await authenticate(client, f)
                if success:
                    clients.append(client)

        while True:
            add_more = input(f"\nCurrently have {len(clients)} accounts loaded. Add another? (y/n): ").strip().lower()
            if add_more == 'y':
                client = Client('en-US')
                idx = len(clients) + 1
                while True:
                    cookies_file = os.path.join(current_dir, f'twitter_cookies_{idx}.json')
                    if not os.path.exists(cookies_file) and cookies_file not in cookie_files:
                        break
                    idx += 1
                success = await authenticate(client, cookies_file)
                if success:
                    clients.append(client)
                    cookie_files.append(cookies_file)
            else:
                break

        if not clients:
            print("No authenticated clients. Exiting...")
            return

        while True:
            print("\n" + "="*40)
            print("       TWITTER SCRAPER MENU       ")
            print("="*40)
            print("0. Quit")
            print("1. Search Custom Query (Latest)")
            print("2. Search Trending Topics")
            print("3. Search Custom Query by Intervals")
            print("4. Continuous Search with Interval & Jitter")
            
            choice = input("\nSelect an option (0-4): ").strip()
            
            if choice == '0':
                print("Exiting...")
                break
            
            search_query = ""
            if choice == '1':
                search_query = input("Enter your search query: ").strip()
                if not search_query:
                    continue
            elif choice == '2':
                trends = await get_trending_topics(clients[0])
                if not trends:
                    continue
                trend_idx = input("Select a trend number to scrape (or 'b' to go back): ").strip()
                if trend_idx.lower() == 'b':
                    continue
                try:
                    selected_trend = trends[int(trend_idx) - 1]
                    search_query = selected_trend.name
                    print(f"Selected Trend: {search_query}")
                except (ValueError, IndexError):
                    print("Invalid selection.")
                    continue
            elif choice == '3':
                search_query = input("Enter your search query: ").strip()
                if not search_query:
                    continue
                
                start_date_str = input("Enter start datetime (YYYY-MM-DD HH:MM:SS): ").strip()
                end_date_str = input("Enter end datetime (YYYY-MM-DD HH:MM:SS): ").strip()
                
                try:
                    start_dt = datetime.strptime(start_date_str, "%Y-%m-%d %H:%M:%S")
                    end_dt = datetime.strptime(end_date_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    print("Invalid datetime format. Please use YYYY-MM-DD HH:MM:SS.")
                    continue
                
                interval_input = input("Enter interval size in hours (default 2): ").strip()
                try:
                    interval_hours = float(interval_input) if interval_input else 2.0
                except ValueError:
                    print("Invalid input. Using default 2.0 hours.")
                    interval_hours = 2.0

                output_file = input('Enter name for output CSV file (without .csv): ').strip()
                if not output_file:
                    output_file = "scraped_tweets"
                if not output_file.endswith('.csv'):
                    output_file += '.csv'
                
                max_results = 20
                print(f"Starting {interval_hours}-hour interval scraper (with +/- 30m jitter) for query: '{search_query}' from {start_date_str} to {end_date_str}")
                
                known_ids = set()
                existing_data = []
                file_exists = os.path.exists(output_file)
                if file_exists:
                    try:
                        with open(output_file, 'r', encoding='utf-8') as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                if 'tweet_id' in row:
                                    known_ids.add(row['tweet_id'])
                                existing_data.append(row)
                        print(f"Found {len(known_ids)} existing tweets in {output_file}. Duplicates will be skipped.")
                    except Exception as e:
                        print(f"Warning reading existing file: {e}")
                
                all_data = existing_data.copy()
                
                intervals = []
                current_start = start_dt
                while current_start < end_dt:
                    # Add random jitter between -30 and +30 minutes
                    jitter_minutes = random.randint(-30, 30)
                    current_interval = timedelta(hours=interval_hours) + timedelta(minutes=jitter_minutes)
                    # Ensure interval is at least 10 minutes to avoid going backwards or getting stuck
                    current_interval = max(timedelta(minutes=10), current_interval)
                    
                    current_end = current_start + current_interval
                    if current_end > end_dt:
                        current_end = end_dt
                    
                    intervals.append((current_start, current_end))
                    current_start = current_end + timedelta(seconds=1)
                    
                async def process_interval(interval, client_idx):
                    start, end = interval
                    # Convert to epoch timestamps for exact time search
                    start_epoch = int(start.timestamp())
                    end_epoch = int(end.timestamp())
                    
                    interval_query = f"{search_query} since_time:{start_epoch} until_time:{end_epoch}"
                    
                    c = clients[client_idx]
                    print(f"\n[INTERVAL] Scraping from {start} to {end} [Account {client_idx + 1}]")
                    return await scrape_twitter_search(c, interval_query, None, None, max_results, known_ids, search_product='Latest')
                    
                for i in range(0, len(intervals), len(clients)):
                    batch_intervals = intervals[i:i+len(clients)]
                    tasks = [process_interval(interval, j) for j, interval in enumerate(batch_intervals)]
                    
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    batch_new_data = 0
                    for result in results:
                        if isinstance(result, Exception):
                            print(f"[!] Error in interval scraping: {result}")
                            continue
                        if result:
                            all_data.extend(result)
                            batch_new_data += len(result)
                            for row in result:
                                if 'tweet_id' in row:
                                    known_ids.add(str(row['tweet_id']))
                    
                    if batch_new_data > 0:
                        
                        date_counts = Counter()
                        for row in all_data:
                            try:
                                dt_obj = datetime.strptime(row['datetime'], '%a %b %d %H:%M:%S %z %Y')
                                date_str = dt_obj.strftime('%Y-%m-%d')
                                row['datetime'] = dt_obj.strftime('%Y-%m-%d %H:%M:%S')
                            except Exception:
                                try:
                                    dt_obj = datetime.strptime(row['datetime'], '%Y-%m-%d %H:%M:%S')
                                    date_str = dt_obj.strftime('%Y-%m-%d')
                                except Exception:
                                    date_str = str(row['datetime'])[:10]
                            row['parsed_date'] = date_str
                            date_counts[date_str] += 1
                        
                        for row in all_data:
                            row['tweets_per_date'] = date_counts[row['parsed_date']]
                            if 'parsed_date' in row:
                                del row['parsed_date']
                        
                        fieldnames = list(all_data[0].keys())
                        with open(output_file, 'w', newline='', encoding='utf-8') as f:
                            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                            writer.writeheader()
                            writer.writerows(all_data)
                        print(f"Saved {batch_new_data} new tweets (Total: {len(all_data)})")
                    else:
                        print("No new data for this batch of intervals.")
                    
                    if i + len(clients) < len(intervals):
                        await asyncio.sleep(2)
                
                print(f"\nCompleted interval scraping! Total tweets saved: {len(all_data)}")
                continue
            elif choice == '4':
                search_queries_input = input("Enter your search queries (comma-separated): ").strip()
                if not search_queries_input:
                    continue
                
                queries = [q.strip() for q in search_queries_input.split(',') if q.strip()]
                
                target_amount_input = input("Enter the desired total amount of unique tweets to scrape per query (default 500): ").strip()
                try:
                    target_amount = int(target_amount_input) if target_amount_input else 500
                except ValueError:
                    print("Invalid input. Using default 500.")
                    target_amount = 500
                
                interval_input = input("Enter base interval between searches in minutes (default 30): ").strip()
                try:
                    interval_minutes = float(interval_input) if interval_input else 30.0
                except ValueError:
                    print("Invalid input. Using default 30.0 minutes.")
                    interval_minutes = 30.0
                    
                jitter_input = input("Enter max jitter in minutes (default 5): ").strip()
                try:
                    jitter_minutes = float(jitter_input) if jitter_input else 5.0
                except ValueError:
                    print("Invalid input. Using default 5.0 minutes.")
                    jitter_minutes = 5.0

                max_results_input = input("Enter the maximum number of tweets to scrape per run (default 50): ").strip()
                try:
                    max_results = int(max_results_input) if max_results_input else 50
                except ValueError:
                    print("Invalid number. Using default 50.")
                    max_results = 50

                output_file = input('Enter name for output CSV file (without .csv): ').strip()
                if not output_file:
                    output_file = "continuous_scraped_tweets"
                if not output_file.endswith('.csv'):
                    output_file += '.csv'
                
                print(f"\nStarting continuous scraper for queries: {', '.join(queries)}.")
                print(f"Target: {target_amount} unique tweets per query. Interval: {interval_minutes}m +/- {jitter_minutes}m jitter. Press Ctrl+C to stop.")
                
                known_ids = set()
                existing_data = []
                query_counts = {q: 0 for q in queries}
                
                file_exists = os.path.exists(output_file)
                if file_exists:
                    try:
                        with open(output_file, 'r', encoding='utf-8') as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                if 'tweet_id' in row:
                                    known_ids.add(row['tweet_id'])
                                existing_data.append(row)
                                kw = row.get('keyword')
                                if kw in query_counts:
                                    query_counts[kw] += 1
                        print(f"Found {len(known_ids)} existing tweets in {output_file}. Duplicates will be skipped.")
                        for q, c in query_counts.items():
                            print(f" - '{q}': {c} existing tweets")
                    except Exception as e:
                        print(f"Warning reading existing file: {e}")

                all_data = existing_data.copy()
                
                try:
                    while any(count < target_amount for count in query_counts.values()):
                        for query in queries:
                            if query_counts[query] >= target_amount:
                                continue
                                
                            print(f"\n[CONTINUOUS] Scraping latest tweets for '{query}' at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                            current_max = min(max_results, target_amount - query_counts[query])
                            new_data = await scrape_twitter_search(clients[0], query, None, None, current_max, known_ids, search_product='Latest')
                            
                            if new_data:
                                all_data.extend(new_data)
                                query_counts[query] += len(new_data)
                                for row in new_data:
                                    if 'tweet_id' in row:
                                        known_ids.add(str(row['tweet_id']))
                                
                                date_counts = Counter()
                                for row in all_data:
                                    try:
                                        dt_obj = datetime.strptime(row['datetime'], '%a %b %d %H:%M:%S %z %Y')
                                        date_str = dt_obj.strftime('%Y-%m-%d')
                                        row['datetime'] = dt_obj.strftime('%Y-%m-%d %H:%M:%S')
                                    except Exception:
                                        try:
                                            dt_obj = datetime.strptime(row['datetime'], '%Y-%m-%d %H:%M:%S')
                                            date_str = dt_obj.strftime('%Y-%m-%d')
                                        except Exception:
                                            date_str = str(row['datetime'])[:10]
                                    row['parsed_date'] = date_str
                                    date_counts[date_str] += 1
                                
                                for row in all_data:
                                    row['tweets_per_date'] = date_counts[row['parsed_date']]
                                    if 'parsed_date' in row:
                                        del row['parsed_date']
                                
                                fieldnames = list(all_data[0].keys())
                                with open(output_file, 'w', newline='', encoding='utf-8') as f:
                                    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                                    writer.writeheader()
                                    writer.writerows(all_data)
                                print(f"Saved {len(new_data)} new tweets for '{query}' (Query total: {query_counts[query]}/{target_amount}, Overall: {len(all_data)})")
                            else:
                                print(f"No new data found for '{query}' this run.")
                                
                        if all(count >= target_amount for count in query_counts.values()):
                            print(f"\nReached desired target of {target_amount} unique tweets for all queries. Stopping.")
                            break
                            
                        actual_jitter = random.uniform(-jitter_minutes, jitter_minutes)
                        wait_time_minutes = interval_minutes + actual_jitter
                        wait_time_minutes = max(0.5, wait_time_minutes) # Minimum wait of 30 seconds
                        
                        wait_seconds = int(wait_time_minutes * 60)
                        next_run = datetime.now() + timedelta(seconds=wait_seconds)
                        print(f"Waiting for {wait_time_minutes:.2f} minutes... Next run at {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                        await asyncio.sleep(wait_seconds)
                except asyncio.CancelledError:
                    print("\nContinuous scraping stopped.")
                except KeyboardInterrupt:
                    print("\nContinuous scraping stopped by user.")
                
                continue
            else:
                print("Invalid choice.")
                continue

            start_date = input("Enter start date (YYYY-MM-DD) [Leave empty for no start date]: ").strip()
            end_date = input("Enter end date (YYYY-MM-DD) [Leave empty for no end date]: ").strip()
            max_results_input = input("Enter the maximum number of tweets to scrape (default 50): ").strip()
            output_file = input('Enter name for output CSV file (without .csv): ').strip()
            
            if not output_file:
                output_file = "scraped_tweets"
            if not output_file.endswith('.csv'):
                output_file += '.csv'
            
            try:
                max_results = int(max_results_input) if max_results_input else 50
            except ValueError:
                print("Invalid number. Using default 50.")
                max_results = 50
                
            # Check for existing file to handle appending and duplicates
            known_ids = set()
            existing_data = []
            file_exists = os.path.exists(output_file)
            if file_exists:
                try:
                    with open(output_file, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            if 'tweet_id' in row:
                                known_ids.add(row['tweet_id'])
                            existing_data.append(row)
                    print(f"Found {len(known_ids)} existing tweets in {output_file}. Duplicates will be skipped.")
                except Exception as e:
                    print(f"Warning reading existing file: {e}")

            print(f"Starting scraper for query: '{search_query}' from {start_date or 'beginning'} to {end_date or 'now'}")
            data = await scrape_twitter_search(clients[0], search_query, start_date, end_date, max_results, known_ids, search_product='Latest')

            if data:
                all_data = existing_data + data
                
                # Calculate the number of scraped tweets per date
                date_counts = Counter()
                for row in all_data:
                    try:
                        # Twikit datetime format: "Fri Nov 03 14:02:32 +0000 2023"
                        dt_obj = datetime.strptime(row['datetime'], '%a %b %d %H:%M:%S %z %Y')
                        date_str = dt_obj.strftime('%Y-%m-%d')
                        row['datetime'] = dt_obj.strftime('%Y-%m-%d %H:%M:%S')
                    except Exception:
                        try:
                            # If previously parsed or saved differently
                            dt_obj = datetime.strptime(row['datetime'], '%Y-%m-%d %H:%M:%S')
                            date_str = dt_obj.strftime('%Y-%m-%d')
                        except Exception:
                            # Fallback just in case
                            date_str = str(row['datetime'])[:10]
                    row['parsed_date'] = date_str
                    date_counts[date_str] += 1
                
                for row in all_data:
                    row['tweets_per_date'] = date_counts[row['parsed_date']]
                    del row['parsed_date']  # Remove temporary key to keep CSV clean
                
                fieldnames = list(data[0].keys())

                with open(output_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                    writer.writeheader()
                    writer.writerows(all_data)
                print(f"Successfully saved {len(data)} new tweets to {output_file} (Total rows: {len(all_data)})")
            else:
                print("No new data scraped.")
                
    except Exception as e:
        print(f"Critical error: {e}")

if __name__ == "__main__":
    asyncio.run(main())