import http.client
import unittest
from http.server import HTTPServer
from threading import Thread
from urllib.parse import urlencode

from src.server import make_handler
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

    def test_linear_table_is_an_additional_view_with_probe_calculations(self):
        first_url = "https://example.org/linear-first"
        table = self.shortener.url_table
        initial_bucket = table.bucket_index(first_url)
        second_url = None
        for number in range(10_000):
            candidate = f"https://example.org/linear-{number}"
            if candidate != first_url and table.bucket_index(candidate) == initial_bucket:
                second_url = candidate
                break
        if second_url is None:
            self.fail("could not find a URL with the same initial bucket")

        self.assertEqual(self._shorten(first_url)[0], 200)
        self.assertEqual(self._shorten(second_url)[0], 200)
        status, _, chaining_page = self._request("GET", "/table")
        linear_status, _, linear_page = self._request("GET", "/table/linear")

        self.assertEqual(status, 200)
        self.assertEqual(linear_status, 200)
        self.assertIn("연결 리스트", chaining_page)
        self.assertIn("linear-first", linear_page)
        self.assertIn("Horner 해시 계산 과정", linear_page)
        self.assertIn("조사한 칸", linear_page)
        self.assertIn("(시작 칸 + 이동 횟수) % 용량", linear_page)
        self.assertIn("충돌", linear_page)


if __name__ == "__main__":
    unittest.main()
