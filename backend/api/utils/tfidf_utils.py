import math
import re
import string
import pandas as pd
from collections import Counter
import nltk
from nltk.corpus import stopwords
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

# Initialize NLTK and Sastrawi
nltk.download('stopwords', quiet=True)
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)

factory = StemmerFactory()
stemmer = factory.create_stemmer()
stopwords_set = set(stopwords.words("indonesian"))

def preprocess_tweet(tweet):
    if not isinstance(tweet, str):
        return []
    # Remove URLs
    tweet = re.sub(r'http\S+|www\.\S+|pic\.twitter\.com\S+', '', tweet)
    # Remove mentions
    tweet = re.sub(r'@\w+', '', tweet)
    # Remove numbers
    tweet = re.sub(r'\d+', '', tweet)
    # Remove emojis and non-ASCII characters
    tweet = tweet.encode('ascii', 'ignore').decode('ascii')
    
    # Lowercase, remove punctuation, and strip extra whitespaces
    cleaned_tweet = tweet.lower().translate(str.maketrans("", "", string.punctuation))
    cleaned_tweet = re.sub(r'\s+', ' ', cleaned_tweet).strip()

    tokens = [stemmer.stem(token) for token in nltk.word_tokenize(cleaned_tweet) if token not in stopwords_set]
    return tokens

def calculate_custom_tfidf(sentences):
    # 1. Prepare Basic Corpus Stats
    N = len(sentences) # Jumlah kalimat
    total_kata = sum(len(s) for s in sentences) # Total keseluruhan kata
    min_threshold = total_kata / N if N > 0 else 0 # Min threshold (rata-rata panjang kalimat)

    # 2. Count Word Frequencies
    global_counts = Counter()
    df_counts = Counter()

    for s in sentences:
        global_counts.update(s)
        # Unique words in the current sentence for Document Frequency (DF)
        for w in set(s):
            df_counts[w] += 1

    # 3. Calculate Word Weights (Bobot Kata)
    word_stats = []
    for word in global_counts:
        tf = global_counts[word] / total_kata
        idf = N / df_counts[word] if df_counts[word] > 0 else 0
        bobot_kata = tf * math.log2(idf) if idf > 0 else 0
        
        word_stats.append({
            'Kata Unik': word,
            'Seluruh Kemunculan': global_counts[word],
            'Jml Tweet Mengandung Kata': df_counts[word],
            'Term Frequency (TF)': tf,
            'IDF': idf,
            'Bobot Kata': bobot_kata
        })

    # 4. Calculate Sentence Weights (Bobot Kalimat)
    sentence_stats = []
    word_dict = {w['Kata Unik']: w['Bobot Kata'] for w in word_stats}
    
    for i, s in enumerate(sentences):
        panjang_kalimat = len(s)
        nfs = max(panjang_kalimat, min_threshold)
        
        # Sum of the weights of all words in the sentence
        total_bobot_kata = sum(word_dict.get(word, 0) for word in s)
        bobot_kalimat = total_bobot_kata / nfs if nfs > 0 else 0
        
        sentence_stats.append({
            'No Urut': i + 1,
            'Hasil Kalimat': ", ".join(s),
            'Panjang Kalimat': panjang_kalimat,
            'nf(s)': nfs,
            'Total Bobot Kata': total_bobot_kata,
            'Bobot Kalimat': bobot_kalimat
        })

    df_words = pd.DataFrame(word_stats).sort_values(by='Kata Unik').reset_index(drop=True)
    df_sentences = pd.DataFrame(sentence_stats).sort_values(by='Bobot Kalimat', ascending=False).reset_index(drop=True)

    return df_words, df_sentences, min_threshold, total_kata

def process_csv_tfidf(file_obj, text_column):
    df_raw = pd.read_csv(file_obj)
    
    if text_column not in df_raw.columns:
        raise ValueError(f"Column '{text_column}' not found in CSV.")
        
    dataset = []
    for text in df_raw[text_column].dropna():
        tokens = preprocess_tweet(text)
        if tokens:
            dataset.append(tokens)

    df_words, df_sentences, min_thresh, total_words = calculate_custom_tfidf(dataset)
    return df_words, df_sentences
