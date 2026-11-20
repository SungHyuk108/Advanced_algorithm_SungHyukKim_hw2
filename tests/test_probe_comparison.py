import unittest

from experiments.probe_comparison import CAPACITY, LOAD_FACTORS, run_comparison


class ProbeComparisonTests(unittest.TestCase):
    def test_compares_both_tables_at_each_requested_load_factor(self):
        results = run_comparison()

        self.assertEqual(len(results), 9)
        self.assertEqual(LOAD_FACTORS[0], 0.1)
        self.assertEqual(LOAD_FACTORS[-1], 0.9)
        for result, target_alpha in zip(results, LOAD_FACTORS):
            with self.subTest(target_alpha=target_alpha):
                self.assertEqual(result.target_alpha, target_alpha)
                self.assertEqual(result.entries, round(CAPACITY * target_alpha))
                self.assertEqual(
                    result.chaining_success_theory,
                    1 + result.actual_alpha / 2,
                )
                self.assertEqual(
                    result.chaining_failed_theory,
                    result.actual_alpha,
                )
                self.assertAlmostEqual(
                    result.linear_success_theory,
                    0.5 * (1 + 1 / (1 - result.actual_alpha)),
                )
                self.assertAlmostEqual(
                    result.linear_failed_theory,
                    0.5 * (1 + 1 / (1 - result.actual_alpha) ** 2),
                )


if __name__ == "__main__":
    unittest.main()
