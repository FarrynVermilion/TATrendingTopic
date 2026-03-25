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

def calculate_custom_tfidf(sentences):
    # 1. Prepare Basic Corpus Stats
    N = len(sentences) # Jumlah kalimat
    total_kata = sum(len(s) for s in sentences) # Total keseluruhan kata
    min_threshold = total_kata / N # Min threshold (rata-rata panjang kalimat)

    # 2. Count Word Frequencies
    global_counts = Counter()
    df_counts = Counter()

    for s in sentences:
        global_counts.update(s)
        # Unique words in the current sentence for Document Frequency (DF)
        for w in set(s):
            df_counts[w] += 1

    # 3. Calculate Word Weights (Bobot Kata)
    word_stats = {}
    for word in global_counts:
        tf = global_counts[word] / total_kata
        idf = N / df_counts[word]
        bobot_kata = tf * math.log2(idf)
        
        word_stats[word] = {
            'Kata Unik': word,
            'Seluruh Kemunculan': global_counts[word],
            'Jml Tweet Mengandung Kata': df_counts[word],
            'Term Frequency (TF)': tf,
            'IDF': idf,
            'Bobot Kata': bobot_kata
        }

    # 4. Calculate Sentence Weights (Bobot Kalimat)
    sentence_stats = []
    for i, s in enumerate(sentences):
        panjang_kalimat = len(s)
        nfs = max(panjang_kalimat, min_threshold)
        
        # Sum of the weights of all words in the sentence
        total_bobot_kata = sum(word_stats[word]['Bobot Kata'] for word in s)
        bobot_kalimat = total_bobot_kata / nfs
        
        sentence_stats.append({
            'No Urut': i + 1,
            'Hasil Kalimat': ", ".join(s),
            'Panjang Kalimat': panjang_kalimat,
            'nf(s)': nfs,
            'Total Bobot Kata': total_bobot_kata,
            'Bobot Kalimat': bobot_kalimat
        })

    # Convert to pandas DataFrames for nice tabular viewing
    df_words = pd.DataFrame(word_stats.values()).sort_values(by='Kata Unik').reset_index(drop=True)
    df_sentences = pd.DataFrame(sentence_stats).sort_values(by='Bobot Kalimat', ascending=False).reset_index(drop=True)

    return df_words, df_sentences, min_threshold, total_kata

def preprocess_tweet(tweet):
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

if __name__ == "__main__":
    print("Loading and preprocessing dataset... (This might take a while due to Sastrawi stemming)")
    df_raw = pd.read_csv("perang_iran.csv")
    
    dataset = []
    for text in df_raw['text'].dropna():
        tokens = preprocess_tweet(text)
        if tokens:  # Only add non-empty sequences
            dataset.append(tokens)

    print("Calculating TF-IDF...")
    df_words, df_sentences, min_thresh, total_words = calculate_custom_tfidf(dataset)

    print(f"Total Kata: {total_words}")
    print(f"Min Threshold (Rata-rata): {min_thresh}\n")

    print("="*80)
    print("1. TABEL KATA UNIK & BOBOT KATA")
    print("="*80)
    print(df_words.head(20).to_string(index=False))
    print("... (Showing top 20 rows)")

    print("\n" + "="*80)
    print("2. TABEL HASIL PEMBOBOTAN KALIMAT")
    print("="*80)
    print(df_sentences.head(20).to_string(index=False))
    print("... (Showing top 20 rows)")
    
    # Uncomment these lines to save the outputs to CSV files instead of just printing:
    df_words.to_csv("tf_idf_words_output.csv", index=False)
    df_sentences.to_csv("tf_idf_sentences_output.csv", index=False)
