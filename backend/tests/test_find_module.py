"""find 模块的离线单元测试（不依赖外网，用模拟 context）。

运行：  cd backend && .venv\\Scripts\\python tests\\test_find_module.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from context import ScanContext, ParsedPage, RobotsInfo, SitemapInfo, LlmsInfo
from modules import find


def _mock_context():
    home = ParsedPage(
        url="https://example.com/", status=200, final_url="https://example.com/",
        title="Example", meta_desc="desc", h1_count=1, text_len=2000,
        schemas=["Organization"], canonical="https://example.com/",
    )
    about = ParsedPage(
        url="https://example.com/about", status=200, final_url="https://example.com/about",
        title="About", text_len=500, canonical="https://example.com/about",
    )
    robots = RobotsInfo(url="https://example.com/robots.txt", status=200, found=True, allows_root=True)
    sitemap = SitemapInfo(found=True, urls=["https://example.com/", "https://example.com/about"])
    llms = LlmsInfo(found=True, status=200)
    return ScanContext(domain="example.com", home=home, robots=robots,
                       sitemap=sitemap, llms=llms, pages=[home, about])


def test_find_module():
    checks = find.run(_mock_context())

    # 1. 应返回 8 项，ID 依次为 1-8
    assert len(checks) == 8, f"应返回 8 项，实际 {len(checks)}"
    assert [c["id"] for c in checks] == [1, 2, 3, 4, 5, 6, 7, 8]

    # 2. 所有项都属于维度 0
    assert all(c["dim"] == 0 for c in checks)

    # 3. 计分项总和不超过维度满分 10
    total = sum(c["score"] for c in checks if c["score"] is not None)
    assert total <= 10, f"计分总和 {total} 超过 10"

    # 4. advice 项（5、8）score/max 为 None
    advice = [c for c in checks if c["status"] == "advice"]
    assert all(c["score"] is None and c["max"] is None for c in advice)

    # 5. 字段契约完整
    required = {"id", "dim", "status", "title", "priority", "score", "max",
                "impact", "fix", "scope", "evidence"}
    assert all(required <= set(c.keys()) for c in checks)

    print(f"[PASS] find 模块测试通过：8 项，总分 {total}/10，ID 1-8 正确")


if __name__ == "__main__":
    test_find_module()
    print("全部测试通过")
