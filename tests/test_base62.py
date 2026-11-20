import unittest

from src.base62 import decode_base62, encode_base62


class Base62Tests(unittest.TestCase):
    def test_zero_is_encoded_as_zero_character(self):
        self.assertEqual(encode_base62(0), "0")
        self.assertEqual(decode_base62("0"), 0)

    def test_round_trips_values_across_digit_boundaries(self):
        for value in (1, 61, 62, 63, 3843, 3844, 2**128):
            with self.subTest(value=value):
                self.assertEqual(decode_base62(encode_base62(value)), value)

    def test_rejects_negative_and_non_integer_inputs(self):
        with self.assertRaises(ValueError):
            encode_base62(-1)
        for value in (1.5, True, "12"):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    encode_base62(value)

    def test_rejects_empty_and_invalid_encoded_values(self):
        for encoded in ("", "!", "abc_", "한"):
            with self.subTest(encoded=encoded):
                with self.assertRaises(ValueError):
                    decode_base62(encoded)

    def test_rejects_non_string_encoded_values(self):
        with self.assertRaises(TypeError):
            decode_base62(62)


if __name__ == "__main__":
    unittest.main()
