"""五维评分框架（固定，总 100 分）。

这里是「维度」这个不变的结构；每个维度下的具体检查项在 analyzer.py 里实现。
MVP 先做单页能真实检测的项，其余留 TODO。
"""

# 五个维度，总 100 分
DIMENSIONS = [
    {"key": "find",       "name": "能被找到", "max": 10, "label": "发现与抓取信号"},
    {"key": "see",        "name": "能被看见", "max": 30, "label": "读取与内容结构"},
    {"key": "understand", "name": "能被理解", "max": 25, "label": "实体与结构化标记"},
    {"key": "trust",      "name": "能被信任", "max": 15, "label": "品牌与合规信息"},
    {"key": "cite",       "name": "能被引用", "max": 20, "label": "引用支持内容"},
]

# 检查状态 → 展示文案
STATUS_NAME = {
    "good":   "通过",
    "warn":   "部分满足",
    "bad":    "问题",
    "advice": "建议项",
}
