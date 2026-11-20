import unittest

from src.hash_table import HashTable
from src.shortener import URLShortener


class URLShortenerTests(unittest.TestCase):
    def test_shortens_and_expands_urls(self):
        shortener = URLShortener()
        code = shortener.shorten("https://example.com/path?q=1")
        self.assertEqual(code, "0")
        self.assertEqual(shortener.expand(code), "https://example.com/path?q=1")

    def test_same_url_gets_same_code(self):
        shortener = URLShortener()
        first = shortener.shorten("https://example.com/")
        second = shortener.shorten("https://example.com/")
        self.assertEqual(first, second)

    def test_next_url_gets_next_base62_code(self):
        shortener = URLShortener()
        self.assertEqual(shortener.shorten("https://one.example/"), "0")
        self.assertEqual(shortener.shorten("https://two.example/"), "1")

    def test_rejects_invalid_urls(self):
        shortener = URLShortener()
        for url in ("", "ftp://example.com/", "https://", " http://example.com", "http://"):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    shortener.shorten(url)

    def test_unknown_code_raises_key_error(self):
        with self.assertRaises(KeyError):
            URLShortener().expand("unknown")

    def test_uses_the_supplied_table_implementation(self):
        shortener = URLShortener(table_type=HashTable)
        code = shortener.shorten("http://example.org/")
        self.assertEqual(shortener.expand(code), "http://example.org/")


if __name__ == "__main__":
    unittest.main()
