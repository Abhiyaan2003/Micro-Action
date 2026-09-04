import unittest
import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestPTTReconciliation(unittest.TestCase):
    """
    Test LocalAgreement reconciliation logic used in PTTEngine ticks.
    """
    def test_local_agreement_words(self):
        committed_words = ["hello", "world"]
        prev_hypothesis = ["hello", "world", "this", "is", "a", "test"]
        curr_hypothesis = ["hello", "world", "this", "is", "another", "phrase"]

        n_committed = len(committed_words)
        prev_uncommitted = prev_hypothesis[n_committed:]
        curr_uncommitted = curr_hypothesis[n_committed:]

        match_count = 0
        min_len = min(len(prev_uncommitted), len(curr_uncommitted))
        for i in range(min_len):
            if prev_uncommitted[i] == curr_uncommitted[i]:
                match_count += 1
            else:
                break

        newly_committed = curr_uncommitted[:match_count]
        self.assertEqual(newly_committed, ["this", "is"])

        updated_committed = committed_words + newly_committed
        self.assertEqual(updated_committed, ["hello", "world", "this", "is"])

        tentative = curr_hypothesis[len(updated_committed):]
        self.assertEqual(tentative, ["another", "phrase"])

    def test_final_pass_reconciliation_exact_prefix(self):
        committed = ["hello", "world"]
        final_raw = "hello world this is the final transcription"
        final_words = final_raw.split()

        n_committed = len(committed)
        self.assertEqual(final_words[:n_committed], committed)
        remaining = final_words[n_committed:]
        self.assertEqual(remaining, ["this", "is", "the", "final", "transcription"])

    def test_final_pass_reconciliation_divergent_prefix(self):
        committed = ["hello", "world"]
        final_raw = "hello there this is different"
        final_words = final_raw.split()

        n_committed = len(committed)
        self.assertNotEqual(final_words[:n_committed], committed)
        remaining = final_words[n_committed:]
        self.assertEqual(remaining, ["this", "is", "different"])


if __name__ == "__main__":
    unittest.main()
