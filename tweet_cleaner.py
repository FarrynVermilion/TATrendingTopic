import re
import pandas as pd
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory
import argparse
import sys
import multiprocessing
from functools import partial

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
    "amrik": "amerika",
    "isriwil": "israel",
    "weyhh": "",
    "smp": "sampai",
    "bt": "buat",
    "bbrp": "beberapa",
    "gausa": "tidak usah",
    "pas": "saat",
    "udh": "sudah",
    "monmaap": "maaf",
    "adlhenghasilkannpemimpin": "adalah menghasilkan pemimpin",
    "sma": "sama",
    "smua": "semua",
    "pst": "pasti",
    "trmasuk": "termasuk",
    "pnting": "penting",
    "tuju": "setuju",
    "keinget": "ingat",
    "tmn": "teman",
    "nyerang": "serang",
    "nyari": "cari",
    "nyoba": "coba",
    "ngasih": "kasih",
    "ngomong": "omong",
    "nulis": "tulis",
    "resiko": "risiko",
    "colong": "curi",
    "gin": "begini",
    "dorg": "mereka",
    "tpi": "tapi",
    "akn": "akan",
    "bnyk": "banyak",
    "sgt": "sangat",
    "kdg": "kadang",
    "blm": "belum",
    "blom": "belum",
    "tntu": "tentu",
    "bsa": "bisa",
    "jga": "juga",
    "nak": "hendak",
    "tadi": "tadi",
    "nanti": "nanti",
    "skrg": "sekarang",
    "sekrang": "sekarang",
    "ngebantu": "bantu",
    "maen": "main",
    "berantem": "gaduh",
    "gimana": "bagaimana",
    "kayak": "seperti",
    "kyk": "seperti",
    "banget": "sangat",
    "bgt": "sangat",
    "drmana": "darimana",
    "ape": "apa",
    "yah": "ya",
    "emang": "memang",
    "thd": "terhadap",
    "bhw": "bahwa",
    "drpd": "daripada",
    "mcm": "macam",
    "pdhl": "padahal",
    "dn": "dan",
    "mulu": "selalu",
    "nangkis": "tangkis",
    "gera": "gerak",
    "belaj": "belah",
    "eror": "error",
    "seneng": "senang",
    "dipake": "pakai",
    "dapet": "dapat",
    "nindas": "tindas",
    "ngga": "tidak",
    "nggak": "tidak",
    "gaperlu": "tidak perlu",
    "gakda": "tidak ada",
    "karna": "karena",
    "gitu": "begitu",
    "gini": "begitu",
    "mw": "mau",
    "mo": "mau",
    "skrng": "sekarang",
    "br": "baru",
    "sono": "sana",
    "rmh": "rumah",
    "ksh": "kasih",
    "mreka": "mereka",
    "krena": "karena",
    "mslaj": "masalah",
    "mrrka": "mereka",
    "koq": "kok",
    "pny": "punya",
    "israhell": "israel",
    "nargetin": "target",
    "nyitakin": "nyata",
    "nebar": "tebar",
    "sorga": "surga",
    "anjimg": "anjing",
    "mgkn": "mungkin",
    "smakin": "semakin",
    "tu": "itu",
    "tuh": "itu",
    "bacot": "bicara",
    "ngapain": "apa",
    "ngemis": "minta",
    "tolol": "bodoh",
    "goblok": "bodoh",
    "anjimg": "anjing",
    "bangsat": "jahat",
    "syuriah": "syria",
    "venesvela": "venezuela",
    "venesule": "venezuela",
    "tak": "tidak",
    "pasal": "tentang",
    "koit": "mati",
    "sound": "tegur",
    "skit": "sakit",
    "sy": "saya",
    "nggak": "tidak",
    "pake": "pakai",
    "bener": "benar",
    "sampe": "sampai",
    "ama": "sama",
    "pasu": "pasukan",
    "serikat": "amerika_serikat",
    "sia": "rusia",
}

# Additional Twitter-specific noise and Entity Blacklist (Names, Locations, Orgs)
ADDITIONAL_STOPWORDS = {
    # Noise
    'rt', 'via', 'dm', 'cc', 'id', 'user', 'tweet', 'retweet', 'amp',
    'wkwk', 'wkwkwk', 'deh', 'sih', 'dong', 'kok', 'lah', 'kah', 'lho',
    'btw', 'dll', 'dkk', 'cc', 'barakallahufik',
    
    # Core Keywords (Too frequent in this dataset)
    'perang', 'konflik', 'serang', 'lawan', 'militer', 'rudal', 'drone', 'bom',
    'iran', 'perang', 'serang', 'lawan',
    
    # Entity Noise
    'presiden', 'pimpin', 'perintah', 'menteri', 'rakyat', 'dunia', 'negara',
    'bangsa', 'masyarakat', 'kawan', 'sekutu', 'musuh', 'pihak',
    
    # Media/Link Noise
    'baca', 'berita', 'video', 'foto', 'gambar', 'update', 'klik', 'link', 
    'selengkapnya', 'berikut', 'langsung', 'lapor', 'papar', 'breaking', 'news',
    
    # Locations (Countries/Regions/Cities)
    'iran', 'israel', 'amerika', 'as', 'usa', 'us', 'indonesia', 'indo',
    'arab', 'saudi', 'rusia', 'china', 'cina', 'palestina', 'gaza', 'lebanon', 
    'syiria', 'yaman', 'houthi', 'teheran', 'tel', 'aviv', 'yerusalem', 
    'washington', 'jakarta', 'barat', 'timur', 'tengah', 'selat', 'hormuz',
    'teluk', 'venezuela', 'isfahan', 'russia', 'ukrania', 'ukraina', 'pakistan', 
    'afghanistan', 'taiwan', 'korea', 'selatan', 'utara', 'jepang', 'india', 
    'malaysia', 'eropa', 'kuba', 'korut', 'syuriah', 'venesvela',
    
    # Time/Days
    'senin', 'selasa', 'rabu', 'kamis', 'jumat', 'sabtu', 'minggu',
    'pagi', 'siang', 'sore', 'malam', 'hari', 'jam', 'menit', 'detik',
    'tahun', 'bulan', 'minggu', 'pasca', 'sekarang', 'dulu', 'nanti', 'tadi',
    
    # People (Politicians/Leaders)
    'trump', 'donald', 'netanyahu', 'khamenei', 'biden', 'putin', 
    'jokowi', 'prabowo', 'sby', 'bibi', 'ali', 'akbar', 'velayati',
    
    # Organizations/Others
    'pbb', 'nato', 'zionis', 'yahudi', 'islam', 'syiah', 'sunni', 'idf',
    'tni', 'hamas', 'friendly', 'fire', 'zionist', 'usa', 'uss', 'nazi',
    'astaghfirullahal', 'adziim', 'moga', 'siapa', 'gerangan', 'pny',
    'amin', 'mari', 'yuk', 'ayo', 'silahkan', 'mohon', 'tolong',
    
    # Pop Culture / Meme Noise
    'loid', 'papah', 'anya', 'anime', 'manga',
    
    # General Fillers
    'biar', 'bisa', 'jadi', 'buat', 'dapat', 'lihat', 'tahu', 'bilang', 
    'rasa', 'tuju', 'kali', 'banget', 'sangat', 'terlalu', 'emang', 'memang',
    'nyata', 'pasti', 'mungkin', 'kayaknya', 'mending', 'habis', 'aman',
    'hasil', 'pikir', 'cakap', 'masalah', 'anda', 'kamu', 'saya', 'kita',
    'mereka', 'kalian', 'orang', 'warga', 'anak', 'bini', 'suami', 'keluarga',
    'mampu', 'beri', 'tahu', 'bilang', 'lihat', 'buat', 'jadi', 'bisa', 'pakai',
    'serdadu', 'tentara', 'pasukan', 'menang', 'kalah', 'siaga', 'waspada',
    'berita', 'lapor', 'kabar', 'info', 'informasi',
    'sudah', 'kalau', 'saja', 'dari', 'karena', 'dalam', 'dengan', 'jangan',
    'begitu', 'masih', 'lagi', 'bukan', 'lebih', 'tentang', 'banyak', 'tetap',
    'sedang', 'beberapa', 'tidak', 'adalah', 'ada', 'itu', 'ini', 'yang',
    'untuk', 'pada', 'juga', 'saat', 'sebagai', 'sangat', 'secara', 'serta',
    'syria', 'venezuela', 'anjing', 'jahat', 'bodoh', 'bicara', 'minta',
    'the', 'war', 'irgc', 'usd', 'uea', 'bro', 'nggak', 'pake', 'gila', 'aku', 
    'kau', 'mana', 'satu', 'tuh', 'iya', 'doa', 'kek', 'mah', 'sok', 'ama',
    'mbg', 'bop', 'org', 'sia', 'aju', 'pro', 'irak', 'iraq', 'israhell', 
    'suriah', 'qatar', 'malaysia', 'ali', 'eropa', 'asia', 'laut', 'bbm',
    'gara', 'kait', 'laku', 'fakta', 'bijak', 'kondisi', 'situasi', 'hidup',
    'percaya', 'cepat', 'laku', 'fakta', 'juta', 'ribu', 'kait', 'gara',
    'operasi', 'besar', 'cari', 'alas', 'bakar', 'uang', 'ubah', 'sejarah',
    'kasih', 'bukti', 'jatuh', 'situasi', 'hidup', 'percaya', 'cepat', 'laku',
    'fakta', 'bijak', 'kondisi', 'tewas', 'politik', 'kuasa', 'wilayah', 
    'kawasan', 'pikir', 'jabat', 'pesawat', 'ganti', 'naik', 'turun', 'agama',
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
        # Cache for stemming results to speed up processing
        self.stem_cache = {}
        
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
            # Apply stemming with cache for performance
            stemmed_tokens = []
            for word in cleaned_text.split():
                if word not in self.stem_cache:
                    self.stem_cache[word] = self.stemmer.stem(word)
                stemmed_tokens.append(self.stem_cache[word])
            cleaned_text = " ".join(stemmed_tokens)
            
        # 14. Final Tokenization & Filtering
        # Filter out tokens that are too short (< 3) or too long (> 25)
        # Also filter out words that are in ADDITIONAL_STOPWORDS after stemming
        final_tokens = [w for w in cleaned_text.split() if 2 < len(w) < 25 and w not in ADDITIONAL_STOPWORDS]
        
        return " ".join(final_tokens)
        
# Helper function for multiprocessing
def _process_chunk(chunk_df, use_stemming, col_name):
    cleaner = TweetCleaner(use_stemming=use_stemming)
    return chunk_df[col_name].apply(cleaner.clean_text)

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

    print("[*] Cleaning tweets in parallel (using multiprocessing)...")
    total = len(df)
    
    # Split dataframe into chunks for parallel processing
    num_cores = multiprocessing.cpu_count()
    print(f"[*] Detected {num_cores} cores. Initializing workers...")
    
    # Split the dataframe into equal parts
    chunks = [df[i:i + total//num_cores + 1] for i in range(0, total, total//num_cores + 1)]
    
    with multiprocessing.Pool(processes=num_cores) as pool:
        # Use partial to pass constant arguments
        func = partial(_process_chunk, use_stemming=not args.no_stem, col_name=args.column)
        results = pool.map(func, chunks)
    
    # Merge results back
    df['cleaned_text'] = pd.concat(results)
    
    print(f"[*] Cleaning complete. {total} tweets processed.")
    
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
