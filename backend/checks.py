"""五维评分框架 + 检查项契约（固定，所有模块共用）。

这里是「契约」：维度定义、30 项固定 ID 分配、检查项字段结构。
合作者写模块时，必须用 make_check() 构造结果、用各自维度的 ID 段，避免互相冲突。
"""

# 五个维度，总 100 分
DIMENSIONS = [
    {"key": "find",       "name": "能被找到", "max": 10, "label": "抓取、索引、站点地图与 URL"},
    {"key": "see",        "name": "能被看见", "max": 30, "label": "正文读取、标题与内容结构"},
    {"key": "understand", "name": "能被理解", "max": 25, "label": "品牌、网站与页面结构化标记"},
    {"key": "trust",      "name": "能被信任", "max": 15, "label": "公司、联系、合规与署名信息"},
    {"key": "cite",       "name": "能被引用", "max": 20, "label": "榜单、对比、指南与案例数据"},
]

# 每个维度的固定 ID 段（30 项全部分配好，合作者只能用自己的段）
# 能被找到: 1-8 | 能被看见: 9-16 | 能被理解: 17-21 | 能被信任: 22-26 | 能被引用: 27-30
CHECK_ID_RANGES = {
    "find":       (1, 8),
    "see":        (9, 16),
    "understand": (17, 21),
    "trust":      (22, 26),
    "cite":       (27, 30),
}

# 检查状态 → 展示文案
STATUS_NAME = {
    "good":   "通过",
    "warn":   "部分满足",
    "bad":    "问题",
    "advice": "建议项",
}


def make_check(cid, dim, status, title, score, mx, impact, fix,
               evidence=None, priority="", scope=""):
    """构造一个检查项结果（字段契约，前端渲染依赖这些字段）。

    - cid：全局唯一 ID（用自己维度的 ID 段）
    - dim：维度下标 0-4
    - score/mx 传 None 表示「建议项」不计分
    """
    return {
        "id": cid, "dim": dim, "status": status, "title": title,
        "priority": priority, "score": score, "max": mx,
        "impact": impact, "fix": fix, "scope": scope,
        "evidence": evidence or [],
    }
