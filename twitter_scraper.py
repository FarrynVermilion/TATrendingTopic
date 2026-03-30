import asyncio
import csv
import os
import json
import glob
import random
import re
from datetime import datetime, timedelta
from collections import Counter
from textblob import TextBlob
from twikit import Client

# =============================================================================
# MONKEY PATCH: Fix for twikit ON_DEMAND_FILE_REGEX
# =============================================================================
try:
    _tx_mod = __import__('twikit.x_client_transaction.transaction', fromlist=['ClientTransaction'])
    _tx_mod.ON_DEMAND_FILE_REGEX = re.compile(r""",(\d+):["']ondemand\.s["']""", flags=(re.VERBOSE | re.MULTILINE))
    _tx_mod.ON_DEMAND_HASH_PATTERN = r',{}:"([0-9a-f]+)"'

    async def _patched_get_indices(self, home_page_response, session, headers):
        key_byte_indices = []
        response = self.validate_response(home_page_response) or self.home_page_response
        match = _tx_mod.ON_DEMAND_FILE_REGEX.search(str(response))
        if not match: raise Exception("ON_DEMAND_FILE_REGEX not found")
        on_demand_idx = match.group(1)
        regex = re.compile(_tx_mod.ON_DEMAND_HASH_PATTERN.format(on_demand_idx))
        match = regex.search(str(response))
        if not match: raise Exception("ON_DEMAND_HASH_PATTERN not found")
        filename = match.group(1)
        url = f"https://abs.twimg.com/responsive-web/client-web/ondemand.s.{filename}a.js"
        resp = await session.request(method="GET", url=url, headers=headers)
        indices_match = _tx_mod.INDICES_REGEX.finditer(str(resp.text))
        for item in indices_match: key_byte_indices.append(item.group(2))
        if not key_byte_indices: raise Exception("Couldn't get KEY_BYTE indices")
        return int(key_byte_indices[0]), list(map(int, key_byte_indices[1:]))

    _tx_mod.ClientTransaction.get_indices = _patched_get_indices
except Exception as e:
    print(f"Warning: Twikit monkey patch failed: {e}")

# =============================================================================

FIELDNAMES = [
    "keyword", "tweet_id", "username", "handle", "text", "sentiment", 
    "url", "datetime", "likes", "retweets", "replies", "tweets_per_date"
]

# -----------------------------------------------------------------------------
# CORE MANAGERS & UTILITIES
# -----------------------------------------------------------------------------

class ScraperState:
    """Manages global state for rate limits and active accounts."""
    rate_limits = {}  # {client_id: resume_datetime}
    busy_accounts = set() # {client_id}

    @classmethod
    def mark_limited(cls, client):
        cls.rate_limits[id(client)] = datetime.now() + timedelta(minutes=15)
    
    @classmethod
    def is_limited(cls, client):
        res_time = cls.rate_limits.get(id(client))
        return res_time and res_time > datetime.now()

    @classmethod
    def set_busy(cls, client, status=True):
        if status: cls.busy_accounts.add(id(client))
        else: cls.busy_accounts.discard(id(client))

    @classmethod
    def find_best_account(cls, clients, preferred_idx=0):
        """Finds the first available non-limited, non-busy account."""
        # Try preferred first
        indices = list(range(len(clients)))
        start_pos = preferred_idx % len(clients)
        ordered_indices = indices[start_pos:] + indices[:start_pos]
        
        for idx in ordered_indices:
            c = clients[idx]
            if not cls.is_limited(c) and id(c) not in cls.busy_accounts:
                return c, idx
        return None, -1

def log(msg, category="INFO"):
    """Standardized logging."""
    print(f"[{category}] {msg}")

def get_input(prompt, default=None, type_func=str):
    msg = f"{prompt} (default {default}): " if default is not None else f"{prompt}: "
    val = input(msg).strip()
    if not val: return default
    try: return type_func(val)
    except ValueError:
        log(f"Invalid input. Using default {default}.", "WARN")
        return default

def analyze_sentiment(text):
    if not text: return "N/A"
    try:
        blob = TextBlob(text)
        if blob.sentiment.polarity > 0: return "Positive"
        if blob.sentiment.polarity < 0: return "Negative"
        return "Neutral"
    except Exception: return "Error"

# -----------------------------------------------------------------------------
# DATA HANDLING
# -----------------------------------------------------------------------------

def process_and_save(all_data, filepath):
    """Calculates metadata and saves to CSV."""
    if not all_data: return
    if not filepath.lower().endswith('.csv'): filepath += '.csv'
    
    # Calculate tweets_per_date
    date_counts = Counter()
    for row in all_data:
        dt_str = str(row.get('datetime', ''))
        # Standardize format
        for fmt in ('%a %b %d %H:%M:%S %z %Y', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
            try:
                dt_obj = datetime.strptime(dt_str, fmt)
                date_str = dt_obj.strftime('%Y-%m-%d')
                row['datetime'] = dt_obj.strftime('%Y-%m-%d %H:%M:%S')
                row['_date_key'] = date_str
                break
            except Exception: continue
        
        if '_date_key' not in row:
            row['_date_key'] = dt_str[:10]
        date_counts[row['_date_key']] += 1

    for row in all_data:
        row['tweets_per_date'] = date_counts.get(row.get('_date_key'), 0)
        if '_date_key' in row: del row['_date_key']

    try:
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(all_data)
        log(f"Saved {len(all_data)} records to {filepath}.", "FILE")
    except Exception as e:
        log(f"Save error: {e}", "ERROR")

def load_data(filepath):
    """Loads existing data from CSV."""
    data, known_ids = [], set()
    if not filepath.lower().endswith('.csv'): filepath += '.csv'
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data.append(row)
                    if 'tweet_id' in row: known_ids.add(str(row['tweet_id']))
            log(f"Loaded {len(data)} existing records.", "FILE")
        except Exception as e: log(f"Load error: {e}", "ERROR")
    return data, known_ids

# -----------------------------------------------------------------------------
# AUTHENTICATION
# -----------------------------------------------------------------------------

async def authenticate(client, cookies_file):
    """Authenticates to Twitter using cookies or fresh login."""
    if os.path.exists(cookies_file):
        try:
            client.load_cookies(cookies_file)
            log(f"Loaded {os.path.basename(cookies_file)}.", "AUTH")
            return True
        except Exception: pass

    log(f"Login required for {os.path.basename(cookies_file)}", "AUTH")
    try:
        u, e, p = input("User: "), input("Email: "), input("Pass: ")
        await client.login(auth_info_1=u, auth_info_2=e, password=p)
        client.save_cookies(cookies_file)
        return True
    except Exception as e:
        log(f"Auto-login failed: {e}. Try manual cookies.", "WARN")
        at, ct = input("auth_token: ").strip(), input("ct0: ").strip()
        if at and ct:
            with open(cookies_file, 'w') as f: json.dump({'auth_token': at, 'ct0': ct}, f)
            client.load_cookies(cookies_file)
            return True
    return False

# -----------------------------------------------------------------------------
# SCRAPING ENGINE
# -----------------------------------------------------------------------------

async def scrape_twitter_search(clients, start_idx, query, start_date=None, end_date=None, max_raw=50, known_ids=None, max_dup_pages=1):
    """Core search logic with auto-swapping for rate limits and tiered retry."""
    results, total_processed = [], 0
    scraped_ids = set(known_ids) if known_ids else set()
    consecutive_dup_pages = 0
    
    full_query = query
    if start_date: full_query += f" since:{start_date}"
    if end_date: full_query += f" until:{end_date}"

    curr_idx = start_idx
    wait_level = 0
    wait_delays = [60, 300, 1800] # 1m, 5m, 30m

    while total_processed < max_raw:
        client, active_idx = ScraperState.find_best_account(clients, curr_idx)
        
        if not client:
            wait_time = wait_delays[min(wait_level, len(wait_delays)-1)]
            log(f"All accounts limited. Waiting {wait_time//60}m...", "LIMIT")
            await asyncio.sleep(wait_time)
            wait_level += 1
            continue

        curr_idx = active_idx
        ScraperState.set_busy(client, True)
        log(f"Using Account {curr_idx+1} for '{query}'", "SEARCH")
        
        try:
            try:
                tweets = await client.search_tweet(full_query, 'Latest')
            except Exception as e:
                if '404' in str(e): tweets = await client.search_tweet(full_query, 'Top')
                else: raise e

            while total_processed < max_raw and tweets:
                batch_saw_new = False
                for t in tweets:
                    total_processed += 1
                    if total_processed > max_raw: break
                    
                    if str(t.id) in scraped_ids:
                        print(f"[{total_processed}] Duplicate @{t.user.screen_name}")
                        continue
                    
                    scraped_ids.add(str(t.id))
                    batch_saw_new = True
                    results.append({
                        "keyword": query, "tweet_id": t.id, "username": t.user.name,
                        "handle": t.user.screen_name, "text": t.text.replace('\n', ' '),
                        "sentiment": analyze_sentiment(t.text), "url": f"https://x.com/status/{t.id}",
                        "datetime": t.created_at, "likes": t.favorite_count,
                        "retweets": t.retweet_count, "replies": t.reply_count,
                    })
                    print(f"[{total_processed}] Scraped: @{t.user.screen_name} (New: {len(results)})")

                if not batch_saw_new:
                    consecutive_dup_pages += 1
                    if consecutive_dup_pages >= max_dup_pages:
                        log(f"Stopping search: reached {consecutive_dup_pages} consecutive duplicate-only pages.", "STOP")
                        break
                    log(f"No new tweets this page ({consecutive_dup_pages}/{max_dup_pages}). Trying next...", "INFO")
                else:
                    consecutive_dup_pages = 0 # reset on success

                if total_processed < max_raw:
                    await asyncio.sleep(1)
                    tweets = await tweets.next()
            
            # Finished successfully or reached end of data
            ScraperState.set_busy(client, False)
            break

        except Exception as e:
            ScraperState.set_busy(client, False)
            error_msg = str(e)
            
            if '429' in error_msg:
                log(f"Account {curr_idx+1} reached rate limit. Swapping...", "LIMIT")
                ScraperState.mark_limited(client)
            else:
                log(f"Account {curr_idx+1} error: {e}", "ERROR")
                # We also mark it as briefly limited to avoid immediate reuse if it's a connection/account issue
                ScraperState.rate_limits[id(client)] = datetime.now() + timedelta(minutes=2)
            
            # Switch to next account context
            curr_idx = (curr_idx + 1) % len(clients)
            
            # Safety: if we have already tried all accounts in this loop without any progress, stop.
            if wait_level > len(clients): 
                log(f"Critical error: All available accounts failed for '{query}'. Skipping task.", "FATAL")
                break
                
            wait_level += 1 # repurposed as an error counter for this loop
            await asyncio.sleep(2)
            continue

    return results, total_processed

# -----------------------------------------------------------------------------
# HANDLERS
# -----------------------------------------------------------------------------

async def run_search(clients, is_trending=False):
    query = ""
    if is_trending:
        trends = await clients[0].get_trends('trending')
        for i, t in enumerate(trends[:15], 1): print(f"{i}. {t.name}")
        sel = get_input("Select trend #", "b")
        if sel == 'b' or not sel.isdigit(): return
        query = trends[int(sel)-1].name
    else:
        query = get_input("Enter search query")
        if not query: return

    s, e = get_input("Start (YYYY-MM-DD)", ""), get_input("End (YYYY-MM-DD)", "")
    mx = get_input("Max RAW tweets", 50, int)
    max_dup = get_input("Max consecutive duplicate pages to follow", 3, int)
    out = get_input("Filename", "scraped_tweets")

    data, ids = load_data(out)
    new, raw = await scrape_twitter_search(clients, 0, query, s, e, mx, ids, max_dup)
    if new: process_and_save(data + new, out)

async def run_interval(clients):
    query = get_input("Enter search query")
    if not query: return
    s_dt = datetime.strptime(get_input("Start (YYYY-MM-DD HH:MM:SS)"), "%Y-%m-%d %H:%M:%S")
    e_dt = datetime.strptime(get_input("End (YYYY-MM-DD HH:MM:SS)"), "%Y-%m-%d %H:%M:%S")
    h, j_m = get_input("Interval hours", 2.0, float), get_input("Jitter minutes", 30, int)
    mx = get_input("Max RAW per interval", 20, int)
    max_dup = get_input("Max consecutive duplicate pages to follow", 1, int)
    out = get_input("Filename", "interval_tweets")

    data, ids = load_data(out)
    intervals = []
    curr = s_dt
    while curr < e_dt:
        dur = timedelta(hours=h) + timedelta(minutes=random.randint(-j_m, j_m))
        nxt = min(curr + max(timedelta(minutes=10), dur), e_dt)
        intervals.append((curr, nxt))
        curr = nxt + timedelta(seconds=1)

    for i in range(0, len(intervals), len(clients)):
        batch = intervals[i:i+len(clients)]
        async def task(it, idx):
            q_time = f"{query} since_time:{int(it[0].timestamp())} until_time:{int(it[1].timestamp())}"
            log(f"Interval {it[0].strftime('%H:%M')} - {it[1].strftime('%H:%M')}", "TASK")
            return await scrape_twitter_search(clients, idx % len(clients), q_time, max_raw=mx, known_ids=ids, max_dup_pages=max_dup)
        
        results = await asyncio.gather(*(task(it, j) for j, it in enumerate(batch)), return_exceptions=True)
        for res in results:
            if not isinstance(res, Exception) and res[0]:
                data.extend(res[0])
                for p in res[0]: ids.add(str(p['tweet_id']))
        process_and_save(data, out)
        if i + len(clients) < len(intervals): await asyncio.sleep(2)

async def run_continuous(clients):
    queries = [q.strip() for q in get_input("Queries (comma-separated)").split(',') if q.strip()]
    target = get_input("Target RAW per query", 500, int)
    wait_m, j_m = get_input("Wait minutes", 30.0, float), get_input("Jitter minutes", 5.0, float)
    mx = get_input("Max RAW per run", 50, int)
    max_dup = get_input("Max consecutive duplicate pages to follow", 1, int)
    out = get_input("Filename", "continuous_tweets")

    data, ids = load_data(out)
    prog = {q: sum(1 for r in data if r.get('keyword') == q) for q in queries}
    log(f"Starting Continuous Mode. Target: {target}/query.", "START")

    try:
        while any(v < target for v in prog.values()):
            pending = [q for q in queries if prog[q] < target]
            for i in range(0, len(pending), len(clients)):
                batch = pending[i:i+len(clients)]
                async def task(q, idx):
                    return await scrape_twitter_search(clients, idx % len(clients), q, max_raw=min(mx, target-prog[q]), known_ids=ids, max_dup_pages=max_dup)
                
                results = await asyncio.gather(*(task(q, j) for j, q in enumerate(batch)), return_exceptions=True)
                for j, res in enumerate(results):
                    q = batch[j]
                    if not isinstance(res, Exception):
                        prog[q] += res[1]
                        if res[0]:
                            data.extend(res[0])
                            for p in res[0]: ids.add(str(p['tweet_id']))
                process_and_save(data, out)
            
            slp = max(0.5, wait_m + random.uniform(-j_m, j_m))
            log(f"Sweep complete. Next in {slp:.2f}m...", "WAIT")
            await asyncio.sleep(int(slp * 60))
    except KeyboardInterrupt: log("Stopped.", "INFO")

# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------

async def main():
    path = os.path.dirname(os.path.abspath(__file__))
    f_cookies = sorted(glob.glob(os.path.join(path, 'twitter_cookies*.json')))
    clients = []
    
    for f in f_cookies:
        c = Client('en-US')
        if await authenticate(c, f): clients.append(c)
    
    while not clients or input(f"Loaded {len(clients)} counts. Add? (y/n): ").lower() == 'y':
        idx = 1
        while os.path.exists(os.path.join(path, f'twitter_cookies_{idx}.json')): idx += 1
        f = os.path.join(path, f'twitter_cookies_{idx if idx > 1 else ""}.json')
        if idx == 1: f = os.path.join(path, 'twitter_cookies.json')
        c = Client('en-US')
        if await authenticate(c, f): clients.append(c)
        else: break

    MENU = {
        "1": ("Search", lambda: run_search(clients)),
        "2": ("Trends", lambda: run_search(clients, True)),
        "3": ("Intervals", lambda: run_interval(clients)),
        "4": ("Continuous", lambda: run_continuous(clients)),
        "0": ("Quit", None)
    }

    while True:
        print("\n=== TWITTER SCRAPER v2.0 ===")
        for k, v in MENU.items(): print(f"{k}. {v[0]}")
        ch = input("\nSelect: ").strip()
        if ch == '0': break
        if ch in MENU: await MENU[ch][1]()

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: print("\nExit.")