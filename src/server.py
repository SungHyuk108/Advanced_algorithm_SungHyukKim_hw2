"""HTTP service for the in-memory URL shortener."""

from __future__ import annotations

import argparse
import html
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qsl, quote, urlsplit

from src.hash_table import HashTable, LinearProbingHashTable
from src.shortener import URLShortener

MAX_REQUEST_BODY = 8192
HOST = "0.0.0.0"
LINEAR_DEMO_URLS = (
    "https://linear-demo.example/5",
    "https://linear-demo.example/10",
    "https://linear-demo.example/18",
    "https://linear-demo.example/21",
)


def _render_page(title: str, content: str) -> str:
    escaped_title = html.escape(title)
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escaped_title}</title>
  <style>
    body {{ font: 16px/1.5 sans-serif; margin: 2rem auto; max-width: 1000px; padding: 0 1rem; }}
    nav {{ display: flex; gap: 1rem; margin-bottom: 1.5rem; }}
    input[type=url] {{ box-sizing: border-box; max-width: 42rem; padding: .6rem; width: 100%; }}
    button {{ cursor: pointer; margin-top: .75rem; padding: .6rem 1rem; }}
    code {{ overflow-wrap: anywhere; }}
    .bucket {{ border: 1px solid #bbb; margin: .75rem 0; padding: .75rem; }}
    .bucket h2 {{ font-size: 1rem; margin: 0 0 .75rem; }}
    .chain {{ align-items: stretch; display: flex; flex-wrap: wrap; gap: .5rem; }}
    .node {{ border: 1px solid #667; border-radius: .4rem; max-width: 28rem; padding: .75rem; }}
    .node p {{ margin: .35rem 0; }}
    .arrow {{ align-self: center; font-size: 1.4rem; }}
    .empty {{ color: #666; }}
    ol {{ overflow-wrap: anywhere; }}
  </style>
</head>
<body>
  <nav>
    <a href="/">URL 줄이기</a>
    <a href="/table">해시 테이블</a>
    <a href="/table/linear" target="_blank" rel="noopener">선형 탐지 보기 (새 창)</a>
  </nav>
  <main>
    <h1>{escaped_title}</h1>
    {content}
  </main>
</body>
</html>
"""


def _send_html(
    handler: BaseHTTPRequestHandler,
    status: int,
    title: str,
    content: str,
) -> None:
    body = _render_page(title, content).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _send_redirect(handler: BaseHTTPRequestHandler, url: str) -> None:
    location = quote(url, safe=":/?#[]@!$&'()*+,;=%")
    handler.send_response(302)
    handler.send_header("Location", location)
    handler.send_header("Content-Length", "0")
    handler.end_headers()


def _append_probe_trace(
    output: list[str],
    table: LinearProbingHashTable,
    key: str,
) -> None:
    start = table.bucket_index(key)
    output.extend(
        (
            "<details>",
            "<summary>조사한 칸과 선형 탐지 계산 근거</summary>",
            f"<p>시작 칸 h = {start}; 검사 순서: (시작 칸 + 이동 횟수) % 용량</p>",
            "<ol>",
        )
    )
    for offset, (slot, stored_key) in enumerate(table.probe_trace(key)):
        if stored_key is None:
            reason = "빈 칸에 도달"
        elif stored_key == key:
            reason = "대상 키 발견"
        else:
            reason = f"충돌: <code>{html.escape(stored_key)}</code>가 있어 다음 칸 검사"
        output.append(
            "<li>"
            f"({start} + {offset}) % {table.capacity} = {slot}: {reason}"
            "</li>"
        )
    output.extend(("</ol>", "</details>"))


def _table_page(
    table: HashTable | LinearProbingHashTable,
    short_link_prefix: str = "/",
) -> str:
    linear_table = table if isinstance(table, LinearProbingHashTable) else None
    output = []
    if linear_table is None:
        output.append(
            '<p><a href="/table/linear" target="_blank" rel="noopener">'
            "분리된 선형 탐지 데모 테이블을 새 창에서 보기</a></p>"
        )
        output.append("<p>버킷의 노드는 연결 리스트 순서이며, 화살표는 다음 노드입니다.</p>")
    else:
        output.append(
            "<p>이 화면은 개별 체이닝 테이블과 별도의 선형 탐지 테이블입니다. "
            "Horner 시작 칸부터 빈 칸이나 키를 찾을 때까지 다음 슬롯을 검사합니다.</p>"
        )

    for bucket_index in range(table.capacity):
        nodes = table.bucket_items(bucket_index)
        output.append(
            f'<section class="bucket"><h2>칸 {bucket_index}</h2>'
        )
        if not nodes:
            output.append('<span class="empty">비어 있음</span></section>')
            continue

        if linear_table is None:
            output.append('<div class="chain">')
        for node_index, (url, stored_code) in enumerate(nodes):
            if not isinstance(stored_code, str):
                raise RuntimeError("URL index contains a non-string short code")
            code = html.escape(stored_code, quote=True)
            short_link = html.escape(f"{short_link_prefix}{stored_code}", quote=True)
            safe_url = html.escape(url)
            output.extend(
                (
                    '<article class="node">',
                    f"<h3>노드 {node_index + 1}</h3>",
                    f"<p><strong>URL 키:</strong> <code>{safe_url}</code></p>",
                    f"<p><strong>짧은 코드:</strong> <code>{code}</code></p>",
                    f'<p><strong>짧은 링크:</strong> '
                    f'<a href="{short_link}">{short_link}</a></p>',
                    "<details>",
                    "<summary>Horner 해시 계산 과정</summary>",
                    f"<p>초깃값 h = 0, 용량 = {table.capacity}</p>",
                    "<ol>",
                )
            )
            previous_hash = 0
            for character, code_point, accumulated in table.hash_trace(url):
                safe_character = html.escape(character)
                output.append(
                    "<li>"
                    f"h = ({previous_hash} * 31 + ord('{safe_character}') "
                    f"[{code_point}]) % {table.capacity} = {accumulated}"
                    "</li>"
                )
                previous_hash = accumulated
            output.extend(("</ol>", "</details>"))
            if linear_table is None:
                output.append("</article>")
                if node_index + 1 < len(nodes):
                    output.append('<span class="arrow" aria-label="다음 노드">→</span>')
                else:
                    output.append('<span class="arrow">→ ∅</span>')
            else:
                _append_probe_trace(output, linear_table, url)
                output.append("</article>")
        if linear_table is None:
            output.append("</div>")
        output.append("</section>")
    return "\n".join(output)


def _make_linear_demo_shortener() -> URLShortener:
    shortener = URLShortener(table_type=LinearProbingHashTable)
    for url in LINEAR_DEMO_URLS:
        shortener.shorten(url)
    return shortener


def make_handler(
    shortener: URLShortener,
    linear_shortener: URLShortener | None = None,
) -> type[BaseHTTPRequestHandler]:
    """Create a handler with separate primary and linear-demo shorteners."""
    if linear_shortener is None:
        linear_shortener = _make_linear_demo_shortener()
    if linear_shortener is shortener:
        raise ValueError("the primary and linear shorteners must be separate")
    if not isinstance(linear_shortener.url_table, LinearProbingHashTable):
        raise TypeError("linear_shortener must use LinearProbingHashTable")

    class ShortenerRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            path = urlsplit(self.path).path
            if path == "/":
                content = """
<form method="post" action="/shorten">
  <label for="url">줄일 URL</label><br>
  <input id="url" name="url" type="url" required>
  <br><button type="submit">줄이기</button>
</form>
"""
                _send_html(self, 200, "URL 단축기", content)
                return

            if path == "/table":
                content = _table_page(shortener.url_table)
                _send_html(self, 200, "해시 테이블", content)
                return

            if path == "/table/linear":
                content = """
<form method="post" action="/linear/shorten">
  <label for="linear-url">선형 탐지 테이블에 URL 추가</label><br>
  <input id="linear-url" name="url" type="url" required>
  <br><button type="submit">선형 테이블에 줄이기</button>
</form>
"""
                content += _table_page(
                    linear_shortener.url_table,
                    short_link_prefix="/linear/",
                )
                _send_html(self, 200, "선형 탐지 해시 테이블", content)
                return

            if path.startswith("/linear/"):
                code = path[len("/linear/") :]
                if not code or "/" in code:
                    _send_html(self, 404, "찾을 수 없음", "<p>짧은 링크가 없습니다.</p>")
                    return
                try:
                    original_url = linear_shortener.expand(code)
                except KeyError:
                    _send_html(self, 404, "찾을 수 없음", "<p>짧은 링크가 없습니다.</p>")
                    return
                if not isinstance(original_url, str):
                    raise RuntimeError("linear code index contains a non-string URL")
                _send_redirect(self, original_url)
                return

            if not path.startswith("/") or path.count("/") != 1 or len(path) == 1:
                _send_html(self, 404, "찾을 수 없음", "<p>짧은 링크가 없습니다.</p>")
                return

            code = path[1:]
            try:
                original_url = shortener.expand(code)
            except KeyError:
                _send_html(self, 404, "찾을 수 없음", "<p>짧은 링크가 없습니다.</p>")
                return
            if not isinstance(original_url, str):
                raise RuntimeError("code index contains a non-string URL")

            _send_redirect(self, original_url)

        def do_POST(self) -> None:
            path = urlsplit(self.path).path
            if path == "/shorten":
                target_shortener = shortener
                short_link_prefix = "/"
            elif path == "/linear/shorten":
                target_shortener = linear_shortener
                short_link_prefix = "/linear/"
            else:
                _send_html(self, 404, "찾을 수 없음", "<p>요청한 경로가 없습니다.</p>")
                return

            content_length = self.headers.get("Content-Length")
            try:
                body_length = int(content_length) if content_length is not None else -1
            except ValueError:
                body_length = -1
            if body_length < 0:
                _send_html(self, 400, "잘못된 요청", "<p>요청 본문 길이가 올바르지 않습니다.</p>")
                return
            if body_length > MAX_REQUEST_BODY:
                _send_html(self, 413, "요청이 너무 큼", "<p>URL 입력이 너무 깁니다.</p>")
                return

            try:
                raw_body = self.rfile.read(body_length)
                if len(raw_body) != body_length:
                    _send_html(
                        self,
                        400,
                        "잘못된 요청",
                        "<p>요청 본문이 끝까지 전달되지 않았습니다.</p>",
                    )
                    return
                body = raw_body.decode("utf-8")
                fields = parse_qsl(body, keep_blank_values=True, max_num_fields=32)
            except (UnicodeDecodeError, ValueError):
                _send_html(self, 400, "잘못된 요청", "<p>폼 입력을 읽을 수 없습니다.</p>")
                return

            url = next((value for name, value in fields if name == "url"), None)
            if url is None:
                _send_html(self, 400, "잘못된 요청", "<p>URL을 입력해 주세요.</p>")
                return
            try:
                code = target_shortener.shorten(url)
            except ValueError:
                _send_html(
                    self,
                    400,
                    "잘못된 URL",
                    "<p>http 또는 https URL과 호스트 이름을 입력해 주세요.</p>",
                )
                return

            escaped_url = html.escape(url)
            short_link = html.escape(f"{short_link_prefix}{code}", quote=True)
            content = (
                f"<p>원래 URL: <code>{escaped_url}</code></p>"
                f'<p>짧은 링크: <a href="{short_link}">{short_link}</a></p>'
                '<p><a href="/">다른 URL 줄이기</a></p>'
            )
            _send_html(self, 200, "단축 결과", content)

    return ShortenerRequestHandler


def serve(port: int = 8000, table_mode: str = "chaining") -> None:
    if table_mode == "linear":
        table_type = LinearProbingHashTable
    elif table_mode == "chaining":
        table_type = HashTable
    else:
        raise ValueError("table_mode must be 'chaining' or 'linear'")
    shortener = URLShortener(table_type=table_type)
    server = HTTPServer((HOST, port), make_handler(shortener))
    print(
        f"URL shortener listening on http://{HOST}:{server.server_port} "
        f"with {table_mode} table"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the URL shortener HTTP service.")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--table",
        choices=("chaining", "linear"),
        default="chaining",
        help="table implementation used by the shortener",
    )
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("--port must be between 0 and 65535")
    serve(args.port, args.table)


if __name__ == "__main__":
    main()
