import asyncio
import csv
import json
import os
import glob
import random
import re
import signal
import logging
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import (
    List, Dict, Set, Optional, Tuple, Any, TypedDict, Final, Union, Callable, ClassVar
)
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
        key_byte_indices = [item.group(2) for item in indices_match]
        if not key_byte_indices: raise Exception("Couldn't get KEY_BYTE indices")
        return int(key_byte_indices[0]), list(map(int, key_byte_indices[1:]))

    _tx_mod.ClientTransaction.get_indices = _patched_get_indices
except Exception as e: print(f"Warning: Twikit monkey patch failed: {e}")

# =============================================================================
# REGION: CORE CONFIGURATION
# =============================================================================

# ANSI Styling Constants
C_RESET: Final[str] = "\033[0m"
C_BOLD: Final[str] = "\033[1m"
C_RED: Final[str] = "\033[0;31m"
C_GREEN: Final[str] = "\033[0;32m"
C_YELLOW: Final[str] = "\033[0;33m"
C_BLUE: Final[str] = "\033[0;34m"
C_CYAN: Final[str] = "\033[0;36m"
C_MAGENTA: Final[str] = "\033[0;35m"

@dataclass(frozen=True)
class AppConfig:
    """Central configuration for the Twitter Scraper ecosystem."""
    FIELDNAMES: ClassVar[List[str]] = [
        "keyword", "tweet_id", "username", "handle", "text", "sentiment", 
        "url", "datetime", "likes", "retweets", "replies", "tweets_per_date"
    ]
    COOLDOWN_TIERS: Final[List[int]] = field(default_factory=lambda: [60, 300, 1800, 3600]) # 1m, 5m, 30m, 1h
    RATE_LIMIT_DELAY: Final[int] = 900 # 15m
    PAGINATION_SLEEP: Final[float] = 1.6
    DASHBOARD_WIDTH: Final[int] = 68

# =============================================================================
# REGION: UI & LOGGING FRAMEWORK
# =============================================================================

class DashboardLogger(logging.Formatter):
    """Custom color-coded formatter for the Interactive Dashboard."""
    def format(self, record):
        cat = record.levelname
        colors = {
            "INFO": C_CYAN, "SUCCESS": C_GREEN, "LIMIT": C_YELLOW + C_BOLD, 
            "ERROR": C_RED, "FATAL": C_RED + C_BOLD, "AUTH": C_MAGENTA,
            "TASK": C_BLUE + C_BOLD, "FILE": C_BLUE, "WAIT": C_YELLOW
        }
        color = colors.get(cat, C_RESET)
        return f" {color}{C_BOLD}{cat:<8}{C_RESET} │ {record.getMessage()}"

# Setup Custom Logging levels
logging.addLevelName(25, "SUCCESS")
logging.addLevelName(35, "LIMIT")
logging.addLevelName(15, "AUTH")
logging.addLevelName(16, "TASK")
logging.addLevelName(17, "FILE")
logging.addLevelName(18, "WAIT")

logger = logging.getLogger("TwitterScraper")
logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(DashboardLogger())
logger.addHandler(sh)

def log(msg: str, cat: str = "INFO"):
    mappings = {"INFO": 20, "SUCCESS": 25, "LIMIT": 35, "ERROR": 40, "FATAL": 50, "AUTH": 15, "TASK": 16, "FILE": 17, "WAIT": 18}
    logger.log(mappings.get(cat, 20), msg)

def print_header(title: str):
    """Visual framed header for the dashboard modules."""
    w = AppConfig.DASHBOARD_WIDTH
    print(f"\n{C_BLUE}{'═'*w}{C_RESET}\n{C_BOLD}{C_CYAN}  {title:^{w-4}}  {C_RESET}\n{C_BLUE}{'═'*w}{C_RESET}")

def get_input(prompt: str, default: Any = None, type_func: Callable = str) -> Any:
    """Interactively gathers user input with validation and defaults."""
    p = f"{C_BOLD}{C_CYAN}➤ {prompt}{C_RESET}" + (f" {C_YELLOW}({default}){C_RESET}: " if default is not None else ": ")
    val = input(p).strip()
    if not val: return default
    try: return type_func(val)
    except: return default

# =============================================================================
# REGION: DATA PROCESSING LAYER
# =============================================================================

class DataEngine:
    """Handles high-performance CSV operations and sentiment algorithms."""
    
    @staticmethod
    def _path(p: str) -> str:
        return p if p.lower().endswith('.csv') else p + '.csv'

    @staticmethod
    def analyze_sentiment(text: str) -> str:
        """Returns a human-readable sentiment label for a given text."""
        if not text: return "Neutral"
        try:
            pol = TextBlob(text).sentiment.polarity
            if pol > 0.1: return "Positive"
            if pol < -0.1: return "Negative"
            return "Neutral"
        except: return "Neutral"

    @classmethod
    def sync_to_disk(cls, data: List[Dict], path: str):
        """Standardizes, counts, and saves a dataset to CSV."""
        if not data: return
        path = cls._path(path)
        
        # Calculate frequencies and normalize datetimes
        date_map = Counter()
        for row in data:
            dt_raw = str(row.get('datetime', ''))
            for fmt in ('%a %b %d %H:%M:%S %z %Y', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
                try:
                    obj = datetime.strptime(dt_raw, fmt)
                    row['datetime'] = obj.strftime('%Y-%m-%d %H:%M:%S')
                    row['_date_key'] = obj.strftime('%Y-%m-%d')
                    break
                except: continue
            if '_date_key' not in row: row['_date_key'] = dt_raw[:10]
            date_map[row['_date_key']] += 1
            
        for row in data:
            row['tweets_per_date'] = date_map.get(row.pop('_date_key', ''), 0)

        try:
            with open(path, 'w', newline='', encoding='utf-8') as fs:
                wr = csv.DictWriter(fs, fieldnames=AppConfig.FIELDNAMES, extrasaction='ignore')
                wr.writeheader()
                wr.writerows(data)
            log(f"Successfully synced {len(data)} records to '{os.path.basename(path)}'", "FILE")
        except Exception as e: log(f"Sync Failure: {e}", "ERROR")

    @classmethod
    def extract_ids(cls, path: str) -> Set[str]:
        """Loads only tweet IDs into a set for high-speed deduplication."""
        path = cls._path(path)
        results = set()
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as fs:
                    for row in csv.DictReader(fs):
                        if 'tweet_id' in row: results.add(str(row['tweet_id']))
            except: pass
        return results

    @classmethod
    def load_full(cls, path: str) -> List[Dict]:
        """Loads full records from disk, or returns an empty list if missing."""
        path = cls._path(path)
        if not os.path.exists(path): return []
        try:
            with open(path, 'r', encoding='utf-8') as fs: return list(csv.DictReader(fs))
        except: return []

# =============================================================================
# REGION: ACCOUNT & WORKER POOL
# =============================================================================

class TwitterAccount:
    """Manages an individual X account, its health, and its async lifecycle."""
    __slots__ = ('idx', 'cookies_file', 'client', 'fails', 'resume_until', 'is_busy')

    def __init__(self, idx: int, file: str):
        self.idx = idx + 1
        self.cookies_file = file
        self.client = Client('en-US')
        self.fails = 0
        self.resume_until: Optional[datetime] = None
        self.is_busy = False

    async def __aenter__(self):
        self.is_busy = True; return self

    async def __aexit__(self, *exc):
        self.is_busy = False

    async def auth(self) -> bool:
        """Authenticates using user-provided credentials or saved cookies."""
        if os.path.exists(self.cookies_file):
            log(f"Acct {self.idx}: Attempting cookie-based login...", "AUTH")
            try:
                self.client.load_cookies(self.cookies_file)
                return True
            except: pass

        print("\n" + "-" * AppConfig.DASHBOARD_WIDTH)
        print(f"{C_BOLD}{C_CYAN}ACTION REQUIRED: Twitter Authentication for Acct {self.idx}{C_RESET}")
        print("Please enter your X credentials (saved as session cookies).")
        print("-" * AppConfig.DASHBOARD_WIDTH)
        
        try:
            u, e, p = input("  ? Username: "), input("  ? Email: "), input("  ? Password: ")
            log("Communicating with X server...", "AUTH")
            await self.client.login(auth_info_1=u, auth_info_2=e, password=p)
            self.client.save_cookies(self.cookies_file)
            log("Authentication Successful!", "AUTH")
            return True
        except Exception as err:
            log(f"Login failed: {err}", "ERROR")
            if "403" in str(err): log("Cloudflare detected. Manual cookies mandatory.", "FATAL")
            
            print("\n  " + C_BOLD + "HOW TO GET MANUAL COOKIES:" + C_RESET)
            print("  Login to Twitter.com -> DevTools (F12) -> Application -> Cookies")
            at = input("  ? Enter auth_token: ").strip()
            ct = input("  ? Enter ct0: ").strip()
            if at and ct:
                with open(self.cookies_file, 'w') as fs: json.dump({'auth_token': at, 'ct0': ct}, fs)
                self.client.load_cookies(self.cookies_file)
                log("Cookies applied successfully.", "AUTH")
                return True
        return False

    def trigger_cooldown(self, is_429: bool = False):
        """Implements a tiered escalation cooldown for rate limits and errors."""
        self.fails += 1
        if is_429:
            sec = 900 if self.fails == 1 else (1800 if self.fails == 2 else 3600)
            reason = "Rate Limit"
        else:
            sec = AppConfig.COOLDOWN_TIERS[min(self.fails-1, len(AppConfig.COOLDOWN_TIERS)-1)]
            reason = "Scrape Error"
        
        self.resume_until = datetime.now() + timedelta(seconds=sec)
        log(f"Acct {self.idx} ({reason}): Cooldown {sec//60}m. Ready at {self.resume_until.strftime('%H:%M:%S')}", "LIMIT")

    def available(self) -> bool:
        """Returns True if the account is ready for work."""
        return not self.is_busy and (not self.resume_until or self.resume_until < datetime.now())

class WorkerPool:
    """Manages a collection of Accounts to distribute scraping workload."""
    def __init__(self, accs: List[TwitterAccount]): self.accs = accs
    
    def lease_best(self, start_idx: int = 0) -> Tuple[Optional[TwitterAccount], int]:
        """Finds and leases the next available account from the pool."""
        total = len(self.accs)
        for i in range(total):
            idx = (start_idx + i) % total
            acc = self.accs[idx]
            if acc.available(): return acc, idx
        return None, -1

    async def stall_for_health(self):
        """Pauses execution until at least one account recovers from cooldown."""
        now = datetime.now()
        waits = [int((a.resume_until - now).total_seconds()) for a in self.accs if a.resume_until and a.resume_until > now]
        if waits:
            d = min(waits) + 2
            log(f"Exhausted healthy accounts. Stall initiated: {d} seconds...", "WAIT")
            await asyncio.sleep(d)

# =============================================================================
# REGION: SCRAPING LOGIC UNIT
# =============================================================================

@dataclass
class ScrapeTask:
    """Blueprint for a single scraping execution task."""
    __slots__ = ('query', 'limit', 'ids', 'since', 'until', 'max_dup')
    query: str; limit: int; ids: Set[str]
    since: Optional[str]; until: Optional[str]; max_dup: int

class ScrapingEngine:
    """Robust processor for paginated Twitter search queries."""
    
    @classmethod
    async def process(cls, pool: WorkerPool, pref_idx: int, t: ScrapeTask) -> Tuple[List[Dict], int]:
        """Executes a search task with automatic rotation and state management."""
        extracted, n, consecutive_dups, rotation_fails = [], 0, 0, 0
        q_final = f"{t.query}{' since:'+t.since if t.since else ''}{' until:'+t.until if t.until else ''}"
        
        curr_idx = pref_idx
        while n < t.limit:
            acc, active_idx = pool.lease_best(curr_idx); curr_idx = active_idx
            if not acc: 
                await pool.stall_for_health(); continue

            async with acc:
                log(f"Acct {acc.idx} ➔ Analyzing: '{t.query}'", "INFO")
                try:
                    try: tws = await acc.client.search_tweet(q_final, 'Latest')
                    except Exception as e:
                        if '404' in str(e): tws = await acc.client.search_tweet(q_final, 'Top')
                        else: raise e

                    while len(extracted) < t.limit and tws:
                        found_fresh = False
                        for tweet in tws:
                            t_id = str(tweet.id)
                            if t_id in t.ids:
                                log(f"Skip: @{tweet.user.screen_name:<16} │ Duplicate", "FILE")
                                continue
                            
                            found_fresh = True; t.ids.add(t_id)
                            n += 1 # Only count unique/new tweets
                            if len(extracted) >= t.limit: break
                            msg = tweet.text.replace('\n', ' ')
                            extracted.append({
                                "keyword": t.query, "tweet_id": tweet.id, "username": tweet.user.name, "handle": tweet.user.screen_name,
                                "text": msg, "sentiment": DataEngine.analyze_sentiment(msg), "url": f"https://x.com/status/{tweet.id}",
                                "datetime": tweet.created_at, "likes": tweet.favorite_count, "retweets": tweet.retweet_count, "replies": tweet.reply_count
                            })
                            log(f"+ Collected: @{tweet.user.screen_name:<15} │ Progress: {n}/{t.limit} │ New: {len(extracted)}", "SUCCESS")

                        if not found_fresh:
                            consecutive_dups += 1
                            if consecutive_dups >= t.max_dup: 
                                log(f"Search Saturation: {consecutive_dups} duplicate pages. Stopping task.", "WAIT")
                                break
                        else:
                            consecutive_dups = 0; acc.fails = 0 # Reset health on success
                        
                        if n < t.limit:
                            await asyncio.sleep(AppConfig.PAGINATION_SLEEP)
                            tws = await tws.next()
                    break
                except Exception as ex:
                    acc.trigger_cooldown(is_429=('429' in str(ex)))
                    log(f"Acct {acc.idx} Scrape Failure: {ex}", "ERROR")
                    curr_idx = (curr_idx + 1) % len(pool.accs)
                    rotation_fails += 1
                    if rotation_fails >= len(pool.accs) * 2:
                        log("All accounts in pool reported critical failure. Aborting task.", "FATAL")
                        break
                    continue

        return extracted, n

# =============================================================================
# REGION: DASHBOARD APPLICATION
# =============================================================================

class AnalyticaDashboard:
    """High-level controller for dashboard interactions and scrape orchestration."""
    
    def __init__(self, pool: WorkerPool):
        self.pool = pool
        self.is_running = True
        signal.signal(signal.SIGINT, self.graceful_shutdown)

    def graceful_shutdown(self, *args):
        """Ensures all data is flushed to disk before closing on SIGINT."""
        self.is_running = False
        print(f"\n{C_YELLOW}{C_BOLD}Shutdown pulse detected. Finalizing sync and closing console...{C_RESET}")

    async def custom_search(self, trends: bool = False):
        """Module: Targeted search with date and volume tuning."""
        print_header("REAL-TIME TREND DISCOVERY" if trends else "CUSTOM SEARCH MODULE")
        q = ""
        if trends:
            results = await self.pool.accs[0].client.get_trends('trending')
            for i, item in enumerate(results[:15], 1): print(f"  {i}. {item.name}")
            sel = get_input("Select Trend #", "b")
            if sel == 'b' or not str(sel).isdigit(): return
            q = results[int(sel)-1].name
        else:
            q = get_input("Query String")
            if not q: return

        s, e = get_input("Since (YYYY-MM-DD)"), get_input("Until (YYYY-MM-DD)")
        mx = get_input("Max Tweets to Collect", 50, int)
        dup = get_input("Max Page Retries (if only duplicates)", 2, int)
        f_name = get_input("Filename", "search_results")

        known_ids = DataEngine.extract_ids(f_name)
        log(f"Pre-scan: Loaded {len(known_ids)} known IDs for deduplication.", "FILE")
        
        new, _ = await ScrapingEngine.process(self.pool, 0, ScrapeTask(q, mx, known_ids, s, e, dup))
        if new:
            log(f"Merge: Integrating {len(new)} records into existing archive...", "TASK")
            DataEngine.sync_to_disk(DataEngine.load_full(f_name) + new, f_name)
        else:
            log("Process closed: No unique data discovered.", "INFO")

    async def historical_interval(self):
        """Module: Time-chunked historical reconstruction."""
        print_header("HISTORICAL TIMELINE RECONSTRUCTION")
        q = get_input("Keyword"); s_raw = get_input("Start (YYYY-MM-DD HH:MM:SS)"); e_raw = get_input("End (YYYY-MM-DD HH:MM:SS)")
        if not all([q, s_raw, e_raw]): return
        s_dt, e_dt = datetime.strptime(s_raw, "%Y-%m-%d %H:%M:%S"), datetime.strptime(e_raw, "%Y-%m-%d %H:%M:%S")
        
        hrs, jit = get_input("Chunk Size (Hrs)", 2.0, float), get_input("Chunk Jitter (Min)", 20, int)
        mx, dup = get_input("Max/Chunk", 25, int), get_input("Max Page Retries", 1, int)
        f_name = get_input("Filename", "history_archive")

        ids, data = DataEngine.extract_ids(f_name), DataEngine.load_full(f_name)
        log(f"Resuming: Loaded {len(data)} records for '{q}'.", "FILE")
        
        timeline, cursor = [], s_dt
        while cursor < e_dt:
            delta = timedelta(hours=hrs) + timedelta(minutes=random.randint(-jit, jit))
            end_t = min(cursor + max(timedelta(minutes=10), delta), e_dt)
            timeline.append((cursor, end_t)); cursor = end_t + timedelta(seconds=1)

        log(f"Planner: {len(timeline)} time-chunks scheduled for processing.", "TASK")
        for i in range(0, len(timeline), len(self.pool.accs)):
            if not self.is_running: break
            tasks = timeline[i : i + len(self.pool.accs)]
            
            async def chunk_runner(its, off):
                t_q = f"{q} since_time:{int(its[0].timestamp())} until_time:{int(its[1].timestamp())}"
                log(f"Running Task: {its[0].strftime('%H:%M')} ➔ {its[1].strftime('%H:%M')}", "TASK")
                return await ScrapingEngine.process(self.pool, off, ScrapeTask(t_q, mx, ids, None, None, dup))

            results = await asyncio.gather(*(chunk_runner(it, j) for j, it in enumerate(tasks)), return_exceptions=True)
            for res in results:
                if not isinstance(res, Exception) and res[0]: data.extend(res[0])
            DataEngine.sync_to_disk(data, f_name)
            if i + len(self.pool.accs) < len(timeline): await asyncio.sleep(2)

    async def continuous_poll(self):
        """Module: Persistent keyword infrastructure monitoring."""
        print_header("REAL-TIME CONTINUOUS POLLING")
        q_list = [x.strip() for x in get_input("Keywords (comma-sep)").split(',') if x.strip()]
        goal, wait = get_input("Goal/Query", 500, int), get_input("Sweep Interval (min)", 20.0, float)
        f_name = get_input("Filename", "polling_live")

        data, ids = DataEngine.load_full(f_name), DataEngine.extract_ids(f_name)
        stats = {q: sum(1 for r in data if r.get('keyword') == q) for q in q_list}

        try:
            while self.is_running and any(v < goal for v in stats.values()):
                worklist = [q for q in q_list if stats[q] < goal]
                for i in range(0, len(worklist), len(self.pool.accs)):
                    chunk = worklist[i : i + len(self.pool.accs)]
                    results = await asyncio.gather(*(ScrapingEngine.process(self.pool, j, 
                        ScrapeTask(q, mx_swp, ids, None, None, dup)) for j, q in enumerate(chunk)))
                    
                    for k, res in enumerate(results):
                        stats[chunk[k]] += res[1]; data.extend(res[0])
                    DataEngine.sync_to_disk(data, f_name)
                
                log(f"Sequence complete. Next pulse in {wait}m...", "WAIT")
                await asyncio.sleep(int(wait * 60))
        except KeyboardInterrupt: pass

    async def add_new_account(self):
        """Module: On-demand account pool expansion."""
        print_header("ACCOUNT REGISTRATION")
        root = os.path.dirname(os.path.abspath(__file__))
        idx = len(self.pool.accs) + 1
        while any(os.path.basename(a.cookies_file) == f"twitter_cookies_{idx}.json" for a in self.pool.accs): idx += 1
        name = os.path.join(root, f"twitter_cookies_{idx if idx > 1 else ''}.json")
        if idx == 1: name = os.path.join(root, "twitter_cookies.json")
        
        acc = TwitterAccount(len(self.pool.accs), name)
        if await acc.auth(): self.pool.accs.append(acc); log(f"Acct {acc.idx} integrated.", "AUTH")

# =============================================================================
# REGION: ENTRY POINT
# =============================================================================

async def main():
    root = os.path.dirname(os.path.abspath(__file__))
    files = sorted(glob.glob(os.path.join(root, 'twitter_cookies*.json')))
    accounts = []
    
    for i, f in enumerate(files):
        acc = TwitterAccount(i, f)
        if await acc.auth(): accounts.append(acc)
    
    dash = AnalyticaDashboard(WorkerPool(accounts))
    MENU = {
        "1": ("Custom Search", "Targeted query with specific date filters.", dash.custom_search),
        "2": ("Trends Pick", "Discover top trends and start scraping.", lambda: dash.custom_search(trends=True)),
        "3": ("Historical Int", "Deep history reconstruction via time-chunks.", dash.historical_interval),
        "4": ("Continuous Poll", "Sustained keyword infrastructure monitoring.", dash.continuous_poll),
        "5": ("Link Account", "Authenticate a fresh Twitter identity.", dash.add_new_account),
        "0": ("Exit Console", "Safely power down all scraping operations.", None)
    }

    while dash.is_running:
        print(f"\n{C_BOLD}{C_CYAN}    TWITTER ANALYTICA DASHBOARD v1.0{C_RESET}")
        print(f"{C_BLUE}{'─'*AppConfig.DASHBOARD_WIDTH}{C_RESET}")
        for k, (n, d, _) in MENU.items():
            print(f"  {C_YELLOW}[{k}]{C_RESET} {C_BOLD}{n:<18}{C_RESET} {C_CYAN}➔{C_RESET} {d}")
        print(f"{C_BLUE}{'─'*AppConfig.DASHBOARD_WIDTH}{C_RESET}")
        
        ch = get_input("SELECT ACTION")
        if ch == '0' or str(ch).lower() == 'q': break
        if ch in MENU: await MENU[ch][2]()

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass
    except Exception as e: log(f"System halt: {e}", "FATAL")