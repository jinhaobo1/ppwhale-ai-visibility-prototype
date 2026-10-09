"""see 模块离线测试（不依赖外网）。

运行：  cd backend && .venv\\Scripts\\python tests\\test_see_module.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from context import ScanContext, ParsedPage
from modules.see import run as see_run


def _page(url, title, text_len):
    return ParsedPage(url=url, status=200, final_url=url,
                      title=title, meta_desc=f"{title} 的描述", h1_count=1,
                      text_len=text_len, list_count=5, table_count=1,
                      internal_links=10, strong_count=5, time_elems=1,
                      p_count=8, dl_count=1, question_headings=2,
                      visible_date=True, jsonld_dates=["2024-01-01"])


def _ctx():
    home = _page("https://example.com/", "首页", 1200)
    about = _page("https://example.com/about", "关于我们", 900)
    return ScanContext(domain="example.com", pages=[home, about])


def test_ids_and_count():
    checks = see_run(_ctx())
    ids = [c["id"] for c in checks]
    assert ids == list(range(9, 17)), f"see 应返回 ID 9-16，实际 {ids}"
    print("[PASS] see 返回 8 项，ID 9-16")


def test_score_bounds():
    checks = see_run(_ctx())
    total = 0
    for c in checks:
        assert c["score"] is not None, f"see 无建议项，ID {c['id']} 不应为 None"
        assert 0 <= c["score"] <= c["max"], f"ID {c['id']} 分数越界"
        total += c["score"]
    assert total <= 30, f"see 总分应 ≤ 30，实际 {total}"
    print(f"[PASS] see 计分合法，总分 {total}/30")


def test_empty_context():
    checks = see_run(ScanContext(domain="example.com", pages=[]))
    assert len(checks) == 8, "空 context 也应返回 8 项"
    assert all(c["score"] == 0 for c in checks), "空 context 下应全部 0 分"
    print("[PASS] see 空 context 仍返回 8 项（0 分）")


if __name__ == "__main__":
    test_ids_and_count()
    test_score_bounds()
    test_empty_context()
    print("see 模块测试全部通过")
