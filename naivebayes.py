import math
import os
import re
import string
import pandas as pd
from collections import Counter
import nltk
from nltk.corpus import stopwords
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

# Download NLTK data required for tokenization and stopwords
nltk.download('stopwords', quiet=True)
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)

# Initialize globally to avoid re-instantiating them for every tweet
factory = StemmerFactory()
stemmer = factory.create_stemmer()
stopwords_set = set(stopwords.words("indonesian"))

def split_data_by_sentiment(data, sentiment):
    """
    Split the data DataFrame into separate lists based on sentiment.

    Parameters:
       data (DataFrame): The input DataFrame containing 'text' and 'sentiment' columns.
       sentiment (str): The sentiment label to filter the data.

    Returns:
        list: A list of text corresponding to the specified sentiment.
    """
    result = data[data['sentiment'] == sentiment]['text'].tolist()
    print(f"[DEBUG] split_data_by_sentiment ('{sentiment}'): Found {len(result)} records. Sample: {result[:3]}")
    return result

def preprocess_tweet(tweet):
    original_tweet = tweet
    
    # Remove URLs (http, https, www, pic.twitter.com)
    tweet = re.sub(r'http\S+|www\.\S+|pic\.twitter\.com\S+', '', tweet)
    # Remove mentions (@username)
    tweet = re.sub(r'@\w+', '', tweet)
    # Remove numbers
    tweet = re.sub(r'\d+', '', tweet)
    # Remove emojis and non-ASCII characters
    tweet = tweet.encode('ascii', 'ignore').decode('ascii')
    
    # Lowercase, remove punctuation, and strip extra whitespaces
    cleaned_tweet = tweet.lower().translate(str.maketrans("", "", string.punctuation))
    cleaned_tweet = re.sub(r'\s+', ' ', cleaned_tweet).strip()

    tokens = [stemmer.stem(token) for token in nltk.word_tokenize(cleaned_tweet) if token not in stopwords_set]
    print(f"[DEBUG] preprocess_tweet:\n  Original: '{original_tweet}'\n  Tokens:   {tokens}")
    return tokens

def calculate_word_counts(tweets):
    word_count = Counter()
    for tweet in tweets:
        word_count.update(preprocess_tweet(tweet))
    print(f"[DEBUG] calculate_word_counts: Extracted {len(word_count)} unique words.")
    return word_count

def calculate_likelihood(word_count, total_words, laplacian_smoothing=1):
    vocabulary_size = len(word_count)
    denominator = total_words + laplacian_smoothing * vocabulary_size
    likelihoods = {word: (count + laplacian_smoothing) / denominator for word, count in word_count.items()}
    print(f"[DEBUG] calculate_likelihood: Computed likelihoods for {vocabulary_size} words. Denominator: {denominator}")
    return likelihoods

def calculate_log_prior(sentiment, data):
    log_prior = math.log(len(data[data['sentiment'] == sentiment]) / len(data))
    print(f"[DEBUG] calculate_log_prior ('{sentiment}'): {log_prior}")
    return log_prior

def classify_tweet_with_scores(tweet, log_likelihood_positive, log_likelihood_negative, log_likelihood_neutral,
                               log_prior_positive, log_prior_negative, log_prior_neutral):
    tokens = preprocess_tweet(tweet)

    sentiment_scores = {
        'positive': log_prior_positive + sum(log_likelihood_positive.get(token, 0) for token in tokens),
        'negative': log_prior_negative + sum(log_likelihood_negative.get(token, 0) for token in tokens),
        'neutral': log_prior_neutral + sum(log_likelihood_neutral.get(token, 0) for token in tokens)
    }

    predicted_sentiment = max(sentiment_scores, key=sentiment_scores.get)
    print(f"[DEBUG] classify_tweet_with_scores:\n  Tweet: '{tweet}'\n  Scores: {sentiment_scores}\n  Predicted: {predicted_sentiment}")
    return predicted_sentiment, sentiment_scores

if __name__ == "__main__":
    file_path = input("Enter the path to the dataset (CSV file) for Naive Bayes: ").strip()
    
    if os.path.exists(file_path):
        print(f"[INFO] Loading dataset from {file_path}...")
        df = pd.read_csv(file_path)
        train_df = df  # Using the entire dataset for training in this example
        
        # --- Example execution usage ---
        positive_data = split_data_by_sentiment(df, 'Positive')
        negative_data = split_data_by_sentiment(df, 'Negative')
        neutral_data = split_data_by_sentiment(df, 'Neutral')

        word_count_positive = calculate_word_counts(train_df[train_df['sentiment'] == 'Positive']['text'].astype(str))
        word_count_negative = calculate_word_counts(train_df[train_df['sentiment'] == 'Negative']['text'].astype(str))
        word_count_neutral = calculate_word_counts(train_df[train_df['sentiment'] == 'Neutral']['text'].astype(str))

        log_prior_positive = calculate_log_prior('Positive', df)
        log_prior_negative = calculate_log_prior('Negative', df)
        log_prior_neutral = calculate_log_prior('Neutral', df)
        
        print("[INFO] Naive Bayes calculation complete.")
    else:
        print(f"[ERROR] Could not find the file at {file_path}")