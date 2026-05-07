import os
import glob
import logging
import signal
import inspect
import asyncio
from typing import (
    List, Dict, Optional, Any, Callable, Final, ClassVar
)
from dataclasses import dataclass

# Import the core logic
try:
    from tweet_cleaner import run_cleaning_pipeline, SLANG_DICT, KEY_ENTITIES, ADDITIONAL_STOPWORDS
except ImportError:
    # Fallback if run from different context
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from tweet_cleaner import run_cleaning_pipeline, SLANG_DICT, KEY_ENTITIES, ADDITIONAL_STOPWORDS

# =============================================================================
# REGION: THEME & CONSTANTS
# =============================================================================

class Theme:
    """Centralized ANSI styling constants (Matching Twitter Scraper Style)."""
    RESET: Final[str] = "\033[0m"
    BOLD: Final[str] = "\033[1m"
    RED: Final[str] = "\033[0;31m"
    GREEN: Final[str] = "\033[0;32m"
    YELLOW: Final[str] = "\033[0;33m"
    BLUE: Final[str] = "\033[0;34m"
    CYAN: Final[str] = "\033[0;36m"
    MAGENTA: Final[str] = "\033[0;35m"

@dataclass(frozen=True)
class AppConfig:
    """Dashboard configuration."""
    DASHBOARD_WIDTH: ClassVar[int] = 76
    DEFAULT_CORES: ClassVar[int] = 4
    DEFAULT_COLUMN: ClassVar[str] = "text"

# =============================================================================
# REGION: CORE INITIALIZATION
# =============================================================================

class AppState:
    STOP_REQUESTED = False

def _interupt_handler(signum, frame):
    if AppState.STOP_REQUESTED:
        print("\n\033[0;31m[FATAL]\033[0m Forced Exit.")
        os._exit(1)
    print("\n\033[0;33m[WAIT]\033[0m Interrupt detected! Returning to menu... (Press Ctrl+C again to force exit)")
    AppState.STOP_REQUESTED = True

signal.signal(signal.SIGINT, _interupt_handler)

# =============================================================================
# REGION: UI FRAMEWORK
# =============================================================================

class DashboardLogger(logging.Formatter):
    """Custom color-coded formatter."""
    def format(self, record):
        cat = record.levelname
        colors = {
            "INFO": Theme.CYAN, "SUCCESS": Theme.GREEN, "LIMIT": Theme.YELLOW + Theme.BOLD, 
            "ERROR": Theme.RED, "FATAL": Theme.RED + Theme.BOLD, "AUTH": Theme.MAGENTA,
            "TASK": Theme.BLUE + Theme.BOLD, "FILE": Theme.BLUE, "WAIT": Theme.YELLOW
        }
        color = colors.get(cat, Theme.RESET)
        return f" {color}{Theme.BOLD}{cat:<8}{Theme.RESET} │ {record.getMessage()}"

# Register Custom Logging levels
for lvl, name in [(25, "SUCCESS"), (35, "LIMIT"), (15, "AUTH"), (16, "TASK"), (17, "FILE"), (18, "WAIT")]:
    logging.addLevelName(lvl, name)

logger = logging.getLogger("CleanerDashboard")
logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(DashboardLogger())
logger.addHandler(sh)

def log(msg: str, cat: str = "INFO"):
    mappings = {"INFO": 20, "SUCCESS": 25, "LIMIT": 35, "ERROR": 40, "FATAL": 50, "AUTH": 15, "TASK": 16, "FILE": 17, "WAIT": 18}
    logger.log(mappings.get(cat, 20), msg)

def print_header(title: str):
    """Visual framed header."""
    w = AppConfig.DASHBOARD_WIDTH
    print(f"\n{Theme.BLUE}{'═'*w}{Theme.RESET}\n{Theme.BOLD}{Theme.CYAN}  {title:^{w-4}}  {Theme.RESET}\n{Theme.BLUE}{'═'*w}{Theme.RESET}")

def get_input(prompt: str, default: Any = None, type_func: Callable = str) -> Any:
    """Interactive CLI prompt with default handling."""
    p = f"{Theme.BOLD}{Theme.CYAN}➤ {prompt}{Theme.RESET}" + (f" {Theme.YELLOW}({default}){Theme.RESET}: " if default is not None else ": ")
    try:
        val = input(p).strip()
    except EOFError:
        return default
    if not val: return default
    try: return type_func(val)
    except ValueError:
        log(f"Invalid input type. Using default: {default}", "ERROR")
        return default

# =============================================================================
# REGION: CLEANER DASHBOARD CLASS
# =============================================================================

class CleanerDashboard:
    """Interactive Control Layer for Tweet Cleaning."""
    
    def __init__(self):
        self.is_running = True
        self.last_stats = None
        self.default_column = AppConfig.DEFAULT_COLUMN
        self.default_cores = AppConfig.DEFAULT_CORES
        self.use_stemming = True

    def list_data_files(self) -> List[str]:
        """Scans local and parent directories for data files."""
        patterns = ['*.csv', '*.json', '*.xlsx']
        files = []
        # Current dir
        for p in patterns:
            files.extend(glob.glob(p))
        # Parent web_scrape dir (common data source)
        web_scrape_path = os.path.join('..', 'web_scrape')
        if os.path.exists(web_scrape_path):
            for p in patterns:
                files.extend(glob.glob(os.path.join(web_scrape_path, p)))
        return sorted(list(set(files)))

    async def clean_workflow(self):
        """Step-by-step cleaning wizard."""
        print_header("DATA CLEANING WIZARD")
        
        files = self.list_data_files()
        if not files:
            log("No data files found in the vicinity.", "ERROR")
            input_file = get_input("Enter Path Manually")
            if not input_file: return
        else:
            print(f" {Theme.BOLD}AVAILABLE DATASETS:{Theme.RESET}")
            for i, f in enumerate(files, 1):
                print(f"  {Theme.YELLOW}[{i}]{Theme.RESET} {f}")
            
            sel = get_input("Select Dataset # (or enter path)", "1")
            if str(sel).isdigit() and 1 <= int(sel) <= len(files):
                input_file = files[int(sel)-1]
            else:
                input_file = sel if sel else None
        
        if not input_file or not os.path.exists(input_file):
            log(f"File not found: {input_file}", "ERROR")
            return

        # Output path suggestion
        base = os.path.splitext(os.path.basename(input_file))[0]
        suggested_out = f"cleaned_{base}.csv"
        output_file = get_input("Output Filename", suggested_out)
        
        col = get_input("Target Column", self.default_column)
        stem = get_input("Use Stemming? (y/n)", "y" if self.use_stemming else "n").lower() == 'y'
        cores = get_input("CPU Workers", self.default_cores, int)

        log(f"Initializing Engine: {input_file} ➔ {output_file}", "TASK")
        stats = run_cleaning_pipeline(input_file, output_file, column=col, use_stemming=stem, cores=cores)
        
        if stats:
            self.last_stats = stats
            log(f"Pipeline Complete. Processed {stats['final_total']} tweets.", "SUCCESS")
            self.display_stats(stats)
        else:
            log("Pipeline failed during execution.", "ERROR")

    def display_stats(self, stats: Dict):
        """Renders cleaning statistics in a framed layout."""
        print("\n" + " " * 4 + Theme.BOLD + Theme.CYAN + "--- PERFORMANCE METRICS ---" + Theme.RESET)
        print(f"    {Theme.BOLD}Input Path{Theme.RESET}      : {stats.get('total_initial', 0)} tweets")
        print(f"    {Theme.BOLD}Bots Purged{Theme.RESET}     : {stats.get('bots_removed', 0)}")
        print(f"    {Theme.BOLD}Empty Records{Theme.RESET}   : {stats.get('empty_removed', 0)}")
        print(f"    {Theme.BOLD}Final Payload{Theme.RESET}   : {stats.get('final_total', 0)}")
        print(f"    {Theme.BLUE}───────────────────────────{Theme.RESET}")
        print(f"    {Theme.BOLD}Engine Latency{Theme.RESET}  : {stats.get('processing_time', 0):.2f}s")
        print(f"    {Theme.BOLD}Vocabulary Size{Theme.RESET} : {stats.get('unique_vocab', 0)} unique words")
        print("    " + Theme.BLUE + "═" * 30 + Theme.RESET)

    def view_dictionary_info(self):
        """Shows metadata about the loaded dictionaries."""
        print_header("DICTIONARY METADATA")
        print(f"  {Theme.BOLD}Slang Dictionary{Theme.RESET}  : {len(SLANG_DICT)} entries")
        print(f"  {Theme.BOLD}Protected Entities{Theme.RESET}: {len(KEY_ENTITIES)} words")
        print(f"  {Theme.BOLD}Custom Stopwords{Theme.RESET}  : {len(ADDITIONAL_STOPWORDS)} words")
        print(f"\n  {Theme.CYAN}Note:{Theme.RESET} These are loaded from local JSON config files.")
        get_input("Press Enter to return", "")

    async def run(self):
        """Main Loop."""
        MENU = {
            "1": ("Start Cleaning Wizard", "Interactive step-by-step cleaning process.", self.clean_workflow),
            "2": ("View Last Session Stats", "Display performance metrics of the last run.", lambda: self.display_stats(self.last_stats) if self.last_stats else log("No stats recorded yet.", "WAIT")),
            "3": ("Dictionary Overview", "Check the status of loaded slang and stopword sets.", self.view_dictionary_info),
            "4": ("Engine Configuration", "Adjust default workers and target columns.", self.adjust_config),
            "0": ("Exit Dashboard", "Terminate the cleaning console.", None)
        }

        while self.is_running:
            print(f"\n{Theme.BOLD}{Theme.CYAN}    --- INDONESIAN CLEANER DASHBOARD v1.0 ---{Theme.RESET}")
            print(f"{Theme.BLUE}{'─'*AppConfig.DASHBOARD_WIDTH}{Theme.RESET}")
            
            for k in ["1", "2", "3", "4"]:
                n, d, _ = MENU[k]
                print(f"  {Theme.YELLOW}[{k}]{Theme.RESET} {Theme.BOLD}{n:<22}{Theme.RESET} {Theme.CYAN}➔{Theme.RESET} {d}")
            
            print(f"\n  {Theme.YELLOW}[0]{Theme.RESET} {Theme.BOLD}Exit Dashboard{Theme.RESET}")
            print(f"{Theme.BLUE}{'─'*AppConfig.DASHBOARD_WIDTH}{Theme.RESET}")

            try:
                ch = get_input("SYSTEM READY. SELECT OPERATION")
                if ch == '0' or str(ch).lower() == 'q': break
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
                        log("Action aborted.", "WAIT")
            except KeyboardInterrupt:
                print()
                break

    def adjust_config(self):
        print_header("ENGINE CONFIGURATION")
        self.default_column = get_input("Default Text Column", self.default_column)
        self.default_cores = get_input("Default CPU Workers", self.default_cores, int)
        self.use_stemming = get_input("Enable Stemming by default? (y/n)", "y" if self.use_stemming else "n").lower() == 'y'
        log("Global defaults updated.", "SUCCESS")

async def main():
    dash = CleanerDashboard()
    await dash.run()

if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"\n{Theme.RED}[FATAL]{Theme.RESET} System Crash: {e}")
