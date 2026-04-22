import math
import pandas as pd
from collections import Counter

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

if __name__ == "__main__":
    # Raw data strictly extracted from your 'tf - Bersih.csv'
    dataset = [
        ["gempa", "susul", "jadi", "di", "cianjur"],
        ["infak", "guna", "bantu", "korban", "gempa"],
        ["kelola", "pasar", "desa", "beri", "bantu"],
        ["gempa", "susul", "lumpuh", "cianjur"],
        ["tugas", "bantu", "gempa", "cianjur"],
        ["paket", "rendang", "beri", "kepada", "korban", "gempa"],
        ["reta", "puncak", "gunung", "gede"],
        ["korban", "gempa", "bumi", "di", "cianjur", "butuh", "bantu"],
        ["tes", "layak", "makan", "untuk", "layan", "korban", "bencana", "di", "cianjur"],
        ["gempa", "susul", "sering", "jadi", "di", "cianjur", "cianjur"]
    ]

    df_words, df_sentences, min_thresh, total_words = calculate_custom_tfidf(dataset)

    print(f"Total Kata: {total_words}")
    print(f"Min Threshold (Rata-rata): {min_thresh}\n")

    print("="*80)
    print("1. TABEL KATA UNIK & BOBOT KATA")
    print("="*80)
    # Print formatting matches your CSV values nicely
    print(df_words.to_string(index=False))

    print("\n" + "="*80)
    print("2. TABEL HASIL PEMBOBOTAN KALIMAT")
    print("="*80)
    print(df_sentences.to_string(index=False))
