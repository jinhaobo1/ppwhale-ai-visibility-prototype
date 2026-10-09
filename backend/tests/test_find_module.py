"""find 模块离线测试（不依赖外网）。

运行：  cd backend && .venv\\Scripts\\python tests\\test_find_module.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from context import ScanContext, ParsedPage, RobotsInfo, SitemapInfo, LlmsInfo
from modules.find import run as find_run


def _ctx():
    home = ParsedPage(url="https://example.com/", status=200, final_url="https://example.com/",
                      title="Example", text_len=500,
                      canonical="https://example.com/", h1_count=1)
    about = ParsedPage(url="https://example.com/about", status=200, final_url="https://example.com/about",
                       title="About", text_len=300, canonical="https://example.com/about")
    return ScanContext(domain="example.com", home=home,
                       robots=RobotsInfo(url="https://example.com/robots.txt", status=200,
                                         found=True, allows_root=True),
                       sitemap=SitemapInfo(found=True, urls=["https://example.com/about"]),
                       llms=LlmsInfo(found=True, status=200),
                       pages=[home, about])


def test_ids_and_count():
    checks = find_run(_ctx())
    ids = [c["id"] for c in checks]
    assert ids == list(range(1, 9)), f"find 应返回 ID 1-8，实际 {ids}"
    print("[PASS] find 返回 8 项，ID 1-8")


def test_score_bounds_and_advice():
    checks = find_run(_ctx())
    total = 0
    for c in checks:
        if c["score"] is None:
            assert c["id"] in (5, 8), f"只有建议项(5/8)计分为 None，实际 {c['id']}"
        else:
            assert 0 <= c["score"] <= c["max"], f"ID {c['id']} 分数越界"
            total += c["score"]
    assert total <= 10, f"find 总分应 ≤ 10，实际 {total}"
    print(f"[PASS] find 计分合法，总分 {total}/10")


def test_empty_context():
    ctx = ScanContext(domain="example.com", pages=[])
    checks = find_run(ctx)
    assert len(checks) == 8, "空 context 也应返回 8 项"
    assert all(c["score"] is None or c["score"] <= c["max"] for c in checks)
    print("[PASS] find 空 context 仍返回 8 项")


if __name__ == "__main__":
    test_ids_and_count()
    test_score_bounds_and_advice()
    test_empty_context()
    print("find 模块测试全部通过")
