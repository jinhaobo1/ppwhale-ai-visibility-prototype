"""维度 4（能被信任）离线测试：用假数据验证 5 个检查项的离散判定。

运行：  cd backend && .venv\\Scripts\\python tests\\test_trust_module.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from context import ScanContext, ParsedPage
from modules import trust

DIM = 3


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


def test_complete_site():
    """全齐站点：5 项满分 15。"""
    home = _page("https://example.com/", title="Example — 官网",
                 og_site_name="Example",
                 jsonld=[{"@type": "Organization", "name": "Example",
                          "url": "https://example.com/",
                          "logo": "https://example.com/logo.png",
                          "sameAs": ["https://x.com/example",
                                     "https://weibo.com/example"]}],
                 external_links=["https://x.com/example"])
    about = _page("https://example.com/about", text_len=800,
                  emails=["hi@example.com"])
    contact = _page("https://example.com/contact", text_len=600,
                    phones=["+1-555-0100"])
    privacy = _page("https://example.com/privacy", text_len=400)
    terms = _page("https://example.com/terms", text_len=400)
    blog = _page("https://example.com/blog/post-1", time_elems=1, author_elems=1)
    ctx = _ctx([home, about, contact, privacy, terms, blog])
    checks = trust.run(ctx)
    s = _scores(checks)
    assert s == {22: 4, 23: 3, 24: 2, 25: 3, 26: 3}, s
    print("[PASS] 全齐站点：22=4 23=3 24=2 25=3 26=3（合计 15）")


def test_empty_site():
    """无信任要素站点：全部 0 分，仍逐项返回。"""
    home = _page("https://example.com/")
    checks = trust.run(_ctx([home]))
    s = _scores(checks)
    assert len(checks) == 5
    assert s == {22: 0, 23: 0, 24: 0, 25: 0, 26: 0}, s
    print("[PASS] 空站点：5 项全部 0 分且逐项返回")


def test_partial_site():
    """部分满足：验证各离散档位。"""
    home = _page("https://example.com/", title="Example — 官网",
                 jsonld=[{"@type": "Organization", "name": "Acme Ltd",
                          "url": "https://example.com/"}],
                 external_links=["https://x.com/example"])
    privacy = _page("https://example.com/privacy", text_len=400)
    blog = _page("https://example.com/blog/post-1", author_elems=1)
    ctx = _ctx([home, privacy, blog],
               discovered=["https://example.com/contact"])
    checks = trust.run(ctx)
    s = _scores(checks)
    # 22：名称不一致、缺 logo、缺 og:site_name → 1 分 bad
    # 23：仅发现 contact 链接未验证 → 1 分 warn
    # 24：隐私可读、条款缺失 → 1 分 warn
    # 25：文章有作者无日期 → 0 分 bad
    # 26：仅页面链接无 sameAs → 1 分 warn
    assert s == {22: 1, 23: 1, 24: 1, 25: 0, 26: 1}, s
    assert sum(s.values()) <= 15
    print(f"[PASS] 部分满足站点：{s}（离散判定正确）")


def test_home_only_contact():
    """首页含联系方式但无独立联系页：23 项应 warn 2 分。"""
    home = _page("https://example.com/", text_len=3000,
                 emails=["hi@example.com"], phones=["+1-555-0100"])
    checks = trust.run(_ctx([home]))
    s = _scores(checks)
    assert s[23] == 2, s
    print("[PASS] 首页含联系方式：23=2（warn）")


def test_contract():
    """契约：ID 落在 22-26，dim=3，分数不超过上限，run(None) 返回空列表。"""
    assert trust.run(None) == []
    home = _page("https://example.com/")
    checks = trust.run(_ctx([home]))
    for c in checks:
        assert 22 <= c["id"] <= 26, c["id"]
        assert c["dim"] == DIM
        assert c["score"] is None or 0 <= c["score"] <= c["max"]
    assert sum(c["score"] or 0 for c in checks) <= 15
    print("[PASS] 契约检查：ID/维度/分数上限均合规")


if __name__ == "__main__":
    test_contract()
    test_empty_site()
    test_partial_site()
    test_home_only_contact()
    test_complete_site()
    print("test_trust_module 全部通过")
