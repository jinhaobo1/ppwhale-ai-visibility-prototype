"""模块2：能被看见（30 分）——正文读取、标题与内容结构。

TODO：实现本维度的检查项（ID 9-16）：
  9  页面内容可读取    10 标题与摘要      11 主标题结构      12 正文信息深度
  13 段落与开篇信息    14 答案型内容结构  15 文章时间信息    16 正文内链与重点标记

实现参考 docs/spec.md 和 modules/README.md：
  - 入口 run(context) -> list[dict]，只读 context，不自己抓取；
  - 用 checks.make_check() 构造结果；
  - ID 必须落在 9-16（见 checks.CHECK_ID_RANGES["see"]）。
"""

from checks import make_check

DIM = 1  # 维度下标（能被看见）


def run(context):
    # TODO: 从 context.pages 读 title/meta_desc/h1_count/text_len 等字段，实现本维度检查项
    return []
