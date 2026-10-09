"""框架层离线测试（不依赖外网，也不依赖任何具体模块实现）。

运行：  cd backend && .venv\\Scripts\\python tests\\test_framework.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from checks import DIMENSIONS, CHECK_ID_RANGES, make_check
from modules import MODULES
from engine import build_report


def test_modules_registered():
    # 5 个模块都已注册，顺序正确
    assert len(MODULES) == 5, f"应注册 5 个模块，实际 {len(MODULES)}"
    names = [m.__name__.split(".")[-1] for m in MODULES]
    assert names == ["find", "see", "understand", "trust", "cite"], names
    print(f"[PASS] 5 个模块已注册：{', '.join(names)}")


def test_module_run_signature():
    # 每个模块都有 run 函数，且返回 list
    for m in MODULES:
        assert hasattr(m, "run"), f"{m.__name__} 缺少 run 函数"
        result = m.run(None)
        assert isinstance(result, list), f"{m.__name__}.run 应返回 list"
    print("[PASS] 所有模块 run 签名正确（返回 list）")


def test_id_ranges():
    # 30 项 ID 覆盖 1-30，无重叠、无遗漏
    all_ids = []
    for lo, hi in CHECK_ID_RANGES.values():
        all_ids.extend(range(lo, hi + 1))
    assert sorted(all_ids) == list(range(1, 31)), "ID 段应覆盖 1-30 且无重叠"
    print("[PASS] 30 项 ID 段覆盖 1-30 无重叠")


def test_dimensions():
    # 五维总分 = 100
    assert sum(d["max"] for d in DIMENSIONS) == 100
    assert len(DIMENSIONS) == 5
    print("[PASS] 五维总分 100")


def test_build_report():
    # 报告结构：5 维度 + 检查项；advice 项不计分
    checks = [
        make_check(1, 0, "good", "测试项", 2, 2, "ok", "fix"),
        make_check(9, 1, "advice", "建议项", None, None, "note", "fix"),
    ]
    report = build_report("example.com", checks)
    assert report["domain"] == "example.com"
    assert len(report["dimensions"]) == 5
    assert report["dimensions"][0]["score"] == 2   # dim0 计分 = 2
    assert report["dimensions"][1]["score"] == 0   # dim1 是 advice，不计分
    assert report["checks"] == checks
    print("[PASS] build_report 汇总正确（advice 不计分）")


if __name__ == "__main__":
    test_modules_registered()
    test_module_run_signature()
    test_id_ranges()
    test_dimensions()
    test_build_report()
    print("全部测试通过")
