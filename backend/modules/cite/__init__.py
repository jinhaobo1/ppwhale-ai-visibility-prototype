"""模块5：能被引用（20 分）——榜单、对比、指南与案例数据。

TODO：实现本维度的检查项（ID 27-30）：
  27 榜单与优选内容    28 对比与替代方案内容
  29 指南与教程内容    30 案例与数据内容

写法参考 modules/find/__init__.py：
  - 入口 run(context) -> list[dict]，只读 context，不自己抓取；
  - 需要发现候选页（榜单/对比/指南/案例）并验证内容证据（列表、表格、步骤、量化结果等）；
  - ID 必须落在 27-30（见 checks.CHECK_ID_RANGES["cite"]）。
"""

from checks import make_check

DIM = 4  # 维度下标（能被引用）


def run(context):
    # TODO: 发现并验证榜单/对比/指南/案例页面及其内容证据
    return []
