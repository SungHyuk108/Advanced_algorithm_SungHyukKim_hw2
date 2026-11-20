import unittest

from src.hash_table import HashTable, LinearProbingHashTable


class HashTableTests(unittest.TestCase):
    def test_empty_table_and_missing_key(self):
        table = HashTable(initial_capacity=4)
        self.assertEqual(len(table), 0)
        self.assertFalse(table.contains_key("missing"))
        with self.assertRaises(KeyError):
            table.get("missing")

    def test_collisions_are_stored_and_counted(self):
        table = HashTable(initial_capacity=8, resize_threshold=None)
        keys_by_bucket = {}
        collision = None
        for number in range(100):
            key = f"key-{number}"
            bucket = table.bucket_index(key)
            if bucket in keys_by_bucket:
                collision = (keys_by_bucket[bucket], key)
                break
            keys_by_bucket[bucket] = key
        self.assertIsNotNone(collision)

        first, second = collision
        table.put(first, "first")
        table.put(second, "second")
        self.assertTrue(table.contains_key(first))
        self.assertTrue(table.contains_key(second))
        value, probes = table.get_with_probes(first)
        self.assertEqual(value, "first")
        self.assertEqual(probes, 2)

    def test_overwrite_does_not_increase_size(self):
        table = HashTable(initial_capacity=4)
        table.put("same", 1)
        table.put("same", 2)
        self.assertEqual(len(table), 1)
        self.assertEqual(table.get("same"), 2)

    def test_growth_preserves_values(self):
        table = HashTable(initial_capacity=4, resize_threshold=0.5)
        for number in range(12):
            table.put(f"key-{number}", number)
        self.assertGreater(table.capacity, 4)
        self.assertEqual(len(table), 12)
        for number in range(12):
            self.assertEqual(table.get(f"key-{number}"), number)

    def test_horner_trace_reports_each_character(self):
        table = HashTable(initial_capacity=8, resize_threshold=None)
        trace = table.hash_trace("abc")
        self.assertEqual([entry[0] for entry in trace], ["a", "b", "c"])
        self.assertEqual([entry[1] for entry in trace], [ord("a"), ord("b"), ord("c")])
        self.assertEqual([entry[2] for entry in trace], [1, 1, 2])
        self.assertEqual(trace[-1][2], table.bucket_index("abc"))

    def test_linear_probing_wraps_from_last_bucket_to_first(self):
        table = LinearProbingHashTable(initial_capacity=4, resize_threshold=None)
        keys = []
        for number in range(100):
            key = f"wrap-{number}"
            if table.bucket_index(key) == table.capacity - 1:
                keys.append(key)
            if len(keys) == 2:
                break

        self.assertEqual(len(keys), 2)
        table.put(keys[0], "first")
        table.put(keys[1], "second")
        self.assertEqual(table.get(keys[0]), "first")
        value, probes = table.get_with_probes(keys[1])
        self.assertEqual(value, "second")
        self.assertEqual(probes, 2)
        self.assertEqual(
            [slot for slot, _ in table.probe_trace(keys[1])],
            [table.capacity - 1, 0],
        )

    def test_linear_probing_can_fill_fixed_capacity_and_retrieve_every_key(self):
        table = LinearProbingHashTable(initial_capacity=4, resize_threshold=None)
        for number in range(table.capacity):
            table.put(f"full-{number}", number)

        self.assertEqual(len(table), table.capacity)
        for number in range(table.capacity):
            self.assertEqual(table.get(f"full-{number}"), number)
        self.assertFalse(table.contains_key("missing"))
        with self.assertRaises(KeyError):
            table.get("missing")
        missing_key = next(
            f"missing-{number}"
            for number in range(100)
            if table.bucket_index(f"missing-{number}")
            == table.bucket_index("present")
        )
        found, value, probes = table.search_with_probes(missing_key)
        self.assertFalse(found)
        self.assertIsNone(value)
        self.assertEqual(probes, table.capacity)
        self.assertEqual(len(table.probe_trace("missing")), table.capacity)

    def test_both_tables_share_measured_search_behavior(self):
        for table_type in (HashTable, LinearProbingHashTable):
            with self.subTest(table_type=table_type.__name__):
                table = table_type(initial_capacity=4, resize_threshold=None)
                table.put("present", None)

                found, value, probes = table.search_with_probes("present")
                self.assertTrue(found)
                self.assertIsNone(value)
                self.assertEqual(probes, 1)

                missing_key = next(
                    f"missing-{number}"
                    for number in range(100)
                    if table.bucket_index(f"missing-{number}")
                    == table.bucket_index("present")
                )
                found, value, probes = table.search_with_probes(missing_key)
                self.assertFalse(found)
                self.assertIsNone(value)
                self.assertGreaterEqual(probes, 1)
                self.assertEqual(len(table), 1)
                self.assertEqual(list(table.items()), [("present", None)])

    def test_non_string_keys_are_rejected(self):
        table = HashTable(initial_capacity=4)
        with self.assertRaises(TypeError):
            table.put(1, "value")
        with self.assertRaises(TypeError):
            table.get(1)


if __name__ == "__main__":
    unittest.main()
