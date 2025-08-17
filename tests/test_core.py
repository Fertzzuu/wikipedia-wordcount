import unittest
import math
import numpy as np

from app.core.text import (
    vectorize_counts,
    to_freq_dict,
    apply_ignore_list,
    apply_percentile,
)


class TestVectorizeCounts(unittest.TestCase):
    def test_vectorize_counts_basic(self):
        texts = [
            "The quick brown fox jumps over the lazy dog.",
            "A quick brown fox was very, very quick!",
        ]
        counts, vocabulary = vectorize_counts(texts)

        self.assertIsInstance(counts, np.ndarray)
        self.assertIsInstance(vocabulary, np.ndarray)
        self.assertGreater(vocabulary.size, 0)
        self.assertEqual(counts.shape, (vocabulary.size,))

        vocab_list = list(vocabulary)
        self.assertIn("quick", vocab_list)
        self.assertIn("brown", vocab_list)
        self.assertIn("fox", vocab_list)

        quick_index = vocab_list.index("quick")
        self.assertEqual(int(counts[quick_index]), 3)

        if "very" in vocab_list:
            very_index = vocab_list.index("very")
            self.assertEqual(int(counts[very_index]), 2)

    def test_vectorize_counts_empty_input(self):
        counts, vocabulary = vectorize_counts([])
        self.assertEqual(vocabulary.size, 0)
        self.assertEqual(counts.size, 0)

    def test_vectorize_counts_mixed_case_and_punctuation(self):
        texts = [
            "HELLO, Hello... heLLo!!!",
            "hello? world; WORLD world.",
        ]
        counts, vocabulary = vectorize_counts(texts)
        vocab_list = list(vocabulary)
        self.assertIn("hello", vocab_list)
        self.assertIn("world", vocab_list)

        hello_index = vocab_list.index("hello")
        world_index = vocab_list.index("world")
        self.assertEqual(int(counts[hello_index]), 4)
        self.assertEqual(int(counts[world_index]), 3)


class TestToFreqDict(unittest.TestCase):
    def test_to_freq_dict_basic(self):
        counts = np.array([5, 3, 2])
        vocabulary = np.array(["alpha", "beta", "gamma"])
        freq = to_freq_dict(counts, vocabulary)

        self.assertEqual(list(freq.keys()), ["alpha", "beta", "gamma"])
        self.assertEqual(freq["alpha"]["count"], 5)
        self.assertEqual(freq["beta"]["count"], 3)
        self.assertEqual(freq["gamma"]["count"], 2)

        total_percent = sum(item["percent"] for item in freq.values())
        self.assertAlmostEqual(total_percent, 100.0, places=6)

    def test_to_freq_dict_zero_counts_excluded(self):
        counts = np.array([3, 0, 1, 0])
        vocabulary = np.array(["keep3", "zero1", "keep1", "zero2"])
        freq = to_freq_dict(counts, vocabulary)
        self.assertListEqual(list(freq.keys()), ["keep3", "keep1"])
        self.assertEqual(freq["keep3"]["count"], 3)
        self.assertEqual(freq["keep1"]["count"], 1)


class TestApplyIgnoreList(unittest.TestCase):
    def test_apply_ignore_list_case_insensitive(self):
        counts = np.array([10, 5, 1])
        vocabulary = np.array(["Hello", "WORLD", "keep"])
        new_counts, new_vocab = apply_ignore_list(
            counts, vocabulary, ["hello", "world"]
        )
        self.assertListEqual(list(new_vocab), ["keep"])
        self.assertListEqual(list(map(int, new_counts)), [1])

    def test_apply_ignore_list_mixed_present_absent(self):
        counts = np.array([4, 3, 2, 1])
        vocabulary = np.array(["alpha", "beta", "gamma", "delta"])
        new_counts, new_vocab = apply_ignore_list(
            counts, vocabulary, ["beta", "absent"]
        )
        self.assertListEqual(list(new_vocab), ["alpha", "gamma", "delta"])
        self.assertListEqual(list(map(int, new_counts)), [4, 2, 1])

    def test_apply_ignore_list_empty(self):
        counts = np.array([2, 2])
        vocabulary = np.array(["one", "two"])
        new_counts, new_vocab = apply_ignore_list(counts, vocabulary, [])
        np.testing.assert_array_equal(new_counts, counts)
        np.testing.assert_array_equal(new_vocab, vocabulary)


class TestApplyPercentile(unittest.TestCase):
    def test_apply_percentile_zero_keeps_all(self):
        counts = np.array([1, 2, 3, 4])
        vocabulary = np.array(["a", "b", "c", "d"])
        new_counts, new_vocab = apply_percentile(counts, vocabulary, 0)
        np.testing.assert_array_equal(new_counts, counts)
        np.testing.assert_array_equal(new_vocab, vocabulary)

    def test_apply_percentile_top_quartile(self):
        counts = np.array([1, 2, 3, 4])
        vocabulary = np.array(["w", "x", "y", "z"])
        new_counts, new_vocab = apply_percentile(counts, vocabulary, 75)
        self.assertListEqual(list(map(int, new_counts)), [4])
        self.assertListEqual(list(new_vocab), ["z"])

    def test_apply_percentile_includes_ties(self):
        counts = np.array([5, 5, 1, 1])
        vocabulary = np.array(["a", "b", "c", "d"])
        new_counts, new_vocab = apply_percentile(counts, vocabulary, 50)
        self.assertListEqual(list(map(int, new_counts)), [5, 5])
        self.assertListEqual(list(new_vocab), ["a", "b"])

    def test_apply_percentile_empty_input(self):
        counts = np.array([], dtype=int)
        vocabulary = np.array([], dtype=str)
        new_counts, new_vocab = apply_percentile(counts, vocabulary, 90)
        self.assertEqual(new_counts.size, 0)
        self.assertEqual(new_vocab.size, 0)


if __name__ == "__main__":
    unittest.main()
