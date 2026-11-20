import unittest

from src.base62 import decode, encode


class Base62Tests(unittest.TestCase):
    def test_zero_is_encoded_as_zero_character(self):
        self.assertEqual(encode(0), "0")
        self.assertEqual(decode("0"), 0)

    def test_uses_the_requested_digit_order(self):
        for value, expected in ((9, "9"), (10, "a"), (35, "z"), (36, "A"), (61, "Z"), (62, "10")):
            with self.subTest(value=value):
                self.assertEqual(encode(value), expected)
                self.assertEqual(decode(expected), value)

    def test_round_trips_values_across_digit_boundaries(self):
        for value in (1, 61, 62, 63, 3843, 3844, 2**128):
            with self.subTest(value=value):
                self.assertEqual(decode(encode(value)), value)

    def test_rejects_negative_and_non_integer_inputs(self):
        with self.assertRaises(ValueError):
            encode(-1)
        for value in (1.5, True, "12"):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    encode(value)

    def test_rejects_empty_and_invalid_encoded_values(self):
        for encoded in ("", "!", "abc_", "한"):
            with self.subTest(encoded=encoded):
                with self.assertRaises(ValueError):
                    decode(encoded)

    def test_rejects_non_string_encoded_values(self):
        with self.assertRaises(TypeError):
            decode(62)


if __name__ == "__main__":
    unittest.main()
