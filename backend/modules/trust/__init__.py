"""模块4：能被信任（15 分）——公司、联系、合规与署名信息。

TODO：实现本维度的检查项（ID 22-26）：
  22 品牌信息完整性    23 公司与联系页面    24 隐私与服务条款
  25 文章署名与日期    26 官方账号关联

写法参考 modules/find/__init__.py：
  - 入口 run(context) -> list[dict]，只读 context，不自己抓取；
  - 部分检查项需要发现并抓取公司/联系/隐私等特定页面（可在本模块内做，但建议
    复用 context 已有的数据，必要时向框架申请扩展 crawler）；
  - ID 必须落在 22-26（见 checks.CHECK_ID_RANGES["trust"]）。
"""

from checks import make_check

DIM = 3  # 维度下标（能被信任）


def run(context):
    # TODO: 识别公司/联系/隐私页面、作者署名与日期、官方账号(sameAs)关联等
    return []
