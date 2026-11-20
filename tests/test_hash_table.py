import unittest

from src.hash_table import HashTable


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
        self.assertGreaterEqual(probes, 1)

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
        trace = table.hash_trace("ab")
        self.assertEqual([entry[0] for entry in trace], ["a", "b"])
        self.assertEqual([entry[1] for entry in trace], [ord("a"), ord("b")])
        self.assertEqual(trace[-1][2], table.bucket_index("ab"))

    def test_non_string_keys_are_rejected(self):
        table = HashTable(initial_capacity=4)
        with self.assertRaises(TypeError):
            table.put(1, "value")
        with self.assertRaises(TypeError):
            table.get(1)


if __name__ == "__main__":
    unittest.main()
