"""
Text preprocessing utilities for Indonesian tweet/short-text data.

This module provides the preprocessing pipeline used by the GSDMM topic model.
"""

import re
import string
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
    """
    Preprocess a single tweet/short-text for topic modeling.

    Steps:
      1. Remove URLs, mentions, numbers
      2. Remove emojis and non-ASCII characters
      3. Lowercase and remove punctuation
      4. Tokenize
      5. Remove stopwords (Indonesian)
      6. Stem using Sastrawi (Indonesian stemmer)

    Parameters
    ----------
    tweet : str
        Raw tweet text.

    Returns
    -------
    tokens : list[str]
        List of cleaned, stemmed tokens.
    """
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
