# text_vec.py
from __future__ import annotations
from typing import Dict, Iterable, List, Tuple
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer


def vectorize_counts(
        texts: List[str],
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Fit a CountVectorizer on the provided texts and return word counts + vocabulary.

    Args:
        texts: List of document strings (Wikipedia extract).

    Returns:
        counts: Array of word counts, shape (vocab_size,)
        vocab: Array of vocabulary terms, shape (vocab_size,)
    """
    vectorizer = CountVectorizer(stop_words="english")
    document_term_matrix = vectorizer.fit_transform(texts)
    word_counts = np.asarray(document_term_matrix.sum(axis=0)).ravel()
    vocabulary = vectorizer.get_feature_names_out()
    return word_counts, vocabulary


def to_freq_dict(word_counts: np.ndarray, vocabulary: np.ndarray) -> Dict[str, Dict[str, float]]:
    """
    Convert word counts into {word: {"count": int, "percent": float}}.
    """
    total_count = float(word_counts.sum()) or 1.0
    order = np.argsort(-word_counts)  # descending
    return {
        str(vocabulary[i]): {
            "count": int(word_counts[i]),
            "percent": (word_counts[i] / total_count) * 100.0,
        }
        for i in order if word_counts[i] > 0
    }


def apply_ignore_list(
        word_counts: np.ndarray,
        vocabulary: np.ndarray,
        ignore_list: Iterable[str],
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Remove words in the ignore list from counts + vocabulary.
    """
    ignore_set = {word.lower() for word in ignore_list}
    keep_mask = np.array([word.lower() not in ignore_set for word in vocabulary], dtype=bool)
    return word_counts[keep_mask], vocabulary[keep_mask]


def apply_percentile(
        word_counts: np.ndarray,
        vocabulary: np.ndarray,
        percentile: int,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Keep only words whose count >= the given percentile cutoff.
    """
    if word_counts.size == 0:
        return word_counts, vocabulary
    cutoff = float(np.percentile(word_counts, percentile))
    keep_mask = word_counts >= cutoff
    return word_counts[keep_mask], vocabulary[keep_mask]
