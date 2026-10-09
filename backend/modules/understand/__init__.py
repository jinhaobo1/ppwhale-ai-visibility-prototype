"""模块3：能被理解（25 分）——品牌、网站与页面结构化标记。

TODO：实现本维度的检查项（ID 17-21）：
  17 品牌实体标记      18 网站主体标记      19 面包屑标记
  20 代表页面专项标记  21 结构化数据有效性

写法参考 modules/find/__init__.py：
  - 入口 run(context) -> list[dict]，只读 context，不自己抓取；
  - 主要从 context.pages 里每个页面的 schemas（JSON-LD @type 列表）读取；
  - ID 必须落在 17-21（见 checks.CHECK_ID_RANGES["understand"]）。
"""

from checks import make_check

DIM = 2  # 维度下标（能被理解）


def run(context):
    # TODO: 解析 context.pages 里各页的 schemas，识别 Brand/Organization/WebSite/
    #       BreadcrumbList/BlogPosting 等类型，实现本维度检查项
    return []
