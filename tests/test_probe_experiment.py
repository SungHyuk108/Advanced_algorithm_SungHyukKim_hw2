import csv
import tempfile
import unittest
import xml.etree.ElementTree as ElementTree
from pathlib import Path

from experiments.probe_experiment import (
    ExperimentResult,
    _unsuccessful_probe_count,
    _write_csv,
    _write_svg,
)
from src.hash_table import HashTable


class ProbeExperimentTests(unittest.TestCase):
    def test_failed_search_counts_every_node_in_the_bucket(self):
        table = HashTable(initial_capacity=8, resize_threshold=None)
        table.put("a", "first")
        table.put("i", "second")

        self.assertEqual(table.bucket_index("q"), table.bucket_index("a"))
        self.assertEqual(_unsuccessful_probe_count(table, "q"), 2)

    def test_writes_comparable_csv_and_valid_svg(self):
        result = ExperimentResult(
            target_alpha=0.25,
            alpha=0.25,
            entries=1023,
            successful_measured=1.135,
            successful_theory=1.125,
            failed_measured=0.246,
            failed_theory=0.25,
        )
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "results.csv"
            svg_path = Path(directory) / "results.svg"

            _write_csv([result], csv_path)
            _write_svg([result], svg_path)

            with csv_path.open(newline="", encoding="utf-8") as file:
                rows = list(csv.DictReader(file))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["capacity"], "4093")
            self.assertEqual(rows[0]["successful_theoretical_nodes"], "1.125000")
            self.assertEqual(rows[0]["failed_theoretical_nodes"], "0.250000")
            root = ElementTree.parse(svg_path).getroot()
            self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")


if __name__ == "__main__":
    unittest.main()
