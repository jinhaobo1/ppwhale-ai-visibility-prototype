"""框架主循环：规范化 → 抓取上下文 → 调用所有模块 → 汇总报告。

合作者不需要碰这个文件。它把各个模块（modules/ 下的 5 个维度）产出的
检查项汇总成前端需要的完整报告结构。
"""

from checks import DIMENSIONS
from crawler import crawl, normalize
from modules import MODULES


def build_report(domain: str, checks: list[dict]) -> dict:
    """把检查项按维度汇总成报告（五维分数 + 检查项）。"""
    dim_scores = [0] * len(DIMENSIONS)
    for c in checks:
        if c["score"] is not None:
            dim_scores[c["dim"]] += c["score"]

    dimensions = [
        {
            "name": d["name"],
            "score": dim_scores[i],
            "max": d["max"],
            "label": d["label"],
        }
        for i, d in enumerate(DIMENSIONS)
    ]
    return {"domain": domain, "dimensions": dimensions, "checks": checks}


async def analyze(raw_url: str) -> dict:
    """入口：规范化 → 抓取 → 各模块打分 → 汇总报告。"""
    domain = normalize(raw_url)
    context = await crawl(domain)
    checks: list[dict] = []
    for mod in MODULES:
        checks.extend(mod.run(context))
    return build_report(domain, checks)
