import re
import os
import sys
import glob
import json
import time
import signal
import logging
import inspect
import asyncio
import argparse
import multiprocessing
from functools import partial
from collections import Counter
from dataclasses import dataclass
from typing import List, Dict, Optional, Any, Callable, Final, ClassVar

import pandas as pd
from tqdm import tqdm
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory

# =============================================================================
# REGION: CONFIGURATION LOADERS
# =============================================================================

def load_json_config(f_name, is_set=False):
    """Loads a JSON config file relative to this script's directory."""
    # Resolve path relative to this script so it works from any CWD
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = f_name if os.path.isabs(f_name) else os.path.join(base_dir, f_name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Critical configuration file '{path}' is missing.")
    try:
        with open(path, 'r') as f:
            data = json.load(f)
            return set(data) if is_set else data
    except Exception as e:
        print(f"[!] Error loading {path}: {e}")
        return set() if is_set else {}

def load_slang_dict():
    return load_json_config('slang_dict.json')

SLANG_DICT           = load_slang_dict()
KEY_ENTITIES         = load_json_config('preserve.json',  is_set=True)
ADDITIONAL_STOPWORDS = load_json_config('stopwords.json', is_set=True)

# =============================================================================
# REGION: CORE ENGINE
# =============================================================================

worker_cleaner = None

class TweetCleaner:
    def __init__(self, use_stemming=True):
        self.factory         = StemmerFactory()
        self.stemmer         = self.factory.create_stemmer() if use_stemming else None
        self.stopword_factory  = StopWordRemoverFactory()
        self.stopword_remover  = self.stopword_factory.create_stop_word_remover()
        self.stem_cache      = {}
        self.stats           = Counter()

    def clean_text(self, text, slang_dict):
        if not isinstance(text, str): return ""
        text = text.lower()
        text = re.sub(r'https?://\S+|www\.\S+', '', text)
        text = re.sub(r'@\w+', '', text)
        text = re.sub(r'#\w+', '', text)
        text = re.sub(r'^rt\s+', '', text)
        text = re.sub(r'[^a-zA-Z\s]', ' ', text)
        text = re.sub(r'(\w)\1{2,}', r'\1', text)

        tokens     = text.split()
        normalized = [slang_dict.get(w, w) for w in tokens]
        tokens     = [w for w in normalized if w not in ADDITIONAL_STOPWORDS]
        self.stats['stopwords_removed'] += (len(normalized) - len(tokens))

        cleaned_text  = " ".join(tokens)
        tokens_before = cleaned_text.split()
        cleaned_text  = self.stopword_remover.remove(cleaned_text)
        tokens_after  = cleaned_text.split()

        final_list = [w for w in tokens_before if w in tokens_after or w in KEY_ENTITIES]
        cleaned_text = " ".join(final_list)

        if self.stemmer:
            stemmed = []
            for w in cleaned_text.split():
                if w not in self.stem_cache:
                    self.stem_cache[w] = self.stemmer.stem(w)
                stemmed.append(self.stem_cache[w])
            cleaned_text = " ".join(stemmed)

        final = [w for w in cleaned_text.split() if (len(w) > 2 or w in ['as', 'us', 'ri'])]
        return " ".join(final)


def _init_worker(use_stemming):
    global worker_cleaner
    worker_cleaner = TweetCleaner(use_stemming=use_stemming)

def _process_chunk_optimized(chunk_data, slang_dict):
    global worker_cleaner
    cleaned = chunk_data.apply(lambda x: worker_cleaner.clean_text(x, slang_dict))
    return cleaned, worker_cleaner.stats


def run_cleaning_pipeline(input_path, output_path, column='text', use_stemming=True, cores=4):
    """
    Core cleaning pipeline. Importable from any external module.
    Returns a statistics dictionary, or None on failure.

    Pipeline stages (in order):
      1. Load dataset (CSV / JSON / Excel)
      2. Deduplicate by tweet_id then by raw text
      3. Filter bot accounts (grok, chatgpt, bot)
      4. Parallel NLP cleaning (slang norm → stopword removal → stemming)
      5. Drop empty post-clean rows
      6. Write output + word_frequencies.csv
    """
    try:
        if input_path.endswith('.csv'):
            df = pd.read_csv(input_path)
        elif input_path.endswith('.json'):
            df = pd.read_json(input_path)
        else:
            df = pd.read_excel(input_path)
    except Exception as e:
        print(f"[!] Error loading input: {e}")
        return None

    total_initial = len(df)

    # --- Stage 1: Deduplication ---
    if 'tweet_id' in df.columns:
        df = df.drop_duplicates(subset=['tweet_id'])
    df = df.drop_duplicates(subset=[column])
    duplicates_removed = total_initial - len(df)

    # --- Stage 2: Bot Filtering ---
    pre_bot_count = len(df)
    if 'handle' in df.columns:
        df = df[~df['handle'].astype(str).str.lower().isin({'grok', 'chatgpt', 'bot'})]
    total_after_filters = len(df)
    bots_removed = pre_bot_count - total_after_filters

    # --- Stage 3: Parallel NLP Cleaning ---
    num_cores  = min(cores, multiprocessing.cpu_count())
    print(f"[*] Starting {num_cores} workers. Please wait...")

    chunk_size = max(1, total_after_filters // (num_cores * 20))
    chunks     = [df[column][i:i + chunk_size] for i in range(0, total_after_filters, chunk_size)]

    start_time = time.time()
    with multiprocessing.Pool(processes=num_cores, initializer=_init_worker, initargs=(use_stemming,)) as pool:
        init_end = time.time()
        print(f"[*] Workers ready in {init_end - start_time:.2f}s. Processing {total_after_filters} tweets...")

        proc_start = time.time()
        func = partial(_process_chunk_optimized, slang_dict=SLANG_DICT)

        results = []
        for res in tqdm(pool.imap(func, chunks), total=len(chunks), desc="Cleaning Progress"):
            results.append(res)
        proc_end = time.time()

    df['cleaned_text'] = pd.concat([res[0] for res in results])
    total_stats = Counter()
    for res in results:
        total_stats.update(res[1])

    # --- Stage 4: Drop Empty Rows ---
    df          = df[df['cleaned_text'].str.strip() != ""]
    final_total = len(df)
    empty_removed = total_after_filters - final_total

    # --- Stage 5: Write Output ---
    if output_path.endswith('.json'):
        df.to_json(output_path, orient='records', indent=4)
    else:
        df.to_csv(output_path, index=False)

    all_words   = " ".join(df['cleaned_text'].astype(str)).split()
    word_counts = Counter(all_words)
    pd.DataFrame(word_counts.most_common(), columns=['word', 'count']).to_csv(
        "word_frequencies.csv", index=False
    )

    return {
        'total_initial':    total_initial,
        'duplicates_removed': duplicates_removed,
        'bots_removed':     bots_removed,
        'empty_removed':    empty_removed,
        'final_total':      final_total,
        'startup_time':     init_end - start_time,
        'processing_time':  proc_end - proc_start,
        'unique_vocab':     len(word_counts),
        'total_deleted':    total_initial - final_total,
    }

# =============================================================================
# REGION: THEME & UI CONSTANTS  (formerly cleaner_dashboard.py)
# =============================================================================

class Theme:
    """Centralized ANSI styling constants."""
    RESET:   Final[str] = "\033[0m"
    BOLD:    Final[str] = "\033[1m"
    RED:     Final[str] = "\033[0;31m"
    GREEN:   Final[str] = "\033[0;32m"
    YELLOW:  Final[str] = "\033[0;33m"
    BLUE:    Final[str] = "\033[0;34m"
    CYAN:    Final[str] = "\033[0;36m"
    MAGENTA: Final[str] = "\033[0;35m"

@dataclass(frozen=True)
class AppConfig:
    """Dashboard configuration."""
    DASHBOARD_WIDTH: ClassVar[int] = 76
    DEFAULT_CORES:   ClassVar[int] = 4
    DEFAULT_COLUMN:  ClassVar[str] = "text"

# =============================================================================
# REGION: APP STATE & SIGNAL HANDLING
# =============================================================================

class AppState:
    STOP_REQUESTED = False

def _interrupt_handler(signum, frame):
    if AppState.STOP_REQUESTED:
        print("\n\033[0;31m[FATAL]\033[0m Forced Exit.")
        os._exit(1)
    print("\n\033[0;33m[WAIT]\033[0m Interrupt detected! Returning to menu... (Press Ctrl+C again to force exit)")
    AppState.STOP_REQUESTED = True

signal.signal(signal.SIGINT, _interrupt_handler)

# =============================================================================
# REGION: LOGGING FRAMEWORK
# =============================================================================

class DashboardLogger(logging.Formatter):
    """Custom color-coded formatter."""
    def format(self, record):
        cat = record.levelname
        colors = {
            "INFO":    Theme.CYAN,
            "SUCCESS": Theme.GREEN,
            "LIMIT":   Theme.YELLOW + Theme.BOLD,
            "ERROR":   Theme.RED,
            "FATAL":   Theme.RED + Theme.BOLD,
            "AUTH":    Theme.MAGENTA,
            "TASK":    Theme.BLUE + Theme.BOLD,
            "FILE":    Theme.BLUE,
            "WAIT":    Theme.YELLOW,
        }
        color = colors.get(cat, Theme.RESET)
        return f" {color}{Theme.BOLD}{cat:<8}{Theme.RESET} │ {record.getMessage()}"

for _lvl, _name in [(25, "SUCCESS"), (35, "LIMIT"), (15, "AUTH"), (16, "TASK"), (17, "FILE"), (18, "WAIT")]:
    logging.addLevelName(_lvl, _name)

logger = logging.getLogger("CleanerDashboard")
logger.setLevel(logging.DEBUG)
_sh = logging.StreamHandler()
_sh.setFormatter(DashboardLogger())
logger.addHandler(_sh)

def log(msg: str, cat: str = "INFO"):
    _mappings = {"INFO": 20, "SUCCESS": 25, "LIMIT": 35, "ERROR": 40,
                 "FATAL": 50, "AUTH": 15, "TASK": 16, "FILE": 17, "WAIT": 18}
    logger.log(_mappings.get(cat, 20), msg)

def print_header(title: str):
    w = AppConfig.DASHBOARD_WIDTH
    print(f"\n{Theme.BLUE}{'═'*w}{Theme.RESET}\n{Theme.BOLD}{Theme.CYAN}  {title:^{w-4}}  {Theme.RESET}\n{Theme.BLUE}{'═'*w}{Theme.RESET}")

def get_input(prompt: str, default: Any = None, type_func: Callable = str) -> Any:
    p = f"{Theme.BOLD}{Theme.CYAN}➤ {prompt}{Theme.RESET}" + \
        (f" {Theme.YELLOW}({default}){Theme.RESET}: " if default is not None else ": ")
    try:
        val = input(p).strip()
    except EOFError:
        return default
    if not val:
        return default
    try:
        return type_func(val)
    except ValueError:
        log(f"Invalid input type. Using default: {default}", "ERROR")
        return default

# =============================================================================
# REGION: INTERACTIVE DASHBOARD  (formerly CleanerDashboard class)
# =============================================================================

class CleanerDashboard:
    """Interactive TUI for the tweet cleaning pipeline."""

    def __init__(self):
        self.is_running     = True
        self.last_stats     = None
        self.default_column = AppConfig.DEFAULT_COLUMN
        self.default_cores  = AppConfig.DEFAULT_CORES
        self.use_stemming   = True

    # ------------------------------------------------------------------
    def list_data_files(self) -> List[str]:
        """Scans local and sibling web_scrape directory for data files."""
        patterns = ['*.csv', '*.json', '*.xlsx']
        files: List[str] = []
        for p in patterns:
            files.extend(glob.glob(p))
        web_scrape_path = os.path.join('..', 'web_scrape')
        if os.path.exists(web_scrape_path):
            for p in patterns:
                files.extend(glob.glob(os.path.join(web_scrape_path, p)))
        return sorted(set(files))

    # ------------------------------------------------------------------
    async def clean_workflow(self):
        """Step-by-step cleaning wizard."""
        print_header("DATA CLEANING WIZARD")

        files = self.list_data_files()
        if not files:
            log("No data files found in the vicinity.", "ERROR")
            input_file = get_input("Enter Path Manually")
            if not input_file:
                return
        else:
            print(f" {Theme.BOLD}AVAILABLE DATASETS:{Theme.RESET}")
            for i, f in enumerate(files, 1):
                print(f"  {Theme.YELLOW}[{i}]{Theme.RESET} {f}")

            sel = get_input("Select Dataset # (or enter path)", "1")
            if str(sel).isdigit() and 1 <= int(sel) <= len(files):
                input_file = files[int(sel) - 1]
            else:
                input_file = sel if sel else None

        if not input_file or not os.path.exists(input_file):
            log(f"File not found: {input_file}", "ERROR")
            return

        base          = os.path.splitext(os.path.basename(input_file))[0]
        suggested_out = f"cleaned_{base}.csv"
        output_file   = get_input("Output Filename", suggested_out)

        col   = get_input("Target Column",              self.default_column)
        stem  = get_input("Use Stemming? (y/n)", "y" if self.use_stemming else "n").lower() == 'y'
        cores = get_input("CPU Workers",                self.default_cores, int)

        log(f"Initializing Engine: {input_file} ➔ {output_file}", "TASK")
        stats = run_cleaning_pipeline(input_file, output_file, column=col, use_stemming=stem, cores=cores)

        if stats:
            self.last_stats = stats
            log(f"Pipeline Complete. {stats['final_total']} tweets saved.", "SUCCESS")
            self.display_stats(stats)
        else:
            log("Pipeline failed during execution.", "ERROR")

    # ------------------------------------------------------------------
    def display_stats(self, stats: Dict):
        """Renders cleaning statistics in a framed layout."""
        print("\n" + " " * 4 + Theme.BOLD + Theme.CYAN + "--- PERFORMANCE METRICS ---" + Theme.RESET)
        print(f"    {Theme.BOLD}Initial Tweets{Theme.RESET}   : {stats.get('total_initial', 0)}")
        print(f"    {Theme.BOLD}Duplicates Removed{Theme.RESET}: {stats.get('duplicates_removed', 0)}")
        print(f"    {Theme.BOLD}Bots Purged{Theme.RESET}      : {stats.get('bots_removed', 0)}")
        print(f"    {Theme.BOLD}Empty Records{Theme.RESET}    : {stats.get('empty_removed', 0)}")
        print(f"    {Theme.BOLD}Final Payload{Theme.RESET}    : {stats.get('final_total', 0)}")
        print(f"    {Theme.BLUE}───────────────────────────{Theme.RESET}")
        print(f"    {Theme.BOLD}Engine Latency{Theme.RESET}   : {stats.get('processing_time', 0):.2f}s")
        print(f"    {Theme.BOLD}Vocabulary Size{Theme.RESET}  : {stats.get('unique_vocab', 0)} unique words")
        print("    " + Theme.BLUE + "═" * 30 + Theme.RESET)

    # ------------------------------------------------------------------
    def view_dictionary_info(self):
        """Shows metadata about the loaded dictionaries."""
        print_header("DICTIONARY METADATA")
        print(f"  {Theme.BOLD}Slang Dictionary{Theme.RESET}  : {len(SLANG_DICT)} entries")
        print(f"  {Theme.BOLD}Protected Entities{Theme.RESET}: {len(KEY_ENTITIES)} words")
        print(f"  {Theme.BOLD}Custom Stopwords{Theme.RESET}  : {len(ADDITIONAL_STOPWORDS)} words")
        print(f"\n  {Theme.CYAN}Note:{Theme.RESET} Loaded from local JSON config files.")
        get_input("Press Enter to return", "")

    # ------------------------------------------------------------------
    def adjust_config(self):
        print_header("ENGINE CONFIGURATION")
        self.default_column = get_input("Default Text Column",       self.default_column)
        self.default_cores  = get_input("Default CPU Workers",        self.default_cores, int)
        self.use_stemming   = get_input("Enable Stemming? (y/n)", "y" if self.use_stemming else "n").lower() == 'y'
        log("Global defaults updated.", "SUCCESS")

    # ------------------------------------------------------------------
    async def run(self):
        """Main TUI loop."""
        MENU = {
            "1": ("Start Cleaning Wizard",   "Interactive step-by-step cleaning process.",           self.clean_workflow),
            "2": ("View Last Session Stats",  "Display performance metrics of the last run.",
                  lambda: self.display_stats(self.last_stats) if self.last_stats else log("No stats recorded yet.", "WAIT")),
            "3": ("Dictionary Overview",      "Check the status of loaded slang and stopword sets.", self.view_dictionary_info),
            "4": ("Engine Configuration",     "Adjust default workers and target columns.",           self.adjust_config),
            "0": ("Exit Dashboard",           "Terminate the cleaning console.",                      None),
        }

        while self.is_running and not AppState.STOP_REQUESTED:
            print(f"\n{Theme.BOLD}{Theme.CYAN}    --- INDONESIAN CLEANER DASHBOARD v2.0 ---{Theme.RESET}")
            print(f"{Theme.BLUE}{'─'*AppConfig.DASHBOARD_WIDTH}{Theme.RESET}")

            for k in ["1", "2", "3", "4"]:
                n, d, _ = MENU[k]
                print(f"  {Theme.YELLOW}[{k}]{Theme.RESET} {Theme.BOLD}{n:<22}{Theme.RESET} {Theme.CYAN}➔{Theme.RESET} {d}")

            print(f"\n  {Theme.YELLOW}[0]{Theme.RESET} {Theme.BOLD}Exit Dashboard{Theme.RESET}")
            print(f"{Theme.BLUE}{'─'*AppConfig.DASHBOARD_WIDTH}{Theme.RESET}")

            try:
                AppState.STOP_REQUESTED = False
                ch = get_input("SYSTEM READY. SELECT OPERATION")
                if ch == '0' or str(ch).lower() == 'q':
                    break
                if ch in MENU:
                    try:
                        res = MENU[ch][2]
                        if callable(res):
                            if inspect.iscoroutinefunction(res):
                                await res()
                            else:
                                maybe_coro = res()
                                if inspect.iscoroutine(maybe_coro):
                                    await maybe_coro
                    except KeyboardInterrupt:
                        log("Action aborted. Returning to menu.", "WAIT")
            except KeyboardInterrupt:
                print()
                log("Returning to menu... (Ctrl+C again to quit)", "WAIT")


# =============================================================================
# REGION: ENTRY POINTS
# =============================================================================

def _run_cli():
    """Legacy CLI mode — invoked via `python tweet_cleaner.py --cli ...`"""
    print("=" * 50)
    print("      INDONESIAN TWEET CLEANER - CLI MODE")
    print("=" * 50)

    parser = argparse.ArgumentParser(prog="tweet_cleaner", description="Indonesian Tweet Cleaner CLI")
    parser.add_argument("input",     help="Input file path (CSV / JSON / XLSX)")
    parser.add_argument("output",    help="Output file path")
    parser.add_argument("--column",  default="text",  help="Text column name (default: text)")
    parser.add_argument("--no-stem", action="store_true", help="Disable Sastrawi stemming")
    parser.add_argument("--cores",   type=int, default=4, help="Number of CPU workers (default: 4)")
    args = parser.parse_args()

    stats = run_cleaning_pipeline(
        args.input, args.output,
        column=args.column,
        use_stemming=not args.no_stem,
        cores=args.cores,
    )

    if stats:
        print("\n" + "=" * 50)
        print("               CLEANING SUMMARY")
        print("=" * 50)
        print(f"Initial Tweets      : {stats['total_initial']}")
        print(f"Duplicates Removed  : {stats['duplicates_removed']}")
        print(f"Bots Removed        : {stats['bots_removed']}")
        print(f"Empty After Clean   : {stats['empty_removed']}")
        print(f"Final Tweets (Used) : {stats['final_total']}")
        print(f"Total Deleted       : {stats['total_deleted']}")
        print("-" * 30)
        print(f"Startup Time        : {stats['startup_time']:.2f} seconds")
        print(f"Processing Time     : {stats['processing_time']:.2f} seconds")
        print(f"Unique Vocabulary   : {stats['unique_vocab']} words")
        print("=" * 50)


async def _run_dashboard():
    dash = CleanerDashboard()
    await dash.run()


if __name__ == "__main__":
    # If '--cli' is the first argument, strip it and hand off to argparse CLI.
    # Otherwise, launch the interactive TUI dashboard.
    if len(sys.argv) > 1 and sys.argv[1] == '--cli':
        sys.argv.pop(1)   # remove the --cli flag so argparse doesn't see it
        _run_cli()
    else:
        try:
            asyncio.run(_run_dashboard())
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"\n{Theme.RED}[FATAL]{Theme.RESET} System Crash: {e}")
