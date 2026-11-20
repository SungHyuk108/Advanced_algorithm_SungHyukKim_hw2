"""URL shortening backed by the repository's hash table."""

from urllib.parse import urlsplit

from src.base62 import encode
from src.hash_table import HashTable, LinearProbingHashTable


class URLShortener:
    def __init__(
        self,
        table_type: type[HashTable] | type[LinearProbingHashTable] = HashTable,
    ):
        self._urls_to_codes = table_type()
        self._codes_to_urls = table_type()
        self._next_id = 0

    @property
    def code_table(self) -> HashTable | LinearProbingHashTable:
        return self._codes_to_urls

    @property
    def url_table(self) -> HashTable | LinearProbingHashTable:
        return self._urls_to_codes

    @staticmethod
    def _validate_url(url: str) -> None:
        if not isinstance(url, str) or not url or any(
            character.isspace() or ord(character) < 32 or ord(character) == 127
            for character in url
        ):
            raise ValueError("url must be a non-empty URL without whitespace")
        try:
            parsed = urlsplit(url)
            valid_port = parsed.port
        except ValueError as error:
            raise ValueError("url has an invalid authority") from error
        if parsed.scheme.lower() not in ("http", "https") or not parsed.hostname:
            raise ValueError("url must have an http or https scheme and a host")
        if valid_port is not None and not 0 <= valid_port <= 65535:
            raise ValueError("url port is out of range")

    def shorten(self, url: str) -> str:
        self._validate_url(url)
        if self._urls_to_codes.contains_key(url):
            return self._urls_to_codes.get(url)

        code = encode(self._next_id)
        self._next_id += 1
        self._urls_to_codes.put(url, code)
        self._codes_to_urls.put(code, url)
        return code

    def expand(self, code: str) -> str:
        return self._codes_to_urls.get(code)
