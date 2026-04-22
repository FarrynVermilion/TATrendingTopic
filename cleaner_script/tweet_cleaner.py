import re
import pandas as pd
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory
import argparse
import sys
import multiprocessing
from functools import partial
from collections import Counter
import time
import json
from tqdm import tqdm

import os

# Load Config from JSON
def load_json_config(f_name, is_set=False):
    if not os.path.exists(f_name):
        raise FileNotFoundError(f"Critical configuration file '{f_name}' is missing.")
    try:
        with open(f_name, 'r') as f:
            data = json.load(f)
            return set(data) if is_set else data
    except Exception as e:
        print(f"[!] Error loading {f_name}: {e}")
        return set() if is_set else {}

# Load the dictionary from the current script to ensure no loss
def load_slang_dict():
    return load_json_config('slang_dict.json')

# Re-establishing the massive dictionary
SLANG_DICT = load_slang_dict()

# IMPORTANT ENTITIES TO PRESERVE
KEY_ENTITIES = load_json_config('preserve.json', is_set=True)

# ADDITIONAL STOPWORDS
ADDITIONAL_STOPWORDS = load_json_config('stopwords.json', is_set=True)

worker_cleaner = None

class TweetCleaner:
    def __init__(self, use_stemming=True):
        self.factory = StemmerFactory()
        self.stemmer = self.factory.create_stemmer() if use_stemming else None
        self.stopword_factory = StopWordRemoverFactory()
        self.stopword_remover = self.stopword_factory.create_stop_word_remover()
        self.stem_cache = {}
        self.stats = Counter()
        
    def clean_text(self, text, slang_dict):
        if not isinstance(text, str): return ""
        text = text.lower()
        text = re.sub(r'https?://\S+|www\.\S+', '', text)
        text = re.sub(r'@\w+', '', text)
        text = re.sub(r'#\w+', '', text)
        text = re.sub(r'^rt\s+', '', text)
        text = re.sub(r'[^a-zA-Z\s]', ' ', text)
        text = re.sub(r'(\w)\1{2,}', r'\1', text)
        
        tokens = text.split()
        normalized = [slang_dict.get(w, w) for w in tokens]
        tokens = [w for w in normalized if w not in ADDITIONAL_STOPWORDS]
        self.stats['stopwords_removed'] += (len(normalized) - len(tokens))
        
        cleaned_text = " ".join(tokens)
        tokens_before = cleaned_text.split()
        cleaned_text = self.stopword_remover.remove(cleaned_text)
        tokens_after = cleaned_text.split()
        
        final_list = []
        for w in tokens_before:
            if w in tokens_after or w in KEY_ENTITIES:
                final_list.append(w)
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

def main():
    print("="*50)
    print("      INDONESIAN TWEET CLEANER - OPTIMIZED CLI")
    print("="*50)
    
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--column", default="text")
    parser.add_argument("--no-stem", action="store_true")
    parser.add_argument("--cores", type=int, default=4)
    args = parser.parse_args()
    
    try:
        if args.input.endswith('.csv'):
            df = pd.read_csv(args.input)
        elif args.input.endswith('.json'):
            df = pd.read_json(args.input)
        else:
            df = pd.read_excel(args.input)
    except Exception as e:
        print(f"[!] Error loading input: {e}"); return

    total_initial = len(df)
    if 'handle' in df.columns:
        df = df[~df['handle'].astype(str).str.lower().isin({'grok', 'chatgpt', 'bot'})]
    
    total_after_bot_filter = len(df)
    bots_removed = total_initial - total_after_bot_filter

    num_cores = min(args.cores, multiprocessing.cpu_count())
    print(f"[*] Starting {num_cores} workers. Please wait...")
    
    # Using smaller chunks for smoother progress bar
    chunk_size = max(1, total_after_bot_filter // (num_cores * 20))
    chunks = [df[args.column][i:i + chunk_size] for i in range(0, total_after_bot_filter, chunk_size)]
    
    start_time = time.time()
    with multiprocessing.Pool(processes=num_cores, initializer=_init_worker, initargs=(not args.no_stem,)) as pool:
        init_end = time.time()
        print(f"[*] Workers ready in {init_end - start_time:.2f}s. Processing {total_after_bot_filter} tweets...")
        
        proc_start = time.time()
        func = partial(_process_chunk_optimized, slang_dict=SLANG_DICT)
        
        results = []
        # tqdm progress bar over imap results
        for res in tqdm(pool.imap(func, chunks), total=len(chunks), desc="Cleaning Progress"):
            results.append(res)
            
        proc_end = time.time()
    
    df['cleaned_text'] = pd.concat([res[0] for res in results])
    total_stats = Counter()
    for res in results: total_stats.update(res[1])
    
    # Filter empty tweets
    df = df[df['cleaned_text'].str.strip() != ""]
    final_total = len(df)
    empty_removed = total_after_bot_filter - final_total
    if args.output.endswith('.json'):
        df.to_json(args.output, orient='records', indent=4)
    else:
        df.to_csv(args.output, index=False)
    
    all_words = " ".join(df['cleaned_text'].astype(str)).split()
    word_counts = Counter(all_words)
    pd.DataFrame(word_counts.most_common(), columns=['word', 'count']).to_csv("word_frequencies.csv", index=False)
    
    print("\n" + "="*50)
    print("               CLEANING SUMMARY")
    print("="*50)
    print(f"Initial Tweets      : {total_initial}")
    print(f"Bots Removed        : {bots_removed}")
    print(f"Empty After Clean   : {empty_removed}")
    print(f"Final Tweets (Used) : {final_total}")
    print(f"Total Deleted       : {total_initial - final_total}")
    print("-" * 30)
    print(f"Startup Time        : {init_end - start_time:.2f} seconds")
    print(f"Processing Time     : {proc_end - proc_start:.2f} seconds")
    print(f"Unique Vocabulary   : {len(word_counts)} words")
    print("="*50)

if __name__ == "__main__":
    main()
