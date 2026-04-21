import re
import pandas as pd
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory
import argparse
import sys

# Common Indonesian Slang Mapping (Kamus Alay)
SLANG_DICT = {
    "yg": "yang",
    "gak": "tidak",
    "ga": "tidak",
    "tdk": "tidak",
    "jg": "juga",
    "udah": "sudah",
    "dah": "sudah",
    "kalo": "kalau",
    "tp": "tapi",
    "aja": "saja",
    "bgt": "banget",
    "blm": "belum",
    "dr": "dari",
    "dgn": "dengan",
    "sdh": "sudah",
    "jd": "jadi",
    "bs": "bisa",
    "krn": "karena",
    "pd": "pada",
    "dlm": "dalam",
    "nih": "ini",
    "itu": "itu",
    "gw": "saya",
    "lo": "kamu",
    "lu": "kamu",
    "gue": "saya",
    "elu": "kamu",
    "aq": "saya",
    "ak": "saya",
    "km": "kamu",
    "klo": "kalau",
    "tsb": "tersebut",
    "dl": "dulu",
    "ok": "oke",
    "sd": "sampai",
    "dpt": "dapat",
    "gmn": "bagaimana",
    "sm": "sama",
    "tll": "terlalu",
    "utk": "untuk",
    "skrg": "sekarang",
    "mrk": "mereka",
    "dg": "dengan",
    "jgn": "jangan",
    "sbg": "sebagai",
    "gt": "begitu",
    "gk": "tidak",
    "msh": "masih",
    "spt": "seperti",
    "lg": "lagi",
    "bkn": "bukan",
    "lbh": "lebih",
    "kpd": "kepada",
    "ttg": "tentang",
    "thn": "tahun",
    "hrs": "harus",
    "mmg": "memang",
    "knp": "kenapa",
    "byk": "banyak",
    "kyk": "kayak",
    "ttp": "tetap",
    "sdg": "sedang",
    "kl": "kalau",
    "sblm": "sebelum",
    "bln": "bulan",
    "liat": "lihat",
    "bilang": "cakap",
    "bikin": "buat",
    "tau": "tahu",
    # Name Normalization
    "as": "amerika",
    "usa": "amerika",
    "us": "amerika",
    "paman sam": "amerika",
}

# Additional Twitter-specific noise and Entity Blacklist (Names, Locations, Orgs)
ADDITIONAL_STOPWORDS = {
    # Noise
    'rt', 'via', 'dm', 'cc', 'id', 'user', 'tweet', 'retweet', 'amp',
    'wkwk', 'wkwkwk', 'deh', 'sih', 'dong', 'kok', 'lah', 'kah',
    
    # Locations (Countries/Regions/Cities)
    'iran', 'israel', 'amerika', 'as', 'usa', 'us', 'indonesia', 'indo',
    'arab', 'saudi', 'rusia', 'china', 'palestina', 'gaza', 'lebanon', 
    'syiria', 'yaman', 'houthi', 'teheran', 'tel', 'aviv', 'yerusalem', 
    'washington', 'jakarta', 'barat', 'timur', 'tengah', 'selat', 'hormuz',
    'teluk', 'negara', 'dunia', 'global',
    
    # People (Politicians/Leaders)
    'trump', 'donald', 'netanyahu', 'khamenei', 'biden', 'putin', 
    'jokowi', 'prabowo', 'sby', 'bibi',
    
    # Organizations/Others
    'pbb', 'nato', 'zionis', 'yahudi', 'islam', 'syiah', 'sunni'
}

# AI/Bot account blacklist
USER_BLACKLIST = {
    'grok', 'chatgpt', 'bot'
}


class TweetCleaner:
    def __init__(self, use_stemming=True):
        # Initialize Sastrawi tools
        self.stemmer = StemmerFactory().create_stemmer() if use_stemming else None
        self.stopword_remover = StopWordRemoverFactory().create_stop_word_remover()
        
    def clean_text(self, text):
        if not isinstance(text, str):
            return ""
            
        # 1. Lowercasing
        text = text.lower()
        
        # 2. Remove URLs
        text = re.sub(r'https?://\S+|www\.\S+', '', text)
        
        # 3. Remove Mentions (@user)
        text = re.sub(r'@\w+', '', text)
        
        # 4. Remove Hashtags (#tag)
        text = re.sub(r'#\w+', '', text)
        
        # 5. Remove "RT" prefix
        text = re.sub(r'^rt\s+', '', text)
        
        # 6. Handle HTML entities like &amp;
        text = re.sub(r'&amp;?|&lt;?|&gt;?', ' ', text)
        
        # 7. Remove URLs (secondary check for shortened links)
        text = re.sub(r't\.co/\w+', '', text)
        
        # 8. Remove Emojis and Non-ASCII (more aggressive)
        text = text.encode('ascii', 'ignore').decode('ascii')
        
        # 9. Remove Special Characters and Punctuation
        # This replaces everything except letters, numbers, and spaces with a space
        text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)
        
        # 10. Remove Numbers
        text = re.sub(r'\d+', '', text)
        
        # 11. Remove repeated characters (e.g., bangeeeet -> banget)
        text = re.sub(r'(\w)\1{2,}', r'\1', text)
        
        # 12. Split into tokens
        tokens = text.split()
        
        # 10. Normalize Slang and Remove Twitter noise (RT, via, etc.)
        tokens = [SLANG_DICT.get(word, word) for word in tokens if word not in ADDITIONAL_STOPWORDS]
        
        # 11. Join back for Sastrawi processing
        cleaned_text = " ".join(tokens)
        
        # 12. Remove Indonesian Stopwords (using Sastrawi)
        cleaned_text = self.stopword_remover.remove(cleaned_text)
        
        # 13. Stemming (Optional but recommended for GSDMM)
        if self.stemmer:
            cleaned_text = self.stemmer.stem(cleaned_text)
            
        # 14. Final Tokenization & Filtering
        # Filter out tokens that are too short (less than 3 chars) or common noise
        final_tokens = [w for w in cleaned_text.split() if len(w) > 2]
        
        return " ".join(final_tokens)

def main():
    # If no arguments are provided, switch to interactive mode
    if len(sys.argv) == 1:
        print("=== Indonesian Tweet Cleaner for GSDMM ===")
        input_file = input("[?] Enter input file path (CSV/Excel): ").strip()
        if not input_file:
            print("[!] Input file is required.")
            return
            
        output_file = input("[?] Enter output file path: ").strip()
        if not output_file:
            output_file = "cleaned_output.csv"
            print(f"[*] Using default output: {output_file}")
            
        column_name = input("[?] Enter text column name (default: 'text'): ").strip()
        if not column_name:
            column_name = "text"
            
        use_stemming = input("[?] Enable stemming? (y/n, default: y): ").lower().strip() != 'n'
        
        args = argparse.Namespace(
            input=input_file,
            output=output_file,
            column=column_name,
            no_stem=not use_stemming
        )
    else:
        parser = argparse.ArgumentParser(description="Clean Indonesian Tweets for GSDMM Clustering")
        parser.add_argument("input", help="Path to input CSV or Excel file")
        parser.add_argument("output", help="Path to save cleaned output")
        parser.add_argument("--column", default="text", help="Column name containing tweet text (default: 'text')")
        parser.add_argument("--no-stem", action="store_true", help="Disable stemming")
        args = parser.parse_args()
    
    print(f"[*] Reading data from {args.input}...")
    try:
        if args.input.endswith('.csv'):
            df = pd.read_csv(args.input)
        elif args.input.endswith('.xlsx') or args.input.endswith('.xls'):
            df = pd.read_excel(args.input)
        else:
            print("[!] Unsupported file format. Use CSV or Excel.")
            return
    except Exception as e:
        print(f"[!] Error reading file: {e}")
        return

    if args.column not in df.columns:
        print(f"[!] Column '{args.column}' not found. Available columns: {list(df.columns)}")
        return

    print("[*] Initializing cleaner (this may take a moment)...")
    cleaner = TweetCleaner(use_stemming=not args.no_stem)
    
    print("[*] Filtering out blacklisted users (AI/Bots)...")
    initial_rows = len(df)
    # Check if handle or username columns exist before filtering
    for col in ['handle', 'username']:
        if col in df.columns:
            df = df[~df[col].astype(str).str.lower().isin(USER_BLACKLIST)]
            
    filtered_rows = len(df)
    if initial_rows != filtered_rows:
        print(f"[*] Removed {initial_rows - filtered_rows} tweets from blacklisted accounts.")

    print("[*] Cleaning tweets...")
    # Progress indicator for large datasets
    total = len(df)
    df['cleaned_text'] = ""
    
    for i, row in df.iterrows():
        df.at[i, 'cleaned_text'] = cleaner.clean_text(row[args.column])
        if (i + 1) % 100 == 0:
            print(f"    - Processed {i+1}/{total}...", end='\r')
    
    print(f"\n[*] Cleaning complete. {total} tweets processed.")
    
    # Remove empty results (GSDMM requirement: documents must have content)
    initial_count = len(df)
    df = df[df['cleaned_text'].str.strip() != ""]
    final_count = len(df)
    
    if initial_count != final_count:
        print(f"[*] Removed {initial_count - final_count} empty tweets.")

    print(f"[*] Saving result to {args.output}...")
    if args.output.endswith('.csv'):
        df.to_csv(args.output, index=False)
    elif args.output.endswith('.xlsx'):
        df.to_excel(args.output, index=False)
    else:
        df.to_csv(args.output, index=False)
        
    print("[+] Done!")

if __name__ == "__main__":
    main()
