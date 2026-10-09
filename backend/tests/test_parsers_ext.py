"""解析器扩充字段离线测试（维度 3/4 依赖的新字段）。

运行：  cd backend && .venv\\Scripts\\python tests\\test_parsers_ext.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from parsers import _parse_page_html, _flatten_jsonld, _extract_phones


HTML = """<!DOCTYPE html>
<html><head>
<title>Example — 官网</title>
<meta property="og:site_name" content="Example">
<script type="application/ld+json">{
  "@context": "https://schema.org",
  "@graph": [
    {"@type": "Organization", "name": "Example"},
    {"@type": "WebSite", "name": "Example", "url": "https://example.com/"}
  ]
}</script>
<script type="application/ld+json">{"@type": "BreadcrumbList", "itemListElement": [
  {"@type": "ListItem", "position": 1, "name": "首页", "item": "https://example.com/"},
  {"@type": "ListItem", "position": 2, "name": "关于", "item": "https://example.com/about"}
]}</script>
<script type="application/ld+json">{ 坏掉的 json 段落 </script>
</head><body>
<h1>关于我们</h1>
<p>联系邮箱 hi@example.com，电话 +86 21 5550-0100，或 021-5550-0100。</p>
<a href="https://x.com/example">官方X</a>
<a href="/about">关于</a>
<a href="https://example.com/img.png">图片</a>
</body></html>
"""


def test_jsonld_flatten_and_errors():
    page = _parse_page_html("example.com", "https://example.com/", 200, HTML)
    types = set()
    for n in page.jsonld:
        t = n.get("@type")
        if isinstance(t, str):
            types.add(t)
    # @graph 内的 Organization/WebSite 被摊平；坏段落计为 1 次解析失败
    assert {"Organization", "WebSite", "BreadcrumbList"} <= types, types
    assert page.jsonld_errors == 1, page.jsonld_errors
    assert page.schemas, "schemas @type 列表应与旧口径一致"
    print("[PASS] JSON-LD：@graph 摊平 + 解析失败计数")


def test_og_site_name():
    page = _parse_page_html("example.com", "https://example.com/", 200, HTML)
    assert page.og_site_name == "Example"
    print("[PASS] og:site_name 解析正常")


def test_emails_phones_links():
    page = _parse_page_html("example.com", "https://example.com/", 200, HTML)
    assert page.emails == ["hi@example.com"], page.emails
    assert "+86 21 5550-0100" in page.phones, page.phones
    assert "021-5550-0100" in page.phones, page.phones
    # 站外链接：只收 x.com，过滤图片
    assert page.external_links == ["https://x.com/example"], page.external_links
    print("[PASS] 邮箱/电话/站外链接提取正常")


def test_phone_year_filter():
    phones = _extract_phones("成立于 2026-2027 年，电话 400-888-8888。")
    assert "2026-2027" not in phones, phones
    assert "400-888-8888" in phones, phones
    print("[PASS] 电话提取排除年份/日期")


def test_flatten_array_input():
    out = []
    _flatten_jsonld([{"@type": "A"}, {"@type": "B"}], out)
    assert [n["@type"] for n in out] == ["A", "B"]
    print("[PASS] JSON-LD 数组输入摊平正常")


if __name__ == "__main__":
    test_flatten_array_input()
    test_phone_year_filter()
    test_jsonld_flatten_and_errors()
    test_og_site_name()
    test_emails_phones_links()
    print("test_parsers_ext 全部通过")
