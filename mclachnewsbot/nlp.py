import numpy as np
from nltk.corpus import stopwords
from nltk import download
from nltk.stem import WordNetLemmatizer
from gensim.models import KeyedVectors
from scipy import spatial


def _vectorize(tokens, model):
    return np.mean([model[token] for token in tokens], axis=0).tolist()


def initialize_model(path: str) -> KeyedVectors:
    """
    Load a word2vec model
    """
    download("stopwords")
    download("wordnet")

    return KeyedVectors.load_word2vec_format(path, binary=True)


def vectorize_text(full_text: str, model: KeyedVectors) -> np.ndarray:
    """
    Vectorize a story
    """
    stop_words = set(stopwords.words("english"))
    lemmatizer = WordNetLemmatizer()

    tokens = full_text.lower().split()
    tokens = [word for word in tokens if word not in stop_words]
    tokens = [lemmatizer.lemmatize(word) for word in tokens]
    tokens = [token for token in tokens if token in model.key_to_index]
    return _vectorize(tokens, model)


def similarity(vec1: list, vec2: list) -> float:
    """
    Compute the cosine similarity between two vectors
    """
    cosine_similarity = 1 - spatial.distance.cosine(np.array(vec1), np.array(vec2))
    return cosine_similarity
