"""模块1：能被找到（10 分）——抓取、索引、站点地图与 URL。

TODO：实现本维度的检查项（ID 1-8）：
  1 抓取规则文件    2 站点地图          3 规范地址一致性  4 页面可索引性
  5 页面可访问性    6 语义化 URL        7 HTTPS 交付      8 机器可读内容目录

实现参考 docs/spec.md（30 项规格）和 modules/README.md（开发指南）：
  - 入口 run(context) -> list[dict]，只读 context，不自己抓取；
  - 用 checks.make_check() 构造结果；
  - ID 必须落在 1-8（见 checks.CHECK_ID_RANGES["find"]）。
"""

from checks import make_check

DIM = 0  # 维度下标（能被找到）


def run(context):
    # TODO: 从 context 的 robots/sitemap/llms/home/pages 读数据，实现本维度检查项
    return []
