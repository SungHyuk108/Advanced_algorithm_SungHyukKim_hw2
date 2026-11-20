import http.client
import unittest
from http.server import HTTPServer
from threading import Thread
from urllib.parse import urlencode

from src.base62 import encode
from src.hash_table import LinearProbingHashTable
from src.server import (
    CHAIN_DEMO_URLS,
    LINEAR_DEMO_URLS,
    _seed_chaining_demo,
    make_handler,
)
from src.shortener import URLShortener


class ShortenerServerTests(unittest.TestCase):
    def setUp(self):
        self.shortener = URLShortener()
        self.server = HTTPServer(("127.0.0.1", 0), make_handler(self.shortener))
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.connection = http.client.HTTPConnection(host, port)

    def tearDown(self):
        self.connection.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def _request(self, method, path, body=None):
        headers = {}
        if body is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        self.connection.request(method, path, body=body, headers=headers)
        response = self.connection.getresponse()
        response_body = response.read().decode("utf-8")
        return response.status, dict(response.getheaders()), response_body

    def _shorten(self, url):
        return self._request("POST", "/shorten", urlencode({"url": url}))

    def test_home_form_and_short_link_redirect(self):
        status, headers, body = self._request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn('<form method="post" action="/shorten">', body)

        original_url = "https://example.com/path?q=1"
        status, _, body = self._shorten(original_url)
        self.assertEqual(status, 200)
        self.assertIn('<a href="/0">/0</a>', body)
        self.assertIn(original_url, body)

        status, headers, _ = self._request("GET", "/0")
        self.assertEqual(status, 302)
        self.assertEqual(headers["Location"], original_url)

    def test_invalid_url_and_unknown_code_return_errors(self):
        status, _, _ = self._shorten("ftp://example.com/path")
        self.assertEqual(status, 400)

        status, _, _ = self._request("GET", "/missing")
        self.assertEqual(status, 404)

    def test_table_shows_chained_nodes_links_and_horner_trace_safely(self):
        first_url = "https://example.org/<script>"
        table = self.shortener.url_table
        target_bucket = table.bucket_index(first_url)
        second_url = None
        for number in range(10_000):
            candidate = f"https://example.org/{number}"
            if table.bucket_index(candidate) == target_bucket:
                second_url = candidate
                break
        self.assertIsNotNone(second_url)

        self.assertEqual(self._shorten(first_url)[0], 200)
        self.assertEqual(self._shorten(second_url)[0], 200)
        status, _, body = self._request("GET", "/table")

        self.assertEqual(status, 200)
        self.assertIn("&lt;script&gt;", body)
        self.assertNotIn("<script>", body)
        self.assertIn("Horner", body)
        self.assertIn("<details>", body)
        self.assertIn("→", body)
        self.assertIn('href="/0"', body)
        self.assertIn('href="/1"', body)
        self.assertIn('href="/table/linear"', body)
        self.assertIn('target="_blank"', body)

    def test_chaining_demo_shows_30_urls_and_real_bucket_collisions(self):
        _seed_chaining_demo(self.shortener)
        table = self.shortener.url_table
        bucket_lengths = [
            len(table.bucket_items(index)) for index in range(table.capacity)
        ]
        collision_bucket_count = sum(1 for length in bucket_lengths if length > 1)

        self.assertEqual(len(CHAIN_DEMO_URLS), 30)
        self.assertEqual(table.capacity, 64)
        self.assertEqual(len(table), 30)
        self.assertEqual(collision_bucket_count, 5)
        self.assertEqual(max(bucket_lengths), 2)

        status, _, chaining_page = self._request("GET", "/table")
        self.assertEqual(status, 200)
        self.assertIn("URL:</strong> 30개", chaining_page)
        self.assertIn("충돌 버킷:</strong> 5개", chaining_page)
        self.assertIn("최대 연결 길이:</strong> 2", chaining_page)
        self.assertIn("연결 리스트", chaining_page)
        self.assertIn("→", chaining_page)
        for demo_url in CHAIN_DEMO_URLS:
            self.assertIn(demo_url, chaining_page)

        linear_status, _, linear_page = self._request("GET", "/table/linear")
        self.assertEqual(linear_status, 200)
        for demo_url in CHAIN_DEMO_URLS:
            self.assertNotIn(demo_url, linear_page)

        chain_status, chain_headers, _ = self._request("GET", "/0")
        self.assertEqual(chain_status, 302)
        self.assertEqual(chain_headers["Location"], CHAIN_DEMO_URLS[0])

    def test_linear_table_is_separate_and_shows_all_slots_and_collision_paths(self):
        chain_url = "https://chain-only.example/"
        self.assertEqual(self._shorten(chain_url)[0], 200)
        status, _, chaining_page = self._request("GET", "/table")
        linear_status, _, linear_page = self._request("GET", "/table/linear")

        self.assertEqual(status, 200)
        self.assertEqual(linear_status, 200)
        self.assertIn("연결 리스트", chaining_page)
        self.assertIn(chain_url, chaining_page)
        self.assertEqual(len(LINEAR_DEMO_URLS), 30)
        for demo_url in LINEAR_DEMO_URLS:
            self.assertIn(demo_url, linear_page)
            self.assertNotIn(demo_url, chaining_page)
        self.assertNotIn(chain_url, linear_page)

        demo_table = LinearProbingHashTable()
        for demo_url in LINEAR_DEMO_URLS:
            demo_table.put(demo_url, demo_url)
        start_buckets = sorted(
            demo_table.bucket_index(demo_url) for demo_url in LINEAR_DEMO_URLS
        )
        unique_start_count = sum(
            1
            for index, bucket in enumerate(start_buckets)
            if index == 0 or bucket != start_buckets[index - 1]
        )
        probe_counts = [
            len(demo_table.probe_trace(demo_url)) for demo_url in LINEAR_DEMO_URLS
        ]
        self.assertEqual(unique_start_count, 25)
        self.assertEqual(sum(probes > 1 for probes in probe_counts), 6)
        self.assertEqual(max(probe_counts), 4)

        self.assertIn("용량:</strong> 64칸", linear_page)
        self.assertIn("적재율:</strong> 0.469", linear_page)
        self.assertEqual(linear_page.count('class="occupied-slot"'), 30)
        self.assertEqual(linear_page.count('class="empty-slot"'), 34)
        self.assertIn("시작 칸 25곳", linear_page)
        self.assertIn("시작 칸 중복은 5건", linear_page)
        self.assertIn("6개 URL은 충돌로", linear_page)
        self.assertIn("최대 검사 횟수는 4회", linear_page)
        self.assertIn("50 → 51 → 52", linear_page)
        self.assertIn("실제 조사 순서", linear_page)
        self.assertNotIn("<details>", linear_page)
        self.assertIn('href="/linear/0"', linear_page)
        self.assertIn('action="/linear/shorten"', linear_page)

        linear_status, linear_headers, _ = self._request("GET", "/linear/0")
        self.assertEqual(linear_status, 302)
        self.assertEqual(linear_headers["Location"], LINEAR_DEMO_URLS[0])
        chain_status, chain_headers, _ = self._request("GET", "/0")
        self.assertEqual(chain_status, 302)
        self.assertEqual(chain_headers["Location"], chain_url)

    def test_linear_form_shortens_and_redirects_without_touching_primary_table(self):
        linear_url = "https://linear-added.example/path"
        status, _, response_body = self._request(
            "POST",
            "/linear/shorten",
            urlencode({"url": linear_url}),
        )
        self.assertEqual(status, 200)
        code = encode(len(LINEAR_DEMO_URLS))
        self.assertIn(f'<a href="/linear/{code}">/linear/{code}</a>', response_body)

        status, headers, _ = self._request("GET", f"/linear/{code}")
        self.assertEqual(status, 302)
        self.assertEqual(headers["Location"], linear_url)
        status, _, chaining_page = self._request("GET", "/table")
        self.assertEqual(status, 200)
        self.assertNotIn(linear_url, chaining_page)
        status, _, linear_page = self._request("GET", "/table/linear")
        self.assertEqual(status, 200)
        self.assertIn(linear_url, linear_page)


if __name__ == "__main__":
    unittest.main()
