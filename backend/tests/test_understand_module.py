"""维度 3（能被理解）离线测试：用假数据验证 5 个检查项的离散判定。

运行：  cd backend && .venv\\Scripts\\python tests\\test_understand_module.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from context import ScanContext, ParsedPage
from modules import understand

DIM = 2


def _page(url, **kw):
    d = dict(status=200, final_url=url, title="", meta_desc="", h1_count=1,
             h2_count=3, text_len=2000, schemas=[], canonical=None, og_url=None,
             noindex=False, nosnippet=False, list_count=0, table_count=0,
             internal_links=0, strong_count=0, time_elems=0, author_elems=0,
             jsonld=[], jsonld_errors=0, og_site_name=None, emails=[],
             phones=[], external_links=[])
    d.update(kw)
    d["url"] = url
    return ParsedPage(**d)


def _ctx(pages, domain="example.com", discovered=None):
    return ScanContext(domain=domain, home=(pages[0] if pages else None),
                       pages=pages, discovered_urls=discovered or [])


def _scores(checks):
    return {c["id"]: c["score"] for c in checks}


def _crumb(items):
    return {"@type": "BreadcrumbList", "itemListElement": items}


def _li(name, url):
    return {"@type": "ListItem", "position": 1, "name": name, "item": url}


def test_complete_site():
    """全齐站点：5 项满分 25。"""
    home = _page("https://example.com/", jsonld=[
        {"@type": "Organization", "name": "Example 公司",
         "url": "https://example.com/",
         "logo": {"@type": "ImageObject", "url": "https://example.com/logo.png"},
         "contactPoint": {"@type": "ContactPoint", "telephone": "+1-555-0100"}},
        {"@type": "WebSite", "name": "Example", "url": "https://example.com/",
         "potentialAction": {"@type": "SearchAction",
                             "target": "https://example.com/search?q={search_term_string}"}},
    ])
    blog = _page("https://example.com/blog/post-1", jsonld=[
        _crumb([_li("首页", "https://example.com/"),
                _li("博客", "https://example.com/blog"),
                _li("文章1", "https://example.com/blog/post-1")]),
        {"@type": "BlogPosting", "headline": "文章1",
         "datePublished": "2025-01-01",
         "author": {"@type": "Person", "name": "张三"}},
    ])
    product = _page("https://example.com/products/x", jsonld=[
        _crumb([_li("首页", "https://example.com/"),
                _li("产品", "https://example.com/products"),
                _li("X", "https://example.com/products/x")]),
        {"@type": "Product", "name": "X"},
    ])
    faq = _page("https://example.com/faq", jsonld=[
        {"@type": "FAQPage", "mainEntity": []},
    ])
    ctx = _ctx([home, blog, product, faq])
    checks = understand.run(ctx)
    s = _scores(checks)
    assert s == {17: 5, 18: 4, 19: 4, 20: 8, 21: 4}, s
    print("[PASS] 全齐站点：17=5 18=4 19=4 20=8 21=4（合计 25）")


def test_empty_site():
    """无结构化数据站点：全部 0 分，但仍逐项返回。"""
    home = _page("https://example.com/")
    ctx = _ctx([home])
    checks = understand.run(ctx)
    s = _scores(checks)
    assert len(checks) == 5
    assert s == {17: 0, 18: 0, 19: 0, 20: 0, 21: 0}, s
    print("[PASS] 空站点：5 项全部 0 分且逐项返回")


def test_partial_site():
    """缺字段站点：验证各离散档位。"""
    home = _page("https://example.com/", jsonld=[
        {"@type": "Organization", "name": "Example", "url": "https://example.com/"},
        {"@type": "WebSite", "name": "Example"},
    ], jsonld_errors=2)
    blog = _page("https://example.com/blog/post-9", jsonld=[
        # 面包屑缺 URL（item 为空）→ 无效
        {"@type": "BreadcrumbList",
         "itemListElement": [{"@type": "ListItem", "name": "首页"}]},
    ])
    ctx = _ctx([home, blog])
    checks = understand.run(ctx)
    s = _scores(checks)
    # 17：实体+名称+URL=3 分（缺 logo/联系方式）；18：仅名称=2；19：有但无效=1；
    # 20：1 个文章页无 BlogPosting=0；21：失败 2/5 → 0
    assert s[17] == 3 and s[18] == 2 and s[19] == 1, s
    assert s[20] == 0 and s[21] == 0, s
    assert sum(s.values()) <= 25
    print(f"[PASS] 缺字段站点：{s}（离散判定正确）")


def test_at_graph_flattened():
    """@graph 摊平后的数据（模拟解析器输出）：WebSite 在 @graph 中也能识别。"""
    home = _page("https://example.com/", jsonld=[
        {"@type": "WebSite", "name": "Example", "url": "https://example.com/",
         "potentialAction": {"@type": "SearchAction",
                             "target": "https://example.com/s?q={search_term_string}"}},
        {"@type": "Organization", "name": "Example"},
    ])
    checks = understand.run(_ctx([home]))
    s = _scores(checks)
    assert s[18] == 4, s
    print("[PASS] @graph 摊平：WebSite 标记识别正常")


def test_contract():
    """契约：ID 落在 17-21，dim=2，分数不超过上限，run(None) 返回空列表。"""
    assert understand.run(None) == []
    home = _page("https://example.com/")
    checks = understand.run(_ctx([home]))
    for c in checks:
        assert 17 <= c["id"] <= 21, c["id"]
        assert c["dim"] == DIM
        assert c["score"] is None or 0 <= c["score"] <= c["max"]
    assert sum(c["score"] or 0 for c in checks) <= 25
    print("[PASS] 契约检查：ID/维度/分数上限均合规")


if __name__ == "__main__":
    test_contract()
    test_empty_site()
    test_partial_site()
    test_at_graph_flattened()
    test_complete_site()
    print("test_understand_module 全部通过")
