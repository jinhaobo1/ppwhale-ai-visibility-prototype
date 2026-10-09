# 模块开发指南（给合作者）

这个目录下是 5 个维度模块，每人负责一个。**只改你自己的文件夹**，不要碰 framework 层（`crawler.py` / `parsers.py` / `engine.py` / `context.py` / `checks.py`）。

## 分工

| 模块 | 文件夹 | 维度 | 分数 | 负责的检查项 ID |
|---|---|---|---|---|
| 能被找到 | `find/` | 抓取、索引、站点地图与 URL | 10 分 | 1–8 |
| 能被看见 | `see/` | 正文读取、标题与内容结构 | 30 分 | 9–16 |
| 能被理解 | `understand/` | 品牌、网站与页面结构化标记 | 25 分 | 17–21 |
| 能被信任 | `trust/` | 公司、联系、合规与署名信息 | 15 分 | 22–26 |
| 能被引用 | `cite/` | 榜单、对比、指南与案例数据 | 20 分 | 27–30 |

## 你唯一要写的东西

在你的文件夹的 `__init__.py` 里，写一个 `run(context)` 函数：

```python
from checks import make_check

DIM = 0  # 你的维度下标

def run(context):
    checks = []
    # 从 context 读数据 → 计算 → 用 make_check 构造结果
    return checks
```

**规则：**
1. 入口函数签名固定为 `run(context) -> list[dict]`，框架会自动调用；
2. **只读 `context`，不要自己抓取网页**（抓取是框架 `crawler.py` 的事）；
3. 用 `checks.make_check(...)` 构造每个检查项（字段契约见下）；
4. 检查项 ID 必须落在你自己维度的段内（见上表），避免和别人的冲突。

## context 里有什么（你能读的数据）

```python
context.domain           # 目标域名
context.home             # 首页 ParsedPage（或 None）
context.robots           # RobotsInfo：robots.txt 解析结果
context.sitemap          # SitemapInfo：.found / .urls
context.llms             # LlmsInfo：.found / .status
context.pages            # list[ParsedPage]：所有代表页（含首页）
context.discovered_urls  # list[str]：发现的全部候选 URL（含未抓取的，去重）
```

`ParsedPage` 字段：`url, status, final_url, title, meta_desc, h1_count, h2_count,
text_len, schemas, canonical, og_url, noindex, nosnippet, list_count, table_count,
internal_links, strong_count, time_elems, author_elems, p_count, dl_count,
question_headings, visible_date, jsonld_dates, raw_html, jsonld_blocks, jsonld_errors`。

**自解析兜底（重要）**：上面统计字段不够用时，直接用原料自行解析，**不要改框架层**：

- `p.raw_html`：原始 HTML 字符串，用 BeautifulSoup 自行提取正文/标题/联系方式/步骤等；
- `p.jsonld_blocks`：每个 `<script type="application/ld+json">` 解析后的**完整原始对象**
  （含 `@graph`、数组），供结构化数据类检查项自取字段（name/logo/sameAs/author 等）；
- `p.jsonld_errors`：解析失败的 JSON-LD 块数（用于「结构化数据有效性」检查）。

维度 3/4 扩充字段（只加不改）：`jsonld`（完整 JSON-LD 块，数组/@graph 已摊平为
dict 列表）、`jsonld_errors`（解析失败块数）、`og_site_name`、`emails`、`phones`
（可见文本中的邮箱/电话）、`external_links`（站外链接）。

## make_check 字段契约

```python
make_check(
    cid,        # int，检查项 ID（用你的段）
    dim,        # int，维度下标 0-4
    status,     # "good" / "warn" / "bad" / "advice"
    title,      # str，检查项名
    score,      # int 或 None（advice 项传 None）
    mx,         # int 或 None（advice 项传 None）
    impact,     # str，判定说明
    fix,        # str，优化建议
    evidence=None,   # list[str]，检测证据
    priority="",     # "" / "建议尽快" / "持续优化"
    scope="",        # 判定范围说明（可留空）
)
```

## 本地测试你的模块

```bash
cd backend
.venv\Scripts\activate
python -c "import asyncio; from engine import analyze; \
import json; print(json.dumps(asyncio.run(analyze('example.com')), ensure_ascii=False, indent=2))"
```

## 参考

- 30 项规格与判定要点：`docs/spec.md`
- 字段契约与 `make_check`：`checks.py`
- 数据结构（ScanContext/ParsedPage）：`context.py`
